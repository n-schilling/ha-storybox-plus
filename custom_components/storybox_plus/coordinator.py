"""Polling of the cloud and the live state from the push channel."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import logging
from typing import Any

from yarl import URL

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_OFF, STATE_ON
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import bedtime, fetcher, night, repeat, speech
from .analytics import Analytics
from .battery import BatteryStats
from .cloud import (
    TOPIC_BATTERY,
    TOPIC_HEADPHONES,
    TOPIC_ONLINE,
    TOPIC_PLAYBACK,
    TOPIC_SETTINGS_APPLIED,
    TOPIC_SLEEP_TIMER,
    TOPIC_VOLUME,
    Alarm,
    Auth,
    Battery,
    BedtimeSchedule,
    Box,
    Chapter,
    CloudAuthError,
    CloudClient,
    CloudError,
    CloudNotice,
    Headphones,
    Household,
    Member,
    Playback,
    PushClient,
    PushEvent,
    SleepTimer,
    Tonie,
    TonieDetails,
    TonieKind,
    Tune,
    Volume,
    contract,
)
from .cloud.models import (
    CLASSIC_SETTINGS,
    FEATURE_SETTINGS,
    LIVE_SETTINGS,
    SETTING_FIELDS,
    STEPPED_SETTINGS,
    VOLUME_STEPS,
)
from .cloud.rest import CHAPTER_TITLE_MAX
from .const import (
    CLASSIC_ONLINE_WINDOW,
    CLOUD_INFO_INTERVAL,
    DOMAIN,
    RETRY_INTERVAL,
    STALE_AFTER_POLLS,
    TESTED_BACKEND_RELEASE,
    UNAVAILABLE_AFTER_FAILURES,
    UPDATE_INTERVAL,
)
from .favourites import Action, FavouriteChapters, Plan, Steering
from .ids import account_identifier, box_of
from .night import NightMode, NightModes
from .notices import CloudNotices
from .preferences import LOCKABLE, Preferences
from .shuffle import MIN_CHAPTERS, ShuffleOnSwap, new_order
from .volumes import FigureVolumes

_LOGGER = logging.getLogger(__name__)

# A box that is still offline this long after it said so went to sleep
ASLEEP_AFTER = timedelta(seconds=30)

type PlacementListener = Callable[[str | None, str | None], None]
type NoticeListener = Callable[[CloudNotice], None]

# Bought figures asked for their chapters per poll, when the library gave none
DETAILS_PER_POLL = 5
# A box that told nothing about a figure's chapters is asked again after this
# long, or as soon as the figure is placed again
LENGTHS_RETRY = timedelta(hours=1)


class BoxError(HomeAssistantError):
    """A change to a box's settings or bedtimes that is refused before the cloud is asked.

    The code names why: "unknown_box", "no_alarm" (the box rings no alarms),
    "unknown_schedule", "not_supported" (a setting this box does not have) or
    "alarm_too_soon" (a wake-up light less than five minutes ahead).
    """

    def __init__(self, code: str) -> None:
        """Keep the code; it is the message as well."""
        super().__init__(code)
        self.code = code


# The cloud carries out a Tune change after answering it: it is read this often,
# this many seconds apart, before the change counts as not done
TUNE_CONFIRM_TRIES = 6
TUNE_CONFIRM_PAUSE = 2.0


class ChapterError(HomeAssistantError):
    """A change to the chapters of a figure that is refused before the cloud is asked.

    The code names why: "unknown_figure", "not_creative" (only creative
    figures take chapters), "unknown_chapter", "fetcher_missing" (no app to
    fetch a link with) or "too_long". A text says more where the code alone
    does not.
    """

    def __init__(self, code: str, text: str | None = None) -> None:
        """Keep the code; without a text it is the message as well."""
        super().__init__(text or code)
        self.code = code
        self.text = text


@dataclass(slots=True)
class BoxState:
    """A box: what the REST API says plus what the push channel reported since."""

    box: Box
    online: bool | None = None
    battery: Battery | None = None
    playback: Playback | None = None
    volume: Volume | None = None
    sleep_timer: SleepTimer | None = None
    headphones: Headphones | None = None
    last_push: datetime | None = None
    # When the push channel last said the box came online
    online_since: datetime | None = None
    # The bedtime schedules of a box that rings alarms; None until read once
    schedules: tuple[BedtimeSchedule, ...] | None = None

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
    favourites: FavouriteChapters
    night_modes: NightModes
    volumes: FigureVolumes
    notices: CloudNotices
    preferences: Preferences
    shuffles: ShuffleOnSwap


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
        favourites: FavouriteChapters,
        night_modes: NightModes,
        volumes: FigureVolumes,
        notices: CloudNotices,
        preferences: Preferences,
        shuffles: ShuffleOnSwap,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.client = client
        self.push = push
        self.favourites = favourites
        self.night_modes = night_modes
        self.volumes = volumes
        self.notices = notices
        self.preferences = preferences
        self.shuffles = shuffles
        # Creative figures being shuffled right now
        self._shuffling: set[str] = set()
        # Read now and then: the box pictures by colour and the cloud backend's version
        self.box_pictures: dict[str, str] = {}
        # The members of each household, read with the cloud info
        self.members: dict[str, list[Member]] = {}
        # The Tunes the account bought; None until read once
        self.tunes: list[Tune] | None = None
        self.backend_version: str | None = None
        self._cloud_info_at: datetime | None = None
        # Notifications of the cloud waiting for the event entity, and the entity's listener
        self._notice_listener: NoticeListener | None = None
        self._notices_waiting: list[CloudNotice] = []
        # Per box: the next change of the night mode, and a change being sent
        self._night_timers: dict[str, CALLBACK_TYPE] = {}
        self._night_busy: set[str] = set()
        self.analytics = analytics
        self.battery_stats = battery_stats
        self._failures = 0
        # Polls in a row a box with a device was missing from
        self._missing_polls: dict[str, int] = {}
        self._placement_listeners: dict[str, list[PlacementListener]] = defaultdict(list)
        # The chapters of bought figures come only from the box they stand on
        # (playback info); they are kept so the page knows them afterwards.
        # Creative figures are left out: the cloud names and times their
        # chapters itself, with the IDs a change of them needs.
        self._details_store = details_store
        self._details: dict[str, TonieDetails] = {}
        # Figures the app's detail query knew nothing about, for this run
        self._details_missing: set[str] = set()
        # Figures a box told nothing (more) about, with the time it was asked
        self._lengths_asked: dict[str, datetime] = {}
        # Per box: the wake-up the integration armed last, when it last sent a command,
        # how often it tried for which step since the box came online, and the next check
        self._armed: dict[str, datetime] = {}
        self._alarm_sent: dict[str, datetime] = {}
        self._alarm_tries: dict[str, tuple[datetime | None, int]] = {}
        self._alarm_timers: dict[str, CALLBACK_TYPE] = {}
        # One check of the cloud's interface at a time
        self._cloud_check_lock = asyncio.Lock()
        # Per box: the look whether it stayed offline, for the favourites
        self._asleep_timers: dict[str, CALLBACK_TYPE] = {}
        # Per box: the playback report before the last, for the repeat (kept in the preferences)
        self._repeat_last: dict[str, Playback] = {}
        # Per Toniebox 1 the entity that tells whether it is in the network, as watched now
        self._presence_watched: dict[str, str] = {}
        self._presence_unsub: CALLBACK_TYPE | None = None
        # The first poll has put its boxes together: from then on there is data
        self._polled = False
        entry.async_on_unload(self._cancel_alarm_timers)
        entry.async_on_unload(self._cancel_asleep_timers)
        entry.async_on_unload(self._cancel_night_timers)
        entry.async_on_unload(self._unwatch_presence)

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
            tonie = state.tonies.get(placed) if placed is not None else None
            if placed is not None and self._needs_lengths(tonie):
                await self._async_fetch_details(
                    box.id, placed, named=bool(tonie and tonie.chapters)
                )
        await self._async_ask_library_details(state.tonies)
        state.tonies = {t.id: self._with_details(t) for t in library.tonies}
        for box in library.boxes:
            before = previous.boxes.get(box.id) if previous else None
            if before is not None:
                box_state = replace(before, box=box)
                if not box.live or before.last_push is None:
                    box_state.online = _online_from_rest(box)
            else:
                box_state = BoxState(box=box, online=_online_from_rest(box))
            if (entity_id := self.presence_entity(box)) is not None:
                box_state.online = self._presence_online(entity_id)
            state.boxes[box.id] = box_state
            if box.alarm_capable:
                await self._async_read_schedules(box_state)
            else:
                box_state.schedules = None
        self.push.set_boxes(b.box.mac for b in state.boxes.values() if b.box.live and b.box.mac)
        self._remove_stale_devices(state)
        self._drop_stale_repeats(state)
        now = dt_util.utcnow().timestamp()
        self.favourites.keep(set(state.boxes), set(state.tonies), now)
        for box_state in state.boxes.values():
            # A Toniebox 2 that is switched off: the figure it wakes with counts as placed
            if box_state.box.live and box_state.online is False and not box_state.playing:
                self.runs(box_state.box.id).away(box_state.box.id, now)
        self._watch_presence(state)
        if self.analytics is not None:
            self.analytics.tick()
            self.analytics.save_soon()
        self.battery_stats.tick()
        self.battery_stats.save_soon()
        for box_state in state.boxes.values():
            self._check_alarm(box_state, state)
            self._check_night(box_state)
        await self._async_read_notices()
        await self._async_auto_lock(state)
        await self._async_read_tunes()
        await self._async_read_cloud_info(state)
        self._follow_box_names(state)
        self._settle_presence(state)
        return state

    async def _async_read_tunes(self) -> bool:
        """Read the bought Tunes; a failed read keeps the last ones and answers False.

        A Tune that came onto a figure or left one since the last read is
        logged, whoever laid it on or took it off.
        """
        try:
            tunes = await self.client.async_tunes()
        except CloudError as err:
            _LOGGER.debug("Tunes not read: %s", err)
            return False
        if self.tunes is not None:
            before = {t.id: set(t.assigned) for t in self.tunes}
            for tune in tunes:
                was = before.get(tune.id, set())
                for tonie_id in sorted(set(tune.assigned) - was):
                    _LOGGER.info("Tune %r lies on %s now", tune.title, self._figure_name(tonie_id))
                for tonie_id in sorted(was - set(tune.assigned)):
                    _LOGGER.info("Tune %r left %s", tune.title, self._figure_name(tonie_id))
        self.tunes = tunes
        return True

    def _figure_name(self, tonie_id: str) -> str:
        """A figure as the log names it: its name and the start of its ID."""
        tonie = self.data.tonies.get(tonie_id) if self.data else None
        name = tonie.name if tonie else "figure"
        return f"{name!r} ({tonie_id[:6]}…)"

    def tune_fits(self, tune: Tune) -> list[str]:
        """Return the figures a Tune can be laid on now: those it fits and does not lie on.

        A Tune laid on as often as it may be fits none until it is taken off one.
        """
        if tune.remaining is not None and tune.remaining < 1:
            return []
        fits = set(tune.suitable) | set(tune.compatible)
        if tune.all_creative:
            fits |= {t.id for t in self.data.tonies.values() if t.kind is TonieKind.CREATIVE}
        return sorted(t for t in fits if t in self.data.tonies and t not in tune.assigned)

    def tune_on(self, tonie_id: str) -> Tune | None:
        """Return the Tune that lies on a figure, if any."""
        return next((t for t in self.tunes or () if tonie_id in t.assigned), None)

    async def async_redeem_voucher(self, code: str) -> int:
        """Redeem a Tunes voucher for the account; the Tunes are read anew."""
        count = await self.client.async_redeem_voucher(code)
        await self._async_read_tunes()
        self.async_update_listeners()
        return count

    async def async_redeem_token(self, tonie_id: str, token: str) -> Tonie:
        """Put the content of a token on a creative figure and read the figure anew."""
        tonie = self._creative(tonie_id)
        await self.client.async_redeem_token(tonie, token)
        return await self._async_take_creative(tonie, None)

    async def async_set_tune(self, tonie_id: str, tune_id: str | None) -> None:
        """Lay a bought Tune on a figure, or take the one there off (None).

        A creative figure keeps its chapters while a Tune lies on it; taken
        off, they play again. Afterwards the Tunes and the figures are read
        anew, because the cloud changes what the figure plays.
        """
        tonie = self.data.tonies.get(tonie_id)
        if tonie is None:
            raise ChapterError("unknown_figure")
        if tune_id is None:
            if self.tune_on(tonie_id) is None:
                raise ChapterError("no_tune")
            _LOGGER.info("Taking the Tune off %s", self._figure_name(tonie_id))
            await self.client.async_remove_tune(tonie)
        else:
            tune = next((t for t in self.tunes or () if t.id == tune_id), None)
            if tune is None:
                raise ChapterError("unknown_tune")
            if tonie_id not in self.tune_fits(tune) and tonie_id not in tune.assigned:
                raise ChapterError("unsuitable_tune")
            _LOGGER.info("Laying Tune %r on %s", tune.title, self._figure_name(tonie_id))
            await self.client.async_assign_tune(tonie, tune_id)
        await self._async_confirm_tune(tonie_id, tune_id)
        if tonie.kind is TonieKind.CREATIVE:
            await self._async_take_creative(tonie, None)
        self.async_update_listeners()

    async def _async_confirm_tune(self, tonie_id: str, tune_id: str | None) -> None:
        """Read the Tunes until the cloud shows the change, or refuse after a while.

        The cloud answers a change at once but may carry it out later; a Tune
        it does not take off in time is reported instead of being shown as
        gone.
        """
        for attempt in range(TUNE_CONFIRM_TRIES):
            if attempt:
                await asyncio.sleep(TUNE_CONFIRM_PAUSE)
            if not await self._async_read_tunes():
                continue
            on = self.tune_on(tonie_id)
            if (on.id if on else None) == tune_id:
                _LOGGER.debug("The cloud shows the Tune change after %s reads", attempt + 1)
                return
        _LOGGER.warning(
            "The cloud answered the Tune change of %s but does not show it",
            self._figure_name(tonie_id),
        )
        raise ChapterError("tune_not_changed")

    async def _async_read_cloud_info(self, state: CloudState) -> None:
        """Read the box pictures, the backend's version and the members, at most once an hour."""
        now = dt_util.utcnow()
        if self._cloud_info_at is not None and now - self._cloud_info_at < CLOUD_INFO_INTERVAL:
            return
        self._cloud_info_at = now
        try:
            self.backend_version = await self.client.async_backend_version()
        except CloudError as err:
            _LOGGER.debug("Version of the cloud not read: %s", err)
        if self.backend_version is not None and not self.backend_tested:
            _LOGGER.debug(
                "The cloud runs %s; tested with %s", self.backend_version, TESTED_BACKEND_RELEASE
            )
            last = self.preferences.cloud_check
            if last is None or last.get("release") != self.backend_release:
                # A release this version was not tested with: look once whether the
                # interface still answers as expected
                self.config_entry.async_create_background_task(
                    self.hass, self._async_check_cloud_quietly(), f"{DOMAIN} cloud check"
                )
        try:
            self.box_pictures = await self.client.async_box_pictures()
        except CloudError as err:
            _LOGGER.debug("Pictures of the boxes not read: %s", err)
        await self._async_read_members(state)

    async def _async_read_members(self, state: CloudState) -> None:
        """Read who belongs to each household; one that cannot be read keeps its last members."""
        members: dict[str, list[Member]] = {}
        for household_id in state.households:
            try:
                members[household_id] = await self.client.async_members(household_id)
            except CloudError as err:
                _LOGGER.debug("Members of a household not read: %s", err)
                if household_id in self.members:
                    members[household_id] = self.members[household_id]
        self.members = members

    async def async_check_cloud(self) -> dict[str, Any]:
        """Compare what the cloud answers with what the integration relies on.

        Reads only. The report names requests by their shape, field names,
        kinds and HTTP statuses, never a value of the account, so it can go
        into a public issue as it is. It is kept for the page.
        """
        async with self._cloud_check_lock:
            figures = [
                (b.box.id, b.tonie_id, (b.playback.content_version if b.playback else None) or 0)
                for b in (self.data.boxes.values() if self.data is not None else ())
                if b.box.live and b.tonie_id is not None
            ]
            seen: dict[str, frozenset[str]] = getattr(self.push, "seen_keys", {})
            results = await contract.async_check(self.client, figures, seen)
            try:
                self.backend_version = await self.client.async_backend_version()
            except CloudError as err:
                _LOGGER.debug("Version of the cloud not read: %s", err)
            report: dict[str, Any] = {
                "release": self.backend_release,
                "tested": TESTED_BACKEND_RELEASE,
                "at": dt_util.utcnow().isoformat(),
                "ok": contract.passed(results),
                "results": [result.as_dict() for result in results],
            }
            self.preferences.set_cloud_check(report)
            differing = [r.name for r in results if r.status in ("changed", "failed")]
            if differing:
                _LOGGER.warning(
                    "The cloud (%s) answers differently than expected: %s",
                    self.backend_release,
                    ", ".join(differing),
                )
            else:
                _LOGGER.info("The cloud (%s) answers as expected", self.backend_release)
            self.async_update_listeners()
            return report

    async def _async_check_cloud_quietly(self) -> None:
        """Run the check of the interface by itself; whatever goes wrong is only logged."""
        try:
            await self.async_check_cloud()
        except CloudError as err:
            _LOGGER.debug("The cloud's interface was not checked: %s", err)

    @property
    def backend_release(self) -> str | None:
        """Return the release part of the cloud's version, without its commit."""
        return self.backend_version.split("/", 1)[0] if self.backend_version else None

    @property
    def backend_tested(self) -> bool:
        """Return whether the cloud runs the release this version was tested with."""
        return self.backend_release == TESTED_BACKEND_RELEASE

    def box_picture(self, box: Box) -> str | None:
        """Return the picture of a box: by its colour, else the one the cloud names for it."""
        by_color = self.box_pictures.get(box.color_id) if box.color_id else None
        return by_color or box.image_url

    def _follow_box_names(self, state: CloudState) -> None:
        """Give a box's device the name the box has in the cloud.

        A name given in Home Assistant (name_by_user) stays; it wins anyway.
        """
        registry = dr.async_get(self.hass)
        entry = self.config_entry
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
            box_id = box_of(entry, device.identifiers)
            box_state = state.boxes.get(box_id) if box_id else None
            if box_state is not None and device.name != box_state.box.name:
                registry.async_update_device(device.id, name=box_state.box.name)

    async def _async_auto_lock(self, state: CloudState) -> None:
        """Lock the bought figures and discs that are new in the account, if so preferred."""
        for tonie in self.preferences.to_lock(list(state.tonies.values())):
            try:
                await self.client.async_lock(tonie, True)
            except CloudError as err:
                _LOGGER.debug("A new figure was not locked, trying again later: %s", err)
                continue
            self.preferences.locked(tonie.id)
            state.tonies[tonie.id] = replace(tonie, locked=True)
            _LOGGER.debug("A new figure was locked to the household")

    async def async_rename_household(self, household_id: str, name: str) -> None:
        """Rename a household; the entry and the account's device follow when named after it.

        The entry is titled after its household at setup; as long as the
        title is still that name, it takes the new one, and the device of
        the account's notifications with it. A title given by hand stays.
        """
        household = self.data.households.get(household_id)
        if household is None:
            raise BoxError("unknown_household")
        await self.client.async_rename_household(household_id, name)
        self.data.households[household_id] = replace(household, name=name)
        entry = self.config_entry
        if entry.title == household.name:
            self.hass.config_entries.async_update_entry(entry, title=name)
            registry = dr.async_get(self.hass)
            for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
                if account_identifier(entry) in device.identifiers:
                    registry.async_update_device(device.id, name=name)
        self.async_update_listeners()

    async def async_set_lock(self, tonie_id: str, locked: bool) -> Tonie:
        """Lock a bought figure or disc to the household, or unlock it."""
        tonie = self.data.tonies.get(tonie_id)
        if tonie is None:
            raise ChapterError("unknown_figure")
        if tonie.kind not in LOCKABLE:
            raise ChapterError("not_lockable")
        await self.client.async_lock(tonie, locked)
        # Whatever happens to it from now on, it is no new figure any more
        self.preferences.locked(tonie_id)
        tonie = self.data.tonies[tonie_id] = replace(tonie, locked=locked)
        self.async_update_listeners()
        return tonie

    async def _async_read_notices(self) -> None:
        """Pass on the cloud's notifications not passed on yet; a failed read waits for the next poll."""
        try:
            notices = await self.client.async_notices()
        except CloudError as err:
            _LOGGER.debug("Notifications of the cloud not read: %s", err)
            return
        for notice in self.notices.new(notices):
            if self._notice_listener is not None:
                self._notice_listener(notice)
            else:
                self._notices_waiting.append(notice)
            if self.preferences.mark_read:
                try:
                    await self.client.async_mark_notice_read(notice)
                except CloudError as err:
                    _LOGGER.debug("A notification was not marked as read: %s", err)

    @callback
    def async_set_notice_listener(self, listener: NoticeListener) -> Callable[[], None]:
        """Hand the cloud's new notifications to the listener, those waiting first.

        The waiting ones follow a moment later: an entity's state written
        while it is being added would be lost.
        """
        self._notice_listener = listener

        @callback
        def _flush() -> None:
            waiting, self._notices_waiting = self._notices_waiting, []
            for notice in waiting:
                if self._notice_listener is not None:
                    self._notice_listener(notice)
                else:
                    self._notices_waiting.append(notice)

        self.hass.loop.call_soon(_flush)

        @callback
        def remove() -> None:
            self._notice_listener = None

        return remove

    async def _async_read_schedules(self, box_state: BoxState) -> None:
        """Read the bedtime schedules of a box; a failed read keeps the last ones."""
        try:
            box_state.schedules = tuple(await self.client.async_bedtime_schedules(box_state.box))
        except CloudError as err:
            _LOGGER.debug("Bedtime schedules of a box not read: %s", err)

    def _remove_stale_devices(self, state: CloudState) -> None:
        """Remove the devices of boxes that left the account, and of each Toniebox 1.

        A box counts as gone only after an hour of polls without it, so an
        answer of the cloud that lacks it once does not cost its entities
        and what the user made of them. A Toniebox 1 has no entities, so a
        device of it stands for nothing and goes the same way.
        """
        registry = dr.async_get(self.hass)
        seen: set[str] = set()
        for device in dr.async_entries_for_config_entry(registry, self.config_entry.entry_id):
            # The account's own device stands for no box
            key = box_of(self.config_entry, device.identifiers)
            if key is None or (key in state.boxes and state.boxes[key].box.live):
                continue
            seen.add(key)
            self._missing_polls[key] = self._missing_polls.get(key, 0) + 1
            if self._missing_polls[key] >= STALE_AFTER_POLLS:
                _LOGGER.debug("A box left the account; its device is removed")
                registry.async_remove_device(device.id)
        self._missing_polls = {k: v for k, v in self._missing_polls.items() if k in seen}

    # ------------------------------------------------------------ presence of a Toniebox 1

    def presence_entity(self, box: Box) -> str | None:
        """Return the entity that tells whether a Toniebox 1 is in the network, if one is set."""
        return None if box.live else self.preferences.presence.get(box.id)

    def _presence_online(self, entity_id: str) -> bool | None:
        """Read the entity: at home or on is online, away or off is offline, the rest unknown."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        if state.state in (STATE_HOME, STATE_ON):
            return True
        if state.state in (STATE_NOT_HOME, STATE_OFF):
            return False
        return None

    def _watch_presence(self, state: CloudState) -> None:
        """Follow the presence entities of the boxes in the account; count their active time."""
        wanted = {
            box_state.box.id: entity_id
            for box_state in state.boxes.values()
            if (entity_id := self.presence_entity(box_state.box)) is not None
        }
        if wanted == self._presence_watched:
            return
        before = self._presence_watched
        self._unwatch_presence()
        self._presence_watched = wanted
        if wanted:
            self._presence_unsub = async_track_state_change_event(
                self.hass, sorted(set(wanted.values())), self._presence_changed
            )
        for box_id in before.keys() | wanted.keys():
            self._count_awake(box_id, state.boxes[box_id].online if box_id in wanted else None)

    def _settle_presence(self, state: CloudState) -> None:
        """Read the presence entities once more, at the very end of a poll.

        The boxes of a poll are put together before the cloud has answered
        everything; an entity that changes in between tells the listener, which
        knows only the boxes of the poll before, or none during the first poll.
        Nothing waits between this and the poll's boxes becoming the current
        ones, so no change is lost.
        """
        for box_id, entity_id in self._presence_watched.items():
            box_state = state.boxes.get(box_id)
            online = self._presence_online(entity_id)
            if box_state is None or box_state.online is online:
                continue
            box_state.online = online
            self._count_awake(box_id, online)
        self._polled = True

    def _unwatch_presence(self) -> None:
        if self._presence_unsub is not None:
            self._presence_unsub()
            self._presence_unsub = None
        self._presence_watched = {}

    def _count_awake(self, box_id: str, online: bool | None) -> None:
        if self.analytics is not None and self.counts_box(box_id):
            self.analytics.awake(box_id, online is True, self.preferences.presence_lag(box_id) * 60)
            self.analytics.save_soon()

    @callback
    def _presence_changed(self, event: Event[EventStateChangedData]) -> None:
        """Take a change of a presence entity as the box coming or going."""
        # During the first poll there are no boxes yet; the end of the poll reads the entity
        if not self._polled:
            return
        entity_id = event.data["entity_id"]
        online = self._presence_online(entity_id)
        changed = False
        for box_id, watched in self._presence_watched.items():
            box_state = self.data.boxes.get(box_id)
            if watched != entity_id or box_state is None or box_state.online is online:
                continue
            box_state.online = online
            self._count_awake(box_id, online)
            changed = True
        if changed:
            self.async_update_listeners()

    async def async_set_presence(self, box_id: str, entity_id: str | None) -> BoxState:
        """Set or clear the presence entity of a Toniebox 1."""
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        if box_state.box.live:
            raise BoxError("not_supported")
        await self.preferences.async_set_presence(box_id, entity_id)
        box_state.online = (
            self._presence_online(entity_id)
            if entity_id is not None
            else _online_from_rest(box_state.box)
        )
        self._watch_presence(self.data)
        self.async_update_listeners()
        return box_state

    async def async_set_presence_lag(self, box_id: str, minutes: int) -> BoxState:
        """Set the minutes taken off each stretch of active time of a Toniebox 1."""
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        if box_state.box.live:
            raise BoxError("not_supported")
        await self.preferences.async_set_presence_lag(box_id, minutes)
        if box_id in self._presence_watched:
            self._count_awake(box_id, box_state.online)
        return box_state

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
            was_online = box_state.online
            box_state.online = event.data if isinstance(event.data, bool) else None
            if box_state.online is False:
                self._stop_playing(box_state)
                self._note_asleep_later(box_state.box.id)
            if box_state.online is True and was_online is not True:
                box_state.online_since = box_state.last_push
                self._alarm_tries.pop(box_state.box.id, None)
                self._check_alarm_later(box_state.box.id, bedtime.SETTLE)
        elif event.topic == TOPIC_PLAYBACK and isinstance(event.data, Playback):
            box_state.playback = event.data
            if event.data.tonie_id is not None:
                box_state.online = True
            # Of the accounts that see a box, the one that speaks for it steers it
            action = (
                self.favourites.observe(
                    box_state.box.id,
                    event.data,
                    lambda figure: self.favourite_plan(box_state, figure),
                )
                if self.counts_box(box_state.box.id)
                else None
            )
            again = self._observe_repeat(box_state, event.data, action)
            if again is not None:
                self.config_entry.async_create_background_task(
                    self.hass, self._async_play_from(box_state, again), f"{DOMAIN} repeat"
                )
            elif action is not None:
                self.config_entry.async_create_background_task(
                    self.hass, self._async_steer(box_state, action), f"{DOMAIN} favourites"
                )
        elif event.topic == TOPIC_VOLUME and isinstance(event.data, Volume):
            box_state.volume = event.data
        elif event.topic == TOPIC_HEADPHONES and isinstance(event.data, Headphones):
            box_state.headphones = event.data
        elif event.topic == TOPIC_SLEEP_TIMER and isinstance(event.data, SleepTimer):
            box_state.sleep_timer = event.data
            self._check_alarm(box_state, self.data)
        elif (
            event.topic == TOPIC_SETTINGS_APPLIED
            and box_state.box.settings.settings_applied is False
        ):
            # The page's note that the box has not taken the settings yet goes at once,
            # not with the next poll
            box_state.box = replace(
                box_state.box, settings=replace(box_state.box.settings, settings_applied=True)
            )
        if self.analytics is not None:
            playback = box_state.playback
            self.analytics.observe(
                box_state.box.id,
                box_state.tonie_id,
                box_state.playing and self.counts_box(box_state.box.id),
                playback.chapter if playback else None,
            )
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
            if box_state.box.live:
                self._follow_figure_volume(box_state)
                self._shuffle_replaced(box_state)
            placed = box_state.tonie_id
            if placed is not None:
                # Placed anew: the box may know now what it did not before
                self._lengths_asked.pop(placed, None)
                if self.analytics is not None and self.counts_box(box_state.box.id):
                    self.analytics.placed(box_state.box.id, placed)
                    self.analytics.save_soon()
            if placed is not None and self._needs_lengths(self.data.tonies.get(placed)):
                self.config_entry.async_create_background_task(
                    self.hass,
                    self._async_details_for_placement(box_state.box.id, placed),
                    f"{DOMAIN} chapters",
                )
        self.async_update_listeners()

    def _follow_figure_volume(self, box_state: BoxState) -> None:
        """Set the level of the figure just placed, or restore the box's after one left."""
        current = box_state.volume.level if box_state.volume else None
        level = self.volumes.placed(box_state.box.id, box_state.tonie_id, current)
        self.volumes.save_soon()
        mac = box_state.box.mac
        if level is None or mac is None or level == current:
            return

        async def _send() -> None:
            try:
                await self.push.async_set_volume(mac, level)
            except CloudError as err:
                _LOGGER.debug("The volume of a figure was not set: %s", err)

        self.config_entry.async_create_background_task(self.hass, _send(), f"{DOMAIN} volume")

    def _shuffle_replaced(self, box_state: BoxState) -> None:
        """Shuffle the creative figure another figure just replaced, if it asks for it."""
        target = self.shuffles.placed(box_state.box.id, box_state.tonie_id)
        tonie = self.data.tonies.get(target) if target else None
        if (
            tonie is None
            or tonie.kind is not TonieKind.CREATIVE
            or len(tonie.chapters) < MIN_CHAPTERS
            or tonie.id in self._shuffling
            or self.tune_on(tonie.id) is not None
            or any(b.tonie_id == tonie.id for b in self.data.boxes.values())
        ):
            return
        self._shuffling.add(tonie.id)

        async def _shuffle() -> None:
            try:
                order = new_order([c.id for c in tonie.chapters])
                await self.async_arrange_chapters(tonie.id, order)
                _LOGGER.debug("A replaced creative figure was shuffled")
            except (CloudError, ChapterError) as err:
                _LOGGER.debug("A replaced creative figure was not shuffled: %s", err)
            finally:
                self._shuffling.discard(tonie.id)

        self.config_entry.async_create_background_task(self.hass, _shuffle(), f"{DOMAIN} shuffle")

    async def async_set_figure_volume(self, tonie_id: str, level: int | None) -> None:
        """Keep the level of a figure; a box it stands on gets it at once."""
        if tonie_id not in self.data.tonies:
            raise ChapterError("unknown_figure")
        await self.volumes.async_set(tonie_id, level)
        for box_state in self.data.boxes.values():
            if box_state.box.live and box_state.tonie_id == tonie_id:
                # As if placed anew: the level before the figure stays the one to restore
                self._follow_figure_volume(box_state)

    # ------------------------------------------------------------ favourites

    def _keeper(self, owner: StoryboxConfigEntry | None) -> FavouriteChapters:
        """Return the favourites of the account that speaks for a box or a figure."""
        if owner is None or owner is self.config_entry:
            return self.favourites
        runtime: RuntimeData | None = getattr(owner, "runtime_data", None)
        return runtime.favourites if runtime is not None else self.favourites

    def stars(self, tonie_id: str) -> FavouriteChapters:
        """Return who keeps the stars of a figure: one account, also where several have it."""
        return self._keeper(tonie_owner(self.hass, tonie_id))

    def runs(self, box_id: str) -> FavouriteChapters:
        """Return who steers a box: the account that speaks for it."""
        return self._keeper(box_owner(self.hass, box_id))

    def playing_stars(self, tonie: Tonie | None) -> tuple[int, ...] | None:
        """Return the favourites among the chapters a box plays of a figure.

        None while that is not known: without a figure, and while a Tune lies
        on it, whose chapters are not the figure's.
        """
        if tonie is None or self.tune_on(tonie.id) is not None:
            return None
        return self.stars(tonie.id).indexes(tonie)

    def favourite_mode(self, box_state: BoxState | None, tonie_id: str) -> Steering | None:
        """Return the mode the favourites of a figure play by on a box now; None: off.

        The figure's own mode, else the account's. "bedtime" is "only" within
        a bedtime of the box and "first" otherwise, also without a box.
        """
        kept = self.stars(tonie_id).get(tonie_id)
        # The account that keeps the stars of the figure names the mode as well
        owner = tonie_owner(self.hass, tonie_id)
        runtime: RuntimeData | None = (
            None
            if owner is None or owner is self.config_entry
            else getattr(owner, "runtime_data", None)
        )
        preferences = runtime.preferences if runtime is not None else self.preferences
        mode = (kept.mode if kept else None) or preferences.favourites_mode
        if mode == "off":
            return None
        if mode == "bedtime":
            asleep = box_state is not None and bedtime.asleep(
                box_state.schedules, self.now_at(box_state.box)
            )
            return "only" if asleep else "first"
        return mode

    def favourite_plan(self, box_state: BoxState, tonie_id: str) -> Plan | None:
        """Return how a figure is steered on a box now; None while it is not.

        Not without favourites, and not while a Tune lies on the figure: the
        box then plays the Tune, whose chapters are not the figure's.
        """
        tonie = self.tonie(tonie_id)
        if tonie is None or self.tune_on(tonie_id) is not None:
            return None
        chapters = self.stars(tonie.id).indexes(tonie)
        mode = self.favourite_mode(box_state, tonie_id)
        if not chapters or mode is None:
            return None
        if mode != "only" and not tonie.chapters:
            # The other chapters are not known: there is no order to follow
            return None
        return Plan(mode, chapters, len(tonie.chapters))

    async def async_star(self, tonie_id: str, chapter: int, favourite: bool | None = None) -> bool:
        """Mark a chapter of a figure as a favourite or not (None: the other way round)."""
        tonie = self.tonie(tonie_id)
        if tonie is None:
            raise ChapterError("unknown_figure")
        if chapter < 0 or (tonie.chapters and chapter >= len(tonie.chapters)):
            raise ChapterError("unknown_chapter")
        if tonie.kind is TonieKind.CREATIVE and not tonie.chapters:
            raise ChapterError("unknown_chapter")
        result = await self.stars(tonie_id).async_star(tonie, chapter, favourite)
        self.async_update_listeners()
        return result

    def suspend_favourites(self, box_id: str, suspended: bool) -> BoxState:
        """Let the figure on a Toniebox 2 play everything until it is taken off, or end that."""
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        if not box_state.box.live:
            raise BoxError("not_supported")
        if box_state.tonie_id is None:
            raise BoxError("nothing_plays")
        self.runs(box_id).suspend(box_id, box_state.tonie_id, suspended)
        self.async_update_listeners()
        return box_state

    def chapter_step(self, box_state: BoxState, step: int) -> int:
        """Return the chapter a step forwards (1) or back (-1) leads to on a box.

        By the order of the favourites while the figure is steered, else the
        chapter beside the one that plays. The favourites are told, so the
        chapter plays whatever the order says.
        """
        playback = box_state.playback
        if playback is None or playback.tonie_id is None:
            raise BoxError("nothing_plays")
        runs = self.runs(box_state.box.id)
        # After a restart the order is not known until the box reports
        runs.sync(
            box_state.box.id,
            playback.tonie_id,
            self.favourite_plan(box_state, playback.tonie_id),
        )
        chapter = runs.neighbour(box_state.box.id, playback.tonie_id, step)
        if chapter is None:
            chapter = max(0, (playback.chapter or 0) + step)
            tonie = self.tonie(playback.tonie_id)
            if tonie is not None and tonie.chapters:
                chapter = min(chapter, len(tonie.chapters) - 1)
        self.runs(box_state.box.id).chosen(box_state.box.id, playback.tonie_id, chapter)
        return chapter

    def chapter_chosen(self, box_state: BoxState, chapter: int) -> None:
        """Tell the favourites that Home Assistant sends the box to a chapter."""
        self.runs(box_state.box.id).chosen(box_state.box.id, box_state.tonie_id, chapter)

    def chapter_unchosen(self, box_state: BoxState, chapter: int) -> None:
        """Take the chapter back: the command for it did not reach the box."""
        self.runs(box_state.box.id).unchosen(box_state.box.id, chapter)

    async def async_play_favourite(self, box_id: str) -> int:
        """Send a Toniebox 2 to the next favourite of the figure on it; after the last, the first."""
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        mac = box_state.box.mac
        if not box_state.box.live or mac is None:
            raise BoxError("not_supported")
        tonie = self.tonie(box_state.tonie_id)
        if tonie is None:
            raise BoxError("nothing_plays")
        if self.tune_on(tonie.id) is not None:
            raise BoxError("tune_plays")
        chapters = self.stars(tonie.id).indexes(tonie)
        if not chapters:
            raise BoxError("no_favourites")
        playback = box_state.playback
        now = playback.chapter if playback and playback.chapter is not None else -1
        chapter = next((c for c in chapters if c > now), chapters[0])
        self.chapter_chosen(box_state, chapter)
        try:
            await self.push.async_set_position(mac, chapter, 0)
            await self.push.async_play(mac)
        except CloudError:
            self.chapter_unchosen(box_state, chapter)
            raise
        return chapter

    async def _async_steer(self, box_state: BoxState, action: Action) -> None:
        """Send the box to the chapter the order wants, or pause it after the last one."""
        mac = box_state.box.mac
        if mac is None:
            return
        try:
            if action[0] == "pause":
                await self.push.async_pause(mac)
            else:
                await self.push.async_set_position(mac, action[1], 0)
                if action[0] == "play":
                    await self.push.async_play(mac)
        except CloudError as err:
            _LOGGER.debug("The box was not steered by the favourites: %s", err)
            self.favourites.failed(box_state.box.id)

    # ------------------------------------------------------------ repeat

    def repeat_mode(self, box_id: str) -> repeat.Mode | None:
        """Return the repeat set for the figure on a box."""
        kept = self.preferences.repeat.get(box_id)
        if kept is None:
            return None
        return "all" if kept[0] == "all" else "one"

    def set_repeat(self, box_id: str, mode: repeat.Mode | None) -> BoxState:
        """Set or end the repeat of the figure on a Toniebox 2."""
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        if not box_state.box.live:
            raise BoxError("not_supported")
        if mode is None:
            self.preferences.set_repeat(box_id, None)
        elif box_state.tonie_id is None:
            raise BoxError("nothing_plays")
        else:
            self.preferences.set_repeat(box_id, mode, box_state.tonie_id)
        self.async_update_listeners()
        return box_state

    def _drop_stale_repeats(self, state: CloudState) -> None:
        """End the repeats kept for a box that left, or for a figure another one replaced."""
        for box_id, (_mode, tonie_id) in list(self.preferences.repeat.items()):
            box_state = state.boxes.get(box_id)
            placed = box_state.tonie_id if box_state is not None else None
            if box_state is None or (placed is not None and placed != tonie_id):
                self.preferences.set_repeat(box_id, None)

    def _observe_repeat(
        self, box_state: BoxState, playback: Playback, action: Action | None
    ) -> int | None:
        """Take a playback report; return the chapter to play again from its start, if any.

        With favourites at work, "all" starts again at the first chapter of
        their order once that order has ended, instead of pausing there or
        at the end of the figure.
        """
        box_id = box_state.box.id
        last = self._repeat_last.get(box_id)
        if playback.tonie_id is None:
            # The repeat belongs to the figure: it ends when the figure is taken off
            self.preferences.set_repeat(box_id, None)
            self._repeat_last.pop(box_id, None)
            return None
        self._repeat_last[box_id] = playback
        kept = self.preferences.repeat.get(box_id)
        if kept is not None and kept[1] != playback.tonie_id:
            # Another figure meanwhile, while Home Assistant did not look
            self.preferences.set_repeat(box_id, None)
        mode = self.repeat_mode(box_id)
        if mode is None:
            return None
        again = repeat.decide(mode, playback, last)
        first = self.runs(box_id).first(box_id, playback.tonie_id)
        if mode == "all" and first is not None:
            if action is not None and action[0] != "pause":
                # The order goes on: nothing ended yet
                again = None
            elif again is not None or action is not None:
                again = first
        if again is not None:
            self.runs(box_id).chosen(box_id, playback.tonie_id, again)
            _LOGGER.debug("Repeat %s: chapter %s plays from its start", mode, again + 1)
        return again

    async def _async_play_from(self, box_state: BoxState, chapter: int) -> None:
        """Send the box to the start of a chapter and let it play."""
        mac = box_state.box.mac
        if mac is None:
            return
        try:
            await self.push.async_set_position(mac, chapter, 0)
            await self.push.async_play(mac)
        except CloudError as err:
            _LOGGER.debug("The box was not sent back for the repeat: %s", err)
            # The favourites judge the next report anew: a pause the repeat took the
            # place of is sent after all, and the repeat gets its next try with it
            self.chapter_unchosen(box_state, chapter)
            self.runs(box_state.box.id).failed(box_state.box.id)

    # ------------------------------------------------------------ commands of the page

    async def async_box_command(
        self, box_id: str, command: str, value: int | None, tonie_id: str | None = None
    ) -> None:
        """Send a player command from the page to a Toniebox 2.

        play, pause, next, previous (chapters), chapter (its index from 0),
        volume (level 0 to 13), sleep (minutes), sleep_clear. The sleep timer is refused while the alarm of
        a bedtime is due, as the media player's actions are.
        """
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        mac = box_state.box.mac
        if not box_state.box.live or mac is None:
            raise BoxError("not_supported")
        if command in ("sleep", "sleep_clear") and self.due_alarm(box_id) is not None:
            raise BoxError("alarm_due")
        playback = box_state.playback
        if command in ("next", "previous"):
            if playback is None or playback.tonie_id is None:
                raise BoxError("nothing_plays")
            chapter = self.chapter_step(box_state, 1 if command == "next" else -1)
            try:
                await self.push.async_set_position(mac, chapter, 0)
            except CloudError:
                self.chapter_unchosen(box_state, chapter)
                raise
        elif command == "chapter" and value is not None:
            # Before the box itself reports, the figure the cloud names counts
            if box_state.tonie_id is None:
                raise BoxError("nothing_plays")
            # A chapter meant for one figure does not play another one's, nor a Tune's
            if tonie_id is not None and box_state.tonie_id != tonie_id:
                raise BoxError("other_figure")
            if tonie_id is not None and self.tune_on(tonie_id) is not None:
                raise BoxError("tune_plays")
            tonie = self.tonie(box_state.tonie_id)
            if tonie is None or value >= len(tonie.chapters):
                raise BoxError("unknown_chapter")
            self.chapter_chosen(box_state, value)
            try:
                await self.push.async_set_position(mac, value, 0)
            except CloudError:
                self.chapter_unchosen(box_state, value)
                raise
        elif command == "play":
            await self.push.async_play(mac)
        elif command == "pause":
            await self.push.async_pause(mac)
        elif command == "volume" and value is not None:
            await self.push.async_set_volume(mac, value)
        elif command == "sleep" and value is not None:
            await self.push.async_set_sleep_timer(mac, value * 60)
        elif command == "sleep_clear":
            await self.push.async_clear_sleep_timer(mac)
        else:
            raise BoxError("invalid_command")

    # ------------------------------------------------------------ night mode

    async def async_set_night_mode(self, box_id: str, mode: NightMode) -> BoxState:
        """Keep the night mode of a Toniebox 2 and set the light ring as it asks now."""
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        if not box_state.box.live:
            raise BoxError("not_supported")
        before = self.night_modes.get(box_id)
        mode = await self.night_modes.async_set(box_id, mode)
        if not mode.enabled and before is not None and before.applied == "night":
            # Switched off at night: the light ring comes back now, not at the end of the span
            await self.night_modes.async_applied(box_id, "night")
        self._check_night(box_state)
        self.async_update_listeners()
        return box_state

    def night_phase(self, box_state: BoxState) -> night.Phase | None:
        """Return the phase the night mode of a box is in now; None without one."""
        mode = self.night_modes.get(box_state.box.id)
        if mode is None or not mode.enabled:
            return None
        return night.phase(mode, self.now_at(box_state.box))

    @callback
    def _check_night(self, box_state: BoxState) -> None:
        """Set the light ring when the phase changed since the last time, and wait for the next."""
        box = box_state.box
        mode = self.night_modes.get(box.id)
        if (cancel := self._night_timers.pop(box.id, None)) is not None:
            cancel()
        if mode is None or not box.live:
            return
        if mode.enabled:
            now = self.now_at(box)
            wanted: night.Phase = night.phase(mode, now)

            @callback
            def _next(_now: datetime) -> None:
                self._night_timers.pop(box.id, None)
                if self.data is not None and (current := self.data.boxes.get(box.id)) is not None:
                    self._check_night(current)

            self._night_timers[box.id] = async_track_point_in_utc_time(
                self.hass, _next, dt_util.as_utc(night.next_change(mode, now))
            )
        elif mode.applied == "night":
            wanted = "day"
        else:
            return
        if wanted == mode.applied or box.id in self._night_busy:
            return
        self._night_busy.add(box.id)
        self.config_entry.async_create_background_task(
            self.hass, self._async_apply_night(box_state, wanted), f"{DOMAIN} night mode"
        )

    async def _async_apply_night(self, box_state: BoxState, wanted: night.Phase) -> None:
        box_id = box_state.box.id
        try:
            mode = self.night_modes.get(box_id)
            if mode is None:
                return
            value = night.brightness(mode, wanted)
            try:
                answer = await self.client.async_update_box(
                    box_state.box, {"lightringBrightness": value}
                )
            except CloudError as err:
                # The next poll tries again
                _LOGGER.debug("The light ring of a box was not set for the %s: %s", wanted, err)
                return
            if answer is not None:
                box_state.box = answer
            await self.night_modes.async_applied(box_id, wanted)
            _LOGGER.debug("Light ring set to %s %% for the %s", value, wanted)
            self.async_update_listeners()
        finally:
            self._night_busy.discard(box_id)

    @callback
    def _cancel_night_timers(self) -> None:
        for cancel in self._night_timers.values():
            cancel()
        self._night_timers.clear()

    # ------------------------------------------------------------ alarm

    def now_at(self, box: Box) -> datetime:
        """Return the time in the box's own zone; the schedules are local to the box."""
        zone = dt_util.get_time_zone(box.timezone) if box.timezone else None
        return dt_util.now(zone)

    def due_alarm(self, box_id: str) -> bedtime.NextAlarm | None:
        """Return the alarm the integration arms on the box now, or has armed."""
        box_state = self.data.boxes.get(box_id)
        return self._due(box_state) if box_state is not None else None

    def next_alarm(self, box_state: BoxState) -> bedtime.NextAlarm | None:
        """Return the next wake-up of a box: of its schedules or of its wake-up light."""
        if not box_state.box.alarm_capable:
            return None
        return bedtime.next_alarm(
            box_state.schedules, self.now_at(box_state.box), self.wake_up_light(box_state.box.id)
        )

    def wake_up_light(self, box_id: str) -> bedtime.OneTimeAlarm | None:
        """Return the wake-up light of a box, unless its time has passed."""
        light = self.preferences.wake_up_light.get(box_id)
        return light if light is not None and light.at > dt_util.utcnow() else None

    def _due(self, box_state: BoxState) -> bedtime.NextAlarm | None:
        if not box_state.box.alarm_capable:
            return None
        return bedtime.due(
            box_state.schedules, self.now_at(box_state.box), self.wake_up_light(box_state.box.id)
        )

    @callback
    def _check_alarm_later(self, box_id: str, delay: timedelta) -> None:
        """Look at the alarm of a box again after a while; a later request replaces it."""

        @callback
        def _check(_now: datetime) -> None:
            self._alarm_timers.pop(box_id, None)
            if self.data is not None and (box_state := self.data.boxes.get(box_id)) is not None:
                self._check_alarm(box_state, self.data)

        if (cancel := self._alarm_timers.pop(box_id, None)) is not None:
            cancel()
        self._alarm_timers[box_id] = async_call_later(self.hass, delay, _check)

    def _note_asleep_later(self, box_id: str) -> None:
        """Tell the favourites that a box sleeps, once it stayed offline for a moment.

        A box that wakes reports "offline" once more among its first
        messages; only one that is still offline after a while went to sleep.
        """
        went = dt_util.utcnow().timestamp()

        @callback
        def _look(_now: datetime) -> None:
            self._asleep_timers.pop(box_id, None)
            box_state = self.data.boxes.get(box_id) if self.data is not None else None
            if box_state is not None and box_state.online is False:
                self.runs(box_id).away(box_id, went)

        if (cancel := self._asleep_timers.pop(box_id, None)) is not None:
            cancel()
        self._asleep_timers[box_id] = async_call_later(self.hass, ASLEEP_AFTER, _look)

    @callback
    def _cancel_asleep_timers(self) -> None:
        for cancel in self._asleep_timers.values():
            cancel()
        self._asleep_timers.clear()

    @callback
    def _cancel_alarm_timers(self) -> None:
        for cancel in self._alarm_timers.values():
            cancel()
        self._alarm_timers.clear()

    @callback
    def _check_alarm(self, box_state: BoxState, state: CloudState) -> None:
        """Arm the due alarm of a box, or clear a stale one of ours, if the box listens now."""
        box = box_state.box
        if not box.alarm_capable or box.mac is None:
            return
        now = dt_util.utcnow()
        light = self.preferences.wake_up_light.get(box.id)
        if light is not None and light.at <= now:
            # It rang (or the box was off then): a wake-up light rings once
            self.preferences.set_wake_up_light(box.id, None)
        armed = self._armed.get(box.id)
        if armed is not None and armed <= now:
            # It rang (or the box was off): nothing of ours is armed any more
            self._armed.pop(box.id, None)
            armed = None
        step = bedtime.decide(self._due(box_state), box_state.sleep_timer, armed)
        if step is None or not state.push_connected or box_state.online is not True:
            return
        if step[0] == "arm" and step[1].at - now < bedtime.LEAD:
            # The box would drop it: an alarm that came online too late is missed
            return
        if box_state.online_since is not None and now - box_state.online_since < bedtime.SETTLE:
            self._check_alarm_later(box.id, bedtime.SETTLE - (now - box_state.online_since))
            return
        sent = self._alarm_sent.get(box.id)
        if sent is not None and now - sent < bedtime.RETRY:
            return
        # A box that does not confirm is not asked forever: a few times per time online
        target = step[1].at if step[0] == "arm" else None
        tried_for, tries = self._alarm_tries.get(box.id, (None, 0))
        tries = tries + 1 if tried_for == target else 1
        self._alarm_tries[box.id] = (target, tries)
        if tries > bedtime.TRIES:
            if tries == bedtime.TRIES + 1:
                _LOGGER.warning(
                    "The box %s did not confirm its alarm; it is tried again when it comes online",
                    box.name,
                )
            return
        self._alarm_sent[box.id] = now
        self.config_entry.async_create_background_task(
            self.hass, self._async_alarm_step(box_state, step), f"{DOMAIN} alarm"
        )

    async def _async_alarm_step(self, box_state: BoxState, step: bedtime.Step) -> None:
        mac = box_state.box.mac
        if mac is None:
            return
        try:
            if step[0] == "arm":
                alarm = step[1]
                seconds = round((alarm.at - dt_util.utcnow()).total_seconds())
                # Checked a moment ago; a few seconds late beats a dropped alarm
                seconds = max(seconds, round(bedtime.LEAD.total_seconds()))
                await self.push.async_set_alarm(mac, seconds, alarm.alarm)
                self._armed[box_state.box.id] = alarm.at
                _LOGGER.debug("Alarm armed for %s", alarm.at.isoformat())
            else:
                await self.push.async_clear_sleep_timer(mac)
                self._armed.pop(box_state.box.id, None)
                _LOGGER.debug("An alarm no schedule wants any more was cleared")
        except CloudError as err:
            _LOGGER.debug("The alarm of a box was not sent: %s", err)
        # Should the box not confirm, the next check asks again after the retry time
        self._check_alarm_later(box_state.box.id, bedtime.RETRY + timedelta(seconds=5))

    async def async_save_schedule(
        self, box_id: str, schedule_id: str | None, fields: dict[str, Any]
    ) -> BoxState:
        """Create or change a bedtime schedule of a box, then read them again."""
        box_state = self._alarm_box(box_id)
        if schedule_id is not None and not any(
            s.id == schedule_id for s in box_state.schedules or ()
        ):
            raise BoxError("unknown_schedule")
        await self.client.async_save_bedtime_schedule(box_state.box, schedule_id, fields)
        return await self._async_schedules_changed(box_state)

    async def async_delete_schedule(self, box_id: str, schedule_id: str) -> BoxState:
        """Delete a bedtime schedule of a box, then read them again."""
        box_state = self._alarm_box(box_id)
        if not any(s.id == schedule_id for s in box_state.schedules or ()):
            raise BoxError("unknown_schedule")
        await self.client.async_delete_bedtime_schedule(box_state.box, schedule_id)
        return await self._async_schedules_changed(box_state)

    async def async_change_settings(self, box_id: str, changes: dict[str, Any]) -> BoxState:
        """Change the name or settings of a box (our names) and keep what the cloud answers.

        A setting the box does not have (one of the other generation, or one
        behind a feature flag the box lacks) is refused before the cloud is asked.
        """
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        box = box_state.box
        fields: dict[str, Any] = {}
        for name, value in changes.items():
            if name == "name":
                fields["name"] = value
                continue
            if not setting_supported(box, name):
                raise BoxError("not_supported")
            if name in STEPPED_SETTINGS and not box.live and value not in VOLUME_STEPS:
                raise BoxError("invalid_value")
            fields[SETTING_FIELDS[name][0]] = value
        answer = await self.client.async_update_box(box, fields)
        if answer is None:
            answer = await self.client.async_box(box)
        if answer is not None:
            box_state.box = answer
        self._follow_box_names(self.data)
        self.async_update_listeners()
        return box_state

    async def async_set_wake_up_light(self, box_id: str, at: datetime, alarm: Alarm) -> BoxState:
        """Set the wake-up light of a box: one alarm at that time; a former one is replaced.

        It is armed as soon as it is within the timer's reach and the box is
        online, unless a schedule's alarm rings before it.
        """
        box_state = self._alarm_box(box_id)
        if at - dt_util.utcnow() < bedtime.LEAD:
            raise BoxError("alarm_too_soon")
        self._forget_light(box_state)
        self.preferences.set_wake_up_light(box_id, bedtime.OneTimeAlarm(at, alarm))
        _LOGGER.info("Wake-up light of %s set for %s", box_state.box.name, at.isoformat())
        return self._alarms_changed(box_state)

    async def async_clear_wake_up_light(self, box_id: str) -> BoxState:
        """Drop the wake-up light of a box, and its alarm on the box if armed."""
        box_state = self._alarm_box(box_id)
        if self._forget_light(box_state):
            _LOGGER.info("Wake-up light of %s cleared", box_state.box.name)
        return self._alarms_changed(box_state)

    def _forget_light(self, box_state: BoxState) -> bool:
        """Drop the wake-up light of a box; an alarm the box carries for it counts as ours.

        After a restart the integration no longer knows what it armed; the
        box's timer for the light's time is taken as its own, so the next
        check clears it unless another alarm takes its place.
        """
        light = self.preferences.wake_up_light.get(box_state.box.id)
        if light is None:
            return False
        if bedtime.armed_for(box_state.sleep_timer, light.at):
            self._armed[box_state.box.id] = light.at
        self.preferences.set_wake_up_light(box_state.box.id, None)
        return True

    def _alarms_changed(self, box_state: BoxState) -> BoxState:
        """Act on a changed alarm at once, not after the retry time."""
        self._alarm_sent.pop(box_state.box.id, None)
        self._alarm_tries.pop(box_state.box.id, None)
        self._check_alarm(box_state, self.data)
        self.async_update_listeners()
        return box_state

    def _alarm_box(self, box_id: str) -> BoxState:
        box_state = self.data.boxes.get(box_id)
        if box_state is None:
            raise BoxError("unknown_box")
        if not box_state.box.alarm_capable:
            raise BoxError("no_alarm")
        return box_state

    async def _async_schedules_changed(self, box_state: BoxState) -> BoxState:
        await self._async_read_schedules(box_state)
        return self._alarms_changed(box_state)

    @callback
    def set_push_connected(self, connected: bool) -> None:
        """Note that the push channel came or went."""
        self.data.push_connected = connected
        if not connected:
            # Without the channel nothing is known about playing or being on; count no further
            for box_state in self.data.boxes.values():
                self._stop_playing(box_state)
            self.battery_stats.pause_all()
            self.battery_stats.save_soon()
        else:
            for box_state in self.data.boxes.values():
                self._check_alarm_later(box_state.box.id, bedtime.SETTLE)
        self.async_update_listeners()

    def counts_box(self, box_id: str) -> bool:
        """Return whether this account counts the listening time of a box (see box_owner).

        While this entry is being set up, it is not loaded yet; an older
        loaded entry with the box then counts it.
        """
        owner = box_owner(self.hass, box_id)
        return owner is None or owner is self.config_entry

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
        """Return whether the figure's chapter names are unknown and worth asking for."""
        return (
            tonie is not None
            and not tonie.chapters
            and tonie.id not in self._details
            and tonie.id not in self._details_missing
        )

    def _needs_lengths(self, tonie: Tonie | None) -> bool:
        """Return whether a box should be asked for the figure's chapters with lengths.

        The library names the chapters of bought figures but does not time
        them; the box the figure stands on tells both. Names already kept,
        from the library or from a box that knew no lengths either, do not
        answer the question and so do not stop the asking. A box that told
        nothing is asked again an hour later, or when the figure is placed
        anew. Creative figures are never asked for: the cloud times them.
        """
        if tonie is None or tonie.kind is TonieKind.CREATIVE:
            return False
        asked = self._lengths_asked.get(tonie.id)
        if asked is not None and dt_util.utcnow() - asked < LENGTHS_RETRY:
            return False
        if any(c.seconds for c in tonie.chapters):
            return False
        details = self._details.get(tonie.id)
        return details is None or not any(c.seconds for c in details.chapters)

    def _with_details(self, tonie: Tonie) -> Tonie:
        """Fill in what the box told about the figure, where the library is silent.

        Creative figures stay as the cloud describes them: their chapters
        carry the IDs that rearranging them needs.
        """
        details = self._details.get(tonie.id)
        if details is None or tonie.kind is TonieKind.CREATIVE:
            return tonie
        return replace(
            tonie,
            # Chapters learned from a box carry their lengths; the library's only names
            chapters=details.chapters or tonie.chapters,
            series=tonie.series or details.series,
            image_url=tonie.image_url or details.image_url,
        )

    async def _async_fetch_details(self, box_id: str, tonie_id: str, named: bool) -> bool:
        """Ask the cloud for the chapters of the figure on a box; True when learned.

        ``named`` says whether the library already names the chapters: then
        only lengths are worth keeping.
        """
        box_state = self.data.boxes.get(box_id) if self.data else None
        playback = box_state.playback if box_state else None
        version = playback.content_version if playback and playback.content_version else 0
        try:
            details = await self.client.async_playback_info(box_id, tonie_id, version)
        except CloudError as err:
            _LOGGER.debug("Chapters of a figure not read: %s", err)
            return False
        if details is None or not details.chapters:
            _LOGGER.debug(
                "No chapters for a figure (status %s, content version %s)",
                details.status if details else None,
                version,
            )
            # "outdated" means the box's version was not the latest: worth asking again
            if details is None or details.status != "outdated":
                self._lengths_asked[tonie_id] = dt_util.utcnow()
            return False
        if not any(c.seconds for c in details.chapters):
            # Names without lengths: kept only where nothing names them yet, asked again later
            _LOGGER.debug("The box named the chapters of a figure but did not time them")
            self._lengths_asked[tonie_id] = dt_util.utcnow()
            if named or tonie_id in self._details:
                return False
        self._details[tonie_id] = details
        self._details_store.async_delay_save(self._details_to_save, 10)
        return True

    async def _async_ask_library_details(self, tonies: dict[str, Tonie]) -> None:
        """Ask the app's detail query for a few bought figures still without chapters.

        Needed only when the library query came back without chapters; a
        handful per poll keeps the cloud traffic small.
        """
        waiting = [
            t for t in tonies.values() if t.kind is TonieKind.CONTENT and self._needs_details(t)
        ][:DETAILS_PER_POLL]
        for tonie in waiting:
            try:
                detail = await self.client.async_content_tonie(tonie.household_id, tonie.id)
            except CloudError as err:
                _LOGGER.debug("Detail of a figure not read: %s", err)
                return
            if detail is None or not detail.chapters:
                self._details_missing.add(tonie.id)
                continue
            self._details[tonie.id] = TonieDetails(
                title=detail.name,
                series=detail.series,
                image_url=detail.image_url,
                chapters=detail.chapters,
                status="available",
            )
            self._details_store.async_delay_save(self._details_to_save, 10)

    async def _async_details_for_placement(self, box_id: str, tonie_id: str) -> None:
        """A figure with unknown chapters was placed: learn them and tell the entities."""
        tonie = self.data.tonies.get(tonie_id)
        named = bool(tonie and tonie.chapters)
        if (
            await self._async_fetch_details(box_id, tonie_id, named)
            and tonie_id in self.data.tonies
        ):
            self.data.tonies[tonie_id] = self._with_details(self.data.tonies[tonie_id])
            self.async_update_listeners()

    def _details_to_save(self) -> dict[str, Any]:
        return {"tonies": {tonie_id: _details_to_dict(d) for tonie_id, d in self._details.items()}}

    # --------------------------------------------------- creative figures

    def _creative(self, tonie_id: str) -> Tonie:
        """Return the creative figure, or refuse: only those take chapters."""
        tonie = self.data.tonies.get(tonie_id)
        if tonie is None:
            raise ChapterError("unknown_figure")
        if tonie.kind is not TonieKind.CREATIVE:
            raise ChapterError("not_creative")
        return tonie

    async def async_arrange_chapters(
        self, tonie_id: str, chapter_ids: list[str], titles: dict[str, str] | None = None
    ) -> Tonie:
        """Keep only the named chapters of a creative figure, in the given order.

        titles renames chapters by their ID; a new title converts nothing.

        Order and deletions go to the cloud in one request, because every
        change makes the cloud convert the whole figure again.
        """
        tonie = self._creative(tonie_id)
        by_id = {c.id: c for c in tonie.chapters}
        if len(set(chapter_ids)) != len(chapter_ids) or any(c not in by_id for c in chapter_ids):
            raise ChapterError("unknown_chapter")
        titles = titles or {}
        if any(c not in by_id for c in titles):
            raise ChapterError("unknown_chapter")
        chapters = [
            replace(by_id[c], title=titles[c][:CHAPTER_TITLE_MAX]) if c in titles else by_id[c]
            for c in chapter_ids
        ]
        answer = await self.client.async_set_chapters(tonie.household_id, tonie_id, chapters)
        return await self._async_take_creative(tonie, answer)

    async def async_update_figure(self, tonie_id: str, fields: dict[str, Any]) -> Tonie:
        """Change name or live mode of a creative figure (the cloud's names).

        Bought figures and discs keep the name they came with.
        """
        tonie = self._creative(tonie_id)
        answer = await self.client.async_update_creative(tonie.household_id, tonie_id, fields)
        return await self._async_take_creative(tonie, answer)

    async def async_add_chapter(
        self, tonie_id: str, title: str, data: bytes, filename: str, content_type: str
    ) -> Tonie:
        """Upload an audio file and append it as a chapter of a creative figure.

        A figure a Tune lies on takes no chapters: the cloud would answer, but
        the chapter would not play and could be lost. The Tunes are read anew
        first, since a Tune may have been laid on in the app. The figure the
        cloud answers with must have the new chapter, or the upload counts as
        failed.
        """
        tonie = self._creative(tonie_id)
        await self.async_refuse_tune(tonie_id)
        _LOGGER.info("Adding chapter %r to %s", title, self._figure_name(tonie_id))
        file_id = await self.client.async_upload_file(data, filename, content_type)
        answer = await self.client.async_add_chapter(tonie.household_id, tonie_id, title, file_id)
        figure = await self._async_take_creative(tonie, answer)
        if not any(c.file == file_id for c in figure.chapters) and len(figure.chapters) <= len(
            tonie.chapters
        ):
            _LOGGER.warning(
                "The cloud answered chapter %r of %s without it: %s chapters before, %s after",
                title,
                self._figure_name(tonie_id),
                len(tonie.chapters),
                len(figure.chapters),
            )
            raise ChapterError("chapter_missing")
        _LOGGER.info(
            "Chapter %r is on %s, now %s chapters",
            title,
            self._figure_name(tonie_id),
            len(figure.chapters),
        )
        return figure

    async def async_refuse_tune(self, tonie_id: str) -> None:
        """Refuse a change of chapters while a Tune lies on the figure, after reading the Tunes."""
        await self._async_read_tunes()
        if (on := self.tune_on(tonie_id)) is not None:
            _LOGGER.info(
                "%s carries Tune %r: no chapters added", self._figure_name(tonie_id), on.title
            )
            raise ChapterError(
                "tune_on", f"The Tune {on.title!r} lies on the figure; take it off first"
            )

    async def async_add_chapter_from_link(
        self,
        tonie_id: str,
        url: str,
        progress: Callable[[dict[str, Any]], None],
        cancelled: asyncio.Event,
    ) -> Tonie:
        """Fetch the audio of a video through the Media Fetcher app and append it as a chapter.

        The progress callback hears what happens: the video being read
        ("probe"), the download with its bytes, the conversion, the upload.
        A video that does not fit into the figure's free time is refused
        before anything is fetched. Setting the event gives up a running
        job; an upload that has begun completes.
        """
        tonie = self._creative(tonie_id)
        try:
            link = URL(url)
        except ValueError:
            link = None
        if link is None or link.scheme not in ("http", "https") or not link.host:
            raise ChapterError("invalid_url")
        app = await fetcher.async_find(self.hass)
        if app is None:
            raise ChapterError("fetcher_missing")
        await self.async_refuse_tune(tonie_id)
        client = fetcher.FetcherClient(self.hass, app, self.preferences.fetch_max_bytes)
        progress({"stage": "probe"})
        _LOGGER.info("Fetching a link for %s through %s", self._figure_name(tonie_id), app.host)
        video = await client.async_info(url)
        _LOGGER.info("The link is %r (%s s)", video.title, video.seconds)
        free = tonie.seconds_remaining
        if free is not None and video.seconds is not None and video.seconds > free:
            raise ChapterError(
                "too_long",
                f"The video lasts {_clock(video.seconds)}, the figure has {_clock(free)} left",
            )
        about = {"title": video.title, "seconds": video.seconds}

        def report(job: fetcher.Job) -> None:
            stage = "convert" if job.state == "converting" else "download"
            progress({"stage": stage, **about, "done": job.done, "total": job.total})

        progress({"stage": "download", **about, "done": 0, "total": None})
        job_id = await client.async_start(url, round(free) if free is not None else None)
        try:
            job = await client.async_wait(job_id, report, cancelled)
            data = await client.async_file(job_id)
        finally:
            await client.async_forget(job_id)
        _LOGGER.info(
            "Media Fetcher job %s gave %.1f MB of %s", job_id, len(data) / 1e6, job.content_type
        )
        progress({"stage": "upload", **about, "done": 0, "total": len(data)})
        return await self.async_add_chapter(
            tonie_id,
            video.title,
            data,
            f"{video.id}.{fetcher.FORMAT}",
            job.content_type or fetcher.CONTENT_TYPE,
        )

    async def async_add_chapter_from_text(self, tonie_id: str, text: str, title: str) -> Tonie:
        """Let the account's voice speak a text and append it as a chapter of a creative figure.

        Refused when no voice can speak, before anything is spoken.
        """
        tonie = self._creative(tonie_id)
        engine = speech.find_engine(self.hass, self.preferences.speech_engine)
        if engine is None:
            raise ChapterError("speech_missing")
        try:
            extension, data = await speech.async_speak(
                self.hass,
                engine,
                text,
                self.preferences.voice,
                self.preferences.voice_language,
            )
        except speech.SpeechError as err:
            raise ChapterError(
                "speech_failed", f"The voice could not speak the text: {err}"
            ) from err
        content_type = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg"}.get(
            extension, "audio/mpeg"
        )
        return await self.async_add_chapter(
            tonie.id, title, data, f"text.{extension}", content_type
        )

    async def async_refresh_creative(self, tonie_id: str) -> Tonie:
        """Read one creative figure again, while the cloud converts its chapters."""
        tonie = self._creative(tonie_id)
        return await self._async_take_creative(tonie, None)

    async def _async_take_creative(self, before: Tonie, answer: Tonie | None) -> Tonie:
        """Keep what the cloud answered about a creative figure and tell the entities."""
        if answer is None:
            answer = await self.client.async_creative_tonie(before.household_id, before.id)
        if answer is None:
            raise ChapterError("unknown_figure")
        self.data.tonies[answer.id] = answer
        self.async_update_listeners()
        return answer

    # ------------------------------------------------------------ helpers

    def tonie(self, tonie_id: str | None) -> Tonie | None:
        """Return the figure with the ID, if known."""
        if tonie_id is None:
            return None
        return self.data.tonies.get(tonie_id)


