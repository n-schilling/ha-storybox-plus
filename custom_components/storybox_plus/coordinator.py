"""Polling of the cloud and the live state from the push channel."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .analytics import Analytics
from .battery import BatteryStats
from .cloud import (
    TOPIC_BATTERY,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    Auth,
    Battery,
    Box,
    Chapter,
    CloudAuthError,
    CloudClient,
    CloudError,
    Household,
    Playback,
    PushClient,
    PushEvent,
    SleepTimer,
    Tonie,
    TonieDetails,
    Volume,
)
from .const import (
    CLASSIC_ONLINE_WINDOW,
    DOMAIN,
    RETRY_INTERVAL,
    UNAVAILABLE_AFTER_FAILURES,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type PlacementListener = Callable[[str | None, str | None], None]


@dataclass(slots=True)
class BoxState:
    """A box: what the REST API says plus what the push channel reported since."""

    box: Box
    online: bool | None = None
    battery: Battery | None = None
    playback: Playback | None = None
    volume: Volume | None = None
    sleep_timer: SleepTimer | None = None
    last_push: datetime | None = None

    @property
    def tonie_id(self) -> str | None:
        """Return the figure on the box, from the push channel if it has one."""
        if self.playback is not None:
            return self.playback.tonie_id
        return self.box.placed_tonie_id

    @property
    def playing(self) -> bool:
        """Return whether the box plays right now."""
        return self.playback is not None and self.playback.playing


@dataclass(slots=True)
class CloudState:
    """Everything the integration knows."""

    households: dict[str, Household] = field(default_factory=dict)
    boxes: dict[str, BoxState] = field(default_factory=dict)
    tonies: dict[str, Tonie] = field(default_factory=dict)
    push_connected: bool = False
    polled_at: datetime | None = None

    def box_by_mac(self, mac: str) -> BoxState | None:
        """Return the box with the MAC the push channel named."""
        return next((b for b in self.boxes.values() if b.box.mac == mac), None)


@dataclass(slots=True)
class RuntimeData:
    """Objects shared by the platforms of one entry."""

    auth: Auth
    client: CloudClient
    push: PushClient
    coordinator: StoryboxCoordinator
    analytics: Analytics | None
    battery_stats: BatteryStats


type StoryboxConfigEntry = ConfigEntry[RuntimeData]


class StoryboxCoordinator(DataUpdateCoordinator[CloudState]):
    """Reads the cloud every 5 minutes and takes the live state as it comes.

    A single failed poll keeps the last values and is repeated after a minute;
    only several failed polls in a row make the entities unavailable.
    """

    config_entry: StoryboxConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: StoryboxConfigEntry,
        client: CloudClient,
        push: PushClient,
        analytics: Analytics | None,
        details_store: Store[dict[str, Any]],
        battery_stats: BatteryStats,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.client = client
        self.push = push
        self.analytics = analytics
        self.battery_stats = battery_stats
        self._failures = 0
        self._placement_listeners: dict[str, list[PlacementListener]] = defaultdict(list)
        # The chapters of bought figures come only from the box they stand on
        # (playback info); they are kept so the page knows them afterwards.
        self._details_store = details_store
        self._details: dict[str, TonieDetails] = {}
        self._details_missing: set[str] = set()

    async def async_load_details(self) -> None:
        """Read the chapters learned in earlier runs."""
        data = await self._details_store.async_load()
        if data and isinstance(data.get("tonies"), dict):
            for tonie_id, raw in data["tonies"].items():
                if isinstance(raw, dict) and (details := _details_from_dict(raw)).chapters:
                    self._details[tonie_id] = details

    # ------------------------------------------------------------ polling

    async def _async_update_data(self) -> CloudState:
        try:
            library = await self.client.async_library()
        except CloudAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except CloudError as err:
            self._failures += 1
            self.update_interval = RETRY_INTERVAL
            if self.data is None or self._failures >= UNAVAILABLE_AFTER_FAILURES:
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="update_failed",
                    translation_placeholders={"error": str(err)},
                ) from err
            _LOGGER.debug("Poll %s failed, keeping the last values: %s", self._failures, err)
            return self.data
        self._failures = 0
        self.update_interval = UPDATE_INTERVAL

        previous = self.data
        state = CloudState(
            households={h.id: h for h in library.households},
            tonies={t.id: t for t in library.tonies},
            push_connected=self.push.connected,
            polled_at=dt_util.utcnow(),
        )
        for box in library.boxes:
            placed = box.placed_tonie_id
            if placed is not None and self._needs_details(state.tonies.get(placed)):
                await self._async_fetch_details(box.id, placed)
        state.tonies = {t.id: self._with_details(t) for t in library.tonies}
        for box in library.boxes:
            before = previous.boxes.get(box.id) if previous else None
            if before is not None:
                box_state = replace(before, box=box)
                if not box.live or before.last_push is None:
                    box_state.online = _online_from_rest(box)
            else:
                box_state = BoxState(box=box, online=_online_from_rest(box))
            state.boxes[box.id] = box_state
        self.push.set_boxes(b.box.mac for b in state.boxes.values() if b.box.live and b.box.mac)
        if self.analytics is not None:
            self.analytics.tick()
            self.analytics.save_soon()
        self.battery_stats.tick()
        self.battery_stats.save_soon()
        return state

    # ------------------------------------------------------------ push

    @callback
    def handle_push(self, event: PushEvent) -> None:
        """Take one message of the push channel.

        The listeners are told directly: async_set_updated_data would push the
        next poll back by the whole interval, and with a box that reports
        every minute the cloud would never be polled again.
        """
        box_state = self.data.box_by_mac(event.mac)
        if box_state is None:
            _LOGGER.debug("Push message for an unknown box on %s", event.topic)
            return
        tonie_before = box_state.tonie_id
        box_state.last_push = dt_util.utcnow()
        if event.topic == TOPIC_BATTERY and isinstance(event.data, Battery):
            box_state.battery = event.data
        elif event.topic == TOPIC_ONLINE:
            box_state.online = event.data if isinstance(event.data, bool) else None
            if box_state.online is False:
                self._stop_playing(box_state)
        elif event.topic == TOPIC_PLAYBACK and isinstance(event.data, Playback):
            box_state.playback = event.data
            if event.data.tonie_id is not None:
                box_state.online = True
        elif event.topic == TOPIC_VOLUME and isinstance(event.data, Volume):
            box_state.volume = event.data
        elif event.topic == TOPIC_SLEEP_TIMER and isinstance(event.data, SleepTimer):
            box_state.sleep_timer = event.data
        if self.analytics is not None:
            self.analytics.observe(box_state.box.id, box_state.tonie_id, box_state.playing)
            self.analytics.save_soon()
        if box_state.box.live and event.topic in (TOPIC_BATTERY, TOPIC_ONLINE):
            battery = box_state.battery
            self.battery_stats.observe(
                box_state.box.id,
                battery.percent if battery else None,
                battery.charging if battery else None,
                box_state.online is not False,
            )
            self.battery_stats.save_soon()
        if box_state.tonie_id != tonie_before:
            for listener in self._placement_listeners.get(box_state.box.id, []):
                listener(tonie_before, box_state.tonie_id)
            placed = box_state.tonie_id
            if placed is not None and self._needs_details(self.data.tonies.get(placed)):
                self.config_entry.async_create_background_task(
                    self.hass,
                    self._async_details_for_placement(box_state.box.id, placed),
                    f"{DOMAIN} chapters",
                )
        self.async_update_listeners()

    @callback
    def set_push_connected(self, connected: bool) -> None:
        """Note that the push channel came or went."""
        self.data.push_connected = connected
        if not connected:
            # Without the channel nothing is known about playing; count no further
            for box_state in self.data.boxes.values():
                self._stop_playing(box_state)
        self.async_update_listeners()

    def _stop_playing(self, box_state: BoxState) -> None:
        if box_state.playback is not None and box_state.playback.playing:
            box_state.playback = replace(box_state.playback, paused=True)
        if self.analytics is not None:
            self.analytics.observe(box_state.box.id, box_state.tonie_id, False)

    @callback
    def async_add_placement_listener(
        self, box_id: str, listener: PlacementListener
    ) -> Callable[[], None]:
        """Call the listener when the figure on a box changes."""
        self._placement_listeners[box_id].append(listener)

        @callback
        def remove() -> None:
            self._placement_listeners[box_id].remove(listener)

        return remove

    # ------------------------------------------------------------ chapters

    def _needs_details(self, tonie: Tonie | None) -> bool:
        """Return whether the figure's chapters are unknown and worth asking for."""
        return (
            tonie is not None
            and not tonie.chapters
            and tonie.id not in self._details
            and tonie.id not in self._details_missing
        )

    def _with_details(self, tonie: Tonie) -> Tonie:
        """Fill in what the box told about the figure, where the library is silent."""
        details = self._details.get(tonie.id)
        if details is None:
            return tonie
        return replace(
            tonie,
            chapters=tonie.chapters or details.chapters,
            series=tonie.series or details.series,
            image_url=tonie.image_url or details.image_url,
        )

    async def _async_fetch_details(self, box_id: str, tonie_id: str) -> bool:
        """Ask the cloud for the chapters of the figure on a box; True when learned."""
        try:
            details = await self.client.async_playback_info(box_id, tonie_id)
        except CloudError as err:
            _LOGGER.debug("Chapters of a figure not read: %s", err)
            return False
        if details is None or not details.chapters:
            self._details_missing.add(tonie_id)
            return False
        self._details[tonie_id] = details
        self._details_store.async_delay_save(self._details_to_save, 10)
        return True

    async def _async_details_for_placement(self, box_id: str, tonie_id: str) -> None:
        """A figure with unknown chapters was placed: learn them and tell the entities."""
        if await self._async_fetch_details(box_id, tonie_id) and tonie_id in self.data.tonies:
            self.data.tonies[tonie_id] = self._with_details(self.data.tonies[tonie_id])
            self.async_update_listeners()

    def _details_to_save(self) -> dict[str, Any]:
        return {"tonies": {tonie_id: _details_to_dict(d) for tonie_id, d in self._details.items()}}

    # ------------------------------------------------------------ helpers

    def tonie(self, tonie_id: str | None) -> Tonie | None:
        """Return the figure with the ID, if known."""
        if tonie_id is None:
            return None
        return self.data.tonies.get(tonie_id)


