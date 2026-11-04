"""Polling of the cloud and the live state from the push channel."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .analytics import Analytics
from .cloud import (
    TOPIC_BATTERY,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    Auth,
    Battery,
    Box,
    CloudAuthError,
    CloudClient,
    CloudError,
    Household,
    Playback,
    PushClient,
    PushEvent,
    SleepTimer,
    Tonie,
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
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.client = client
        self.push = push
        self.analytics = analytics
        self._failures = 0
        self._placement_listeners: dict[str, list[PlacementListener]] = defaultdict(list)

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
        return state

    # ------------------------------------------------------------ push

    @callback
    def handle_push(self, event: PushEvent) -> None:
        """Take one message of the push channel."""
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
        if box_state.tonie_id != tonie_before:
            for listener in self._placement_listeners.get(box_state.box.id, []):
                listener(tonie_before, box_state.tonie_id)
        self.async_set_updated_data(self.data)

    @callback
    def set_push_connected(self, connected: bool) -> None:
        """Note that the push channel came or went."""
        self.data.push_connected = connected
        if not connected:
            # Without the channel nothing is known about playing; count no further
            for box_state in self.data.boxes.values():
                self._stop_playing(box_state)
        self.async_set_updated_data(self.data)

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