def _first_entry(
    hass: HomeAssistant, has: Callable[[CloudState], bool]
) -> StoryboxConfigEntry | None:
    entries: list[StoryboxConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    for entry in entries:
        data = entry.runtime_data.coordinator.data
        if data is not None and has(data):
            return entry
    return None


def box_owner(hass: HomeAssistant, box_id: str) -> StoryboxConfigEntry | None:
    """Return the account that speaks for a box on the page and counts its listening time.

    Members of one household who each add their own account all see its
    boxes and figures. The oldest loaded entry that has one speaks for it,
    so the page shows it once and its listening time is counted once.
    """
    return _first_entry(hass, lambda data: box_id in data.boxes)


def tonie_owner(hass: HomeAssistant, tonie_id: str) -> StoryboxConfigEntry | None:
    """Return the account that speaks for a figure on the page (see box_owner)."""
    return _first_entry(hass, lambda data: tonie_id in data.tonies)


def setting_supported(box: Box, name: str) -> bool:
    """Return whether a box has a setting: by its generation and its feature flags."""
    if name not in SETTING_FIELDS:
        return False
    if name in LIVE_SETTINGS and not box.live:
        return False
    if name in CLASSIC_SETTINGS and box.live:
        return False
    feature = FEATURE_SETTINGS.get(name)
    return feature is None or feature in box.features


def _clock(seconds: float) -> str:
    """Seconds as h:mm:ss, for a message."""
    whole = round(seconds)
    return f"{whole // 3600}:{whole % 3600 // 60:02d}:{whole % 60:02d}"


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