def _online_from_rest(box: Box) -> bool | None:
    """Derive whether a box is online from what the REST API says.

    The classic box only leaves a "last seen" timestamp; it counts as online
    while that is recent, and as offline once it is old. Without any
    information the state stays unknown, it is never guessed as off.
    """
    if box.online is not None:
        return box.online
    if box.last_seen is None:
        return None
    return dt_util.utcnow() - box.last_seen <= CLASSIC_ONLINE_WINDOW


def _details_to_dict(details: TonieDetails) -> dict[str, Any]:
    return {
        "title": details.title,
        "series": details.series,
        "image_url": details.image_url,
        "chapters": [
            {"id": c.id, "title": c.title, "seconds": c.seconds, "transcoding": c.transcoding}
            for c in details.chapters
        ],
    }


def _details_from_dict(raw: dict[str, Any]) -> TonieDetails:
    raw_chapters = raw.get("chapters")
    chapters = tuple(
        Chapter(
            id=str(c.get("id", "")),
            title=str(c.get("title", "")),
            seconds=c.get("seconds") if isinstance(c.get("seconds"), int | float) else None,
            transcoding=bool(c.get("transcoding")),
        )
        for c in (raw_chapters if isinstance(raw_chapters, list) else [])
        if isinstance(c, dict) and c.get("id")
    )
    return TonieDetails(
        title=raw.get("title") if isinstance(raw.get("title"), str) else None,
        series=raw.get("series") if isinstance(raw.get("series"), str) else None,
        image_url=raw.get("image_url") if isinstance(raw.get("image_url"), str) else None,
        chapters=chapters,
    )
