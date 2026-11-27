"""What the cloud knows, as plain immutable values.

Only the fields the integration uses are parsed; the parsers accept missing
fields, because the cloud's API is not documented for third parties and has
changed shape before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import time
from typing import Any

# The highest volume level of a box; the app shows levels, not percent.
VOLUME_LEVELS = 13
# The days of a bedtime schedule, as the cloud names them
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# The alarm tone the app uses unless another is chosen
DEFAULT_ALARM_TONE = "alarmLoop1.opus"


class Generation(StrEnum):
    """The two kinds of box the cloud distinguishes."""

    CLASSIC = "classic"
    TONIEBOX_2 = "toniebox_2"


class TonieKind(StrEnum):
    """What a figure is."""

    CONTENT = "content"
    CREATIVE = "creative"
    DISC = "disc"


@dataclass(frozen=True, slots=True)
class Household:
    """A household of the account; boxes and figures belong to one."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Chapter:
    """One chapter of a figure."""

    id: str
    title: str
    seconds: float | None = None
    transcoding: bool = False
    file: str | None = None


@dataclass(frozen=True, slots=True)
class Tonie:
    """A figure: bought content, a creative figure or a disc."""

    id: str
    household_id: str
    kind: TonieKind
    name: str
    series: str | None = None
    image_url: str | None = None
    language: str | None = None
    locked: bool = False
    chapters: tuple[Chapter, ...] = ()
    seconds_remaining: float | None = None
    chapters_remaining: int | None = None
    transcoding: bool = False
    # Why the last conversion of a creative figure dropped chapters: "wrongFormat",
    # "tooLong" or "unknownError", as the cloud names them
    transcoding_errors: tuple[str, ...] = ()
    # The length of the content as the library states it, where the chapters carry none
    seconds_total: float | None = None
    # Creative figures only: the newest chapter plays first (live mode)
    live: bool | None = None

    @property
    def seconds(self) -> float:
        """Return the total length of the content."""
        if self.seconds_total is not None:
            return self.seconds_total
        return sum(c.seconds or 0 for c in self.chapters)


@dataclass(frozen=True, slots=True)
class TonieDetails:
    """What the cloud tells about a figure once it stands on a box (playback info).

    status: "available" with the chapters, "outdated" when the box's content
    version is behind (chapters missing), "unavailable" when the cloud has none.
    """

    title: str | None = None
    series: str | None = None
    image_url: str | None = None
    chapters: tuple[Chapter, ...] = ()
    status: str | None = None


# The settings of a box the API takes, by our name: the API's name and the values it allows
# (a tuple of choices, a (min, max) range, or bool). The maximum volumes are
# documented as 25/50/75/100; a classic box keeps to that, a Toniebox 2 takes
# any percent (a real one reported 74 and 60).
VOLUME_STEPS = (25, 50, 75, 100)
STEPPED_SETTINGS = frozenset({"max_volume", "max_headphone_volume"})
SETTING_FIELDS: dict[str, tuple[str, Any]] = {
    "max_volume": ("maxVolume", (1, 100)),
    "max_headphone_volume": ("maxHeadphoneVolume", (1, 100)),
    "lightring_brightness": ("lightringBrightness", (0, 100)),
    "bedtime_lightring_brightness": ("bedtimeLightringBrightness", (0, 100)),
    "bedtime_max_volume": ("bedtimeMaxVolume", (1, 100)),
    "bedtime_max_headphone_volume": ("bedtimeMaxHeadphoneVolume", (1, 100)),
    "skipping_enabled": ("skippingEnabled", bool),
    "skipping_direction": ("skippingDirection", ("left", "right")),
    "scrubbing_enabled": ("scrubbingEnabled", bool),
    "accelerometer_enabled": ("accelerometerEnabled", bool),
    "tap_direction": ("tapDirection", ("left", "right")),
    "led_level": ("ledLevel", ("on", "dimmed", "off")),
    "age_mode": ("ageMode", ("1+", "3+")),
    "language": ("language", ("de", "en", "en-us", "fr")),
}
# The settings only a Toniebox 2 has (feature tngSettings), and those only the classic box has
LIVE_SETTINGS = frozenset(
    {
        "lightring_brightness",
        "bedtime_lightring_brightness",
        "bedtime_max_volume",
        "bedtime_max_headphone_volume",
        "skipping_enabled",
        "skipping_direction",
        "scrubbing_enabled",
    }
)
CLASSIC_SETTINGS = frozenset({"accelerometer_enabled", "tap_direction", "led_level"})
# Settings a box has only with its feature flag
FEATURE_SETTINGS = {"age_mode": "ageMode", "language": "language"}


@dataclass(frozen=True, slots=True)
class BoxSettings:
    """The settings of a box, as far as the cloud names them; None where it does not."""

    max_volume: int | None = None
    max_headphone_volume: int | None = None
    lightring_brightness: int | None = None
    bedtime_lightring_brightness: int | None = None
    bedtime_max_volume: int | None = None
    bedtime_max_headphone_volume: int | None = None
    skipping_enabled: bool | None = None
    skipping_direction: str | None = None
    scrubbing_enabled: bool | None = None
    accelerometer_enabled: bool | None = None
    tap_direction: str | None = None
    led_level: str | None = None
    age_mode: str | None = None
    language: str | None = None
    # Read only: the box does not contact the internet; the box has the latest settings
    offline_mode: bool | None = None
    settings_applied: bool | None = None


@dataclass(frozen=True, slots=True)
class Box:
    """A box as the REST API describes it."""

    id: str
    household_id: str
    name: str
    mac: str | None
    generation: Generation
    online: bool | None = None
    last_seen: datetime | None = None
    firmware: str | None = None
    color_id: str | None = None
    # The picture the cloud names for the box itself (front view first)
    image_url: str | None = None
    placed_tonie_id: str | None = None
    settings: BoxSettings = field(default_factory=BoxSettings)
    raw_generation: str | None = None
    # The box rings an alarm at the end of its sleep timer (feature sleepTimerAlarm)
    alarm_capable: bool = False
    # The box's own time zone; the times of its bedtime schedules are local to it
    timezone: str | None = None
    # The feature flags as the cloud lists them, for the diagnostics
    features: tuple[str, ...] = ()

    @property
    def live(self) -> bool:
        """Return whether the box has the push channel (Toniebox 2)."""
        return self.generation is Generation.TONIEBOX_2


@dataclass(frozen=True, slots=True)
class Library:
    """Everything the REST API tells about the account, in one snapshot."""

    households: tuple[Household, ...]
    boxes: tuple[Box, ...]
    tonies: tuple[Tonie, ...]


@dataclass(frozen=True, slots=True)
class Battery:
    """The battery of a Toniebox 2, from the push channel."""

    percent: int | None
    charging: bool | None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class Volume:
    """The volume of a Toniebox 2, from the push channel.

    The box is set in levels; it also reports what a level means for its
    loudness in percent (seen: level 1 is 5 %, 7 is 50 %, 8 is 60 %).
    """

    level: int | None
    percent: int | None = None

    @property
    def fraction(self) -> float | None:
        """Return the loudness as 0..1: the box's percent, else the level."""
        if self.percent is not None:
            return max(0.0, min(1.0, self.percent / 100))
        if self.level is None:
            return None
        return max(0.0, min(1.0, self.level / VOLUME_LEVELS))


@dataclass(frozen=True, slots=True)
class Playback:
    """What a Toniebox 2 plays, from the push channel.

    An empty message means the figure was taken off: tonie_id is None then.
    """

    tonie_id: str | None
    chapter: int | None = None
    paused: bool | None = None
    ended: bool | None = None
    downloading: bool | None = None
    duration: float | None = None
    position: float | None = None
    # The version of the content on the box; the cloud wants it to tell the chapters
    content_version: int | None = None
    # The message named the moment the chapter ends: the chapter runs. A box that has
    # just been given a figure says "downloading" for the whole chapter while it plays
    running: bool = False
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def playing(self) -> bool:
        """Return whether audio is playing right now.

        Not while the box only loads the content; a box that loads and names
        the end of the chapter plays it meanwhile.
        """
        return (
            self.tonie_id is not None
            and self.paused is False
            and not self.ended
            and (not self.downloading or self.running)
        )


@dataclass(frozen=True, slots=True)
class SleepTimer:
    """The sleep timer of a Toniebox 2, from the push channel."""

    state: str | None
    duration: int | None = None
    until: datetime | None = None
    # An alarm rings when the timer ends
    alarm: bool = False

    @property
    def running(self) -> bool:
        """Return whether the timer runs."""
        return self.state == "on"


@dataclass(frozen=True, slots=True)
class Headphones:
    """Headphones on a Toniebox 2, from the push channel (metrics/headphones)."""

    connected: bool
    # The kind the box names (bluetooth, cable …), and the battery of wireless ones
    kind: str | None = None
    battery: int | None = None


@dataclass(frozen=True, slots=True)
class Alarm:
    """How the alarm at the end of a sleep timer rings."""

    tone: str = DEFAULT_ALARM_TONE
    volume: int = 100
    morning_light: bool = True


@dataclass(frozen=True, slots=True)
class Tune:
    """A Tune the account bought: an audio play that can be laid on fitting figures.

    id is the account's own copy (myTune), which laying it on a figure names;
    assigned are the figures it lies on. Which ones it fits, the cloud names
    as compatible figures (bought ones) and with all_creative for every
    creative figure; suitable is the older, now mostly empty list of the copy.
    """

    id: str
    title: str
    image_url: str | None = None
    series: str | None = None
    seconds: float | None = None
    remaining: int | None = None
    assigned: tuple[str, ...] = ()
    suitable: tuple[str, ...] = ()
    compatible: tuple[str, ...] = ()
    all_creative: bool = False


@dataclass(frozen=True, slots=True)
class CloudNotice:
    """A notification the cloud keeps for the account, or a broadcast to all users.

    kind is the cloud's ``ntype`` (for example a figure whose conversion
    failed, an invitation), or "system" for a broadcast.
    """

    id: str
    text: str
    kind: str
    read: bool = False
    # The ID the cloud knows the notification by (id carries a prefix for broadcasts)
    cloud_id: str = ""
    timestamp: datetime | None = None
    tonie_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Member:
    """A member of a household, as the cloud shows it to the account.

    role is the cloud's ``mtype``: owner, full or limited. Name and email
    come only as far as the account may see them; display_name is always
    there (the first name or the email address).
    """

    id: str
    display_name: str
    role: str
    is_self: bool = False
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


MEMBER_ROLES = ("owner", "full", "limited")


@dataclass(frozen=True, slots=True)
class BedtimeSchedule:
    """A recurring bedtime of a Toniebox 2, as the app keeps it in the cloud.

    The times are "HH:MM" in the box's time zone. The schedule alone makes
    no box ring: the alarm has to be armed through the sleep timer every
    evening.
    """

    id: str
    name: str
    sleep_time: str | None
    wakeup_time: str | None
    days: tuple[str, ...] = ()
    enabled: bool = False
    alarm_enabled: bool = False
    alarm_tone: str | None = None
    alarm_volume: int | None = None
    alarm_morning_light: bool | None = None

    @property
    def alarm(self) -> Alarm:
        """Return how the alarm of this schedule rings."""
        return Alarm(
            tone=self.alarm_tone or DEFAULT_ALARM_TONE,
            volume=100 if self.alarm_volume is None else max(0, min(100, self.alarm_volume)),
            morning_light=True if self.alarm_morning_light is None else self.alarm_morning_light,
        )


# ---------------------------------------------------------------- parsing


def _text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return None if number is None else int(number)


def _flag(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def parse_datetime(value: Any) -> datetime | None:
    """Parse the cloud's timestamps: ISO 8601 strings or epoch seconds/milliseconds."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        seconds = value / 1000 if value > 1e11 else value
        try:
            return datetime.fromtimestamp(seconds, UTC)
        except OverflowError, OSError, ValueError:
            return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def normalize_mac(value: str | None) -> str | None:
    """Return the MAC as the push channel's topics spell it: upper case, as given."""
    if not value:
        return None
    return value.strip().upper()


# What the push channel and the REST API call a box that is there or not;
# the REST API answers "unsupported" for every box seen so far
_ONLINE_STATES = {"connected": True, "online": True, "disconnected": False, "offline": False}


def parse_household(data: dict[str, Any]) -> Household | None:
    """Parse one household of GET /households."""
    household_id = _text(data, "id")
    if household_id is None:
        return None
    return Household(id=household_id, name=_text(data, "name") or "Household")


def parse_box(data: dict[str, Any], household_id: str) -> Box | None:
    """Parse one box of GET /households/{id}/tonieboxes.

    The generation is read from the feature flag ``tngSettings``: the field
    ``generation`` names hardware revisions (``tng``, ``tb2g2``) that keep
    changing, the flag says what the box can do.
    """
    box_id = _text(data, "id")
    if box_id is None:
        return None
    raw_features = data.get("features")
    features = (
        tuple(f for f in raw_features if isinstance(f, str))
        if isinstance(raw_features, list)
        else ()
    )
    live = "tngSettings" in features
    online = _ONLINE_STATES.get((_text(data, "onlineState") or "").lower())
    placement = data.get("placement")
    placed: str | None = None
    if isinstance(placement, dict):
        tonie = placement.get("tonie")
        if isinstance(tonie, dict):
            placed = _text(tonie, "id")
        elif isinstance(tonie, str) and tonie:
            placed = tonie
    firmware = data.get("firmware")
    if isinstance(firmware, dict):
        firmware = _text(firmware, "version", "name")
    elif not isinstance(firmware, str):
        firmware = _text(data, "firmwareVersion")
    return Box(
        id=box_id,
        household_id=household_id,
        name=_text(data, "name") or "Toniebox",
        mac=normalize_mac(_text(data, "macAddress", "mac_address")),
        generation=Generation.TONIEBOX_2 if live else Generation.CLASSIC,
        online=online,
        last_seen=parse_datetime(data.get("lastSeen", data.get("last_seen"))),
        firmware=firmware or None,
        color_id=_color_id(data.get("bleColorId")),
        image_url=_text(data, "frontImageUrl", "imageUrl"),
        placed_tonie_id=placed,
        settings=parse_box_settings(data),
        raw_generation=_text(data, "generation"),
        alarm_capable=live and "sleepTimerAlarm" in features,
        timezone=_text(data, "timezone"),
        features=features,
    )


def parse_box_settings(data: dict[str, Any]) -> BoxSettings:
    """Take the settings the cloud names; a value of the wrong kind counts as unnamed."""
    values: dict[str, Any] = {}
    for name, (api, allowed) in SETTING_FIELDS.items():
        raw = data.get(api)
        if allowed is bool:
            values[name] = raw if isinstance(raw, bool) else None
        elif isinstance(allowed[0], int):
            values[name] = _integer(raw)
        else:
            values[name] = raw if isinstance(raw, str) and raw else None
    return BoxSettings(
        **values,
        offline_mode=raw if isinstance(raw := data.get("offlineMode"), bool) else None,
        settings_applied=raw if isinstance(raw := data.get("settingsApplied"), bool) else None,
    )


def _color_id(value: Any) -> str | None:
    """The colour of a box comes as a number or a word."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | str):
        return str(value) or None
    return None


def parse_chapter(data: dict[str, Any]) -> Chapter | None:
    """Parse one chapter of a figure."""
    chapter_id = _text(data, "id")
    if chapter_id is None:
        return None
    return Chapter(
        id=chapter_id,
        title=_text(data, "title") or "",
        seconds=_number(data.get("seconds")),
        transcoding=bool(data.get("transcoding")),
        file=_text(data, "file"),
    )


def _chapters(data: dict[str, Any]) -> tuple[Chapter, ...]:
    raw = data.get("chapters")
    if not isinstance(raw, list):
        return ()
    return tuple(c for item in raw if isinstance(item, dict) and (c := parse_chapter(item)))


def parse_creative_tonie(data: dict[str, Any], household_id: str) -> Tonie | None:
    """Parse one figure of GET /households/{id}/creativetonies."""
    tonie_id = _text(data, "id")
    if tonie_id is None:
        return None
    return Tonie(
        id=tonie_id,
        household_id=household_id,
        kind=TonieKind.CREATIVE,
        name=_text(data, "name", "title") or "Creative-Tonie",
        image_url=_text(data, "imageUrl"),
        locked=bool(data.get("lock", data.get("locked"))),
        chapters=_chapters(data),
        seconds_remaining=_number(data.get("secondsRemaining")),
        chapters_remaining=_integer(data.get("chaptersRemaining")),
        transcoding=bool(data.get("transcoding")),
        transcoding_errors=_transcoding_errors(data.get("transcodingErrors")),
        live=_flag(data.get("live")),
    )


def _transcoding_errors(raw: Any) -> tuple[str, ...]:
    """The reasons of the conversion errors, as the cloud names them."""
    if not isinstance(raw, list):
        return ()
    return tuple(
        reason
        for item in raw
        if isinstance(item, dict) and (reason := _text(item, "reason")) is not None
    )


def _content_chapters(data: dict[str, Any]) -> tuple[Chapter, ...]:
    """The chapters of a bought figure: names in order, no IDs, no lengths."""
    raw = data.get("chapters")
    if not isinstance(raw, list):
        return ()
    return tuple(
        Chapter(
            id=str(index),
            title=_text(item, "name", "title") or "",
            seconds=_number(item.get("seconds")),
        )
        for index, item in enumerate(raw)
        if isinstance(item, dict)
    )


def parse_content_tonie(data: dict[str, Any], household_id: str | None = None) -> Tonie | None:
    """Parse one bought figure of the GraphQL library (households.contentTonies or myContentTonies)."""
    tonie_id = _text(data, "id")
    household_id = household_id or _text(data, "householdId")
    if tonie_id is None or household_id is None:
        return None
    series = data.get("series")
    series_name = _text(series, "name") if isinstance(series, dict) else None
    return Tonie(
        id=tonie_id,
        household_id=household_id,
        kind=TonieKind.CONTENT,
        name=_text(data, "title") or series_name or "Tonie",
        series=series_name,
        image_url=_text(data, "imageUrl", "coverUrl"),
        language=_text(data, "languageName", "languageUnicode"),
        locked=bool(data.get("lock")),
        chapters=_content_chapters(data),
        seconds_total=_number(data.get("secondsPresent")),
    )


def parse_disc(data: dict[str, Any]) -> Tonie | None:
    """Parse one node of the GraphQL field myDiscs."""
    disc_id = _text(data, "id")
    household_id = _text(data, "householdId")
    if disc_id is None or household_id is None:
        return None
    return Tonie(
        id=disc_id,
        household_id=household_id,
        kind=TonieKind.DISC,
        name=_text(data, "title") or "Disc",
        image_url=_text(data, "coverImageUrl", "discImageUrl"),
        language=_text(data, "language"),
        locked=bool(data.get("lock")),
        chapters=_chapters(data),
    )


def parse_playback_info(data: dict[str, Any]) -> TonieDetails:
    """Parse GET /playback-info/{box}/{tonie}: the chapters of the figure on a box.

    These chapters carry no IDs; their position is their identity.
    """
    raw = data.get("chapters")
    chapters = tuple(
        Chapter(
            id=str(index),
            title=_text(item, "title") or _text(item, "tuneTitle") or "",
            seconds=_number(item.get("seconds")),
        )
        for index, item in enumerate(raw if isinstance(raw, list) else [])
        if isinstance(item, dict)
    )
    return TonieDetails(
        title=_text(data, "title"),
        series=_text(data, "series"),
        image_url=_text(data, "tonieImageUrl", "coverUrl", "imageUrl"),
        chapters=chapters,
        status=_text(data, "status"),
    )


# Statuses the battery message sends while charging, and while not; any other
# status ("charged", say) leaves it unknown
_CHARGING = frozenset({"charging", "fastcharging", "fast_charging"})
_NOT_CHARGING = frozenset({"discharging", "notcharging", "not_charging", "full", "idle"})


def parse_battery(data: dict[str, Any]) -> Battery:
    """Parse metrics/battery; a box that shuts down sends only nulls."""
    status = _text(data, "status")
    charging: bool | None = None
    if status is not None:
        lowered = status.lower()
        if lowered in _CHARGING:
            charging = True
        elif lowered in _NOT_CHARGING:
            charging = False
    return Battery(percent=_integer(data.get("percent")), charging=charging, status=status)


def parse_online(data: dict[str, Any]) -> bool | None:
    """Parse online-state; anything but a known word stays unknown."""
    state = _text(data, "onlineState", "state")
    return _ONLINE_STATES.get((state or "").lower())


def parse_volume(data: dict[str, Any]) -> Volume:
    """Parse volume/state."""
    return Volume(
        level=_integer(data.get("level")), percent=_integer(data.get("hardwarePercentage"))
    )


def parse_playback(data: dict[str, Any], now: float | None = None) -> Playback:
    """Parse playback/state.

    While playing the message carries the moment the chapter ends
    (``chapterUntilMs``), while paused the position (``chapterPositionMs``);
    both become a position in seconds at the time the message arrived.
    """
    now = time.time() if now is None else now
    raw_tonie = data.get("tonie")
    tonie_id: str | None = None
    if isinstance(raw_tonie, dict):
        tonie_id = _text(raw_tonie, "id")
    elif isinstance(raw_tonie, str) and raw_tonie:
        tonie_id = raw_tonie
    else:
        tonie_id = _text(data, "tonieId", "id")
    duration = _number(data.get("chapterDuration"))
    position: float | None = None
    position_ms = _number(data.get("chapterPositionMs"))
    until_ms = _number(data.get("chapterUntilMs"))
    if position_ms is not None:
        position = position_ms / 1000
    elif duration is not None and until_ms is not None:
        position = duration - (until_ms / 1000 - now)
    if position is not None:
        position = max(0.0, position)
        if duration is not None:
            position = min(duration, position)
    version = next(
        (
            _integer(v)
            for k, v in data.items()
            if "version" in k.lower() and _integer(v) is not None
        ),
        None,
    )
    return Playback(
        tonie_id=tonie_id,
        chapter=_integer(data.get("chapter")),
        content_version=version,
        paused=_flag(data.get("paused")),
        ended=_flag(data.get("ended")),
        downloading=_flag(data.get("downloading")),
        running=until_ms is not None and position_ms is None,
        duration=duration,
        position=position,
        received_at=datetime.fromtimestamp(now, UTC),
    )


def parse_headphones(data: dict[str, Any]) -> Headphones:
    """Parse metrics/headphones: the list of what is connected, the first one counts."""
    connected = data.get("connected")
    first = (
        connected[0]
        if isinstance(connected, list) and connected and isinstance(connected[0], dict)
        else None
    )
    if first is None:
        return Headphones(connected=bool(isinstance(connected, list) and connected))
    battery = _integer(first.get("battery"))
    return Headphones(
        connected=True,
        kind=_text(first, "type"),
        battery=battery if battery is not None and 0 <= battery <= 100 else None,
    )


def parse_sleep_timer(data: dict[str, Any]) -> SleepTimer:
    """Parse app-reply/bedtime-state."""
    stl = data.get("stl")
    if not isinstance(stl, dict):
        return SleepTimer(state=None)
    return SleepTimer(
        state=_text(stl, "state"),
        duration=_integer(stl.get("duration")),
        until=parse_datetime(stl.get("until")),
        alarm=isinstance(stl.get("alarm"), dict) and bool(stl["alarm"]),
    )


def _tonie_ids(items: Any) -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    return tuple(i for item in items if isinstance(item, dict) and (i := _text(item, "id")))


def parse_tune(data: dict[str, Any]) -> Tune | None:
    """Parse one node of the GraphQL field tunesItems (owned ones)."""
    mine = data.get("myTune")
    tune_id = _text(mine, "id") if isinstance(mine, dict) else None
    if tune_id is None or not isinstance(mine, dict):
        return None
    series = data.get("series")
    info = data.get("contentInfo")
    return Tune(
        id=tune_id,
        title=_text(data, "title") or "Tune",
        image_url=_text(data, "thumbnail"),
        series=_text(series, "name") if isinstance(series, dict) else None,
        seconds=_number(info.get("seconds")) if isinstance(info, dict) else None,
        remaining=_integer(mine.get("assignCountRemaining")),
        assigned=_tonie_ids(mine.get("assignedTonies")),
        suitable=_tonie_ids(mine.get("suitableTonies")),
        compatible=_tonie_ids(data.get("compatibleTonies")),
        all_creative=data.get("allCreativeTonies") is True,
    )


def parse_notice(data: dict[str, Any], system: bool = False) -> CloudNotice | None:
    """Parse one entry of GET /notifications or GET /system-notifications."""
    notice_id = _text(data, "id")
    text = _text(data, "translatedText", "text")
    if notice_id is None or text is None:
        return None
    return CloudNotice(
        id=("system:" if system else "") + notice_id,
        cloud_id=notice_id,
        text=text,
        kind="system" if system else (_text(data, "ntype") or "unknown"),
        read=data.get("read") is True,
        timestamp=parse_datetime(data.get("timestamp")),
        tonie_id=_text(data, "tonieId"),
        reason=_text(data, "tonieReason"),
    )


def parse_member(data: dict[str, Any]) -> Member | None:
    """Parse one entry of GET /households/{id}/memberships."""
    member_id = _text(data, "id")
    display_name = _text(data, "displayName", "firstName", "email")
    if member_id is None or display_name is None:
        return None
    role = _text(data, "mtype")
    return Member(
        id=member_id,
        display_name=display_name,
        role=role if role in MEMBER_ROLES else "unknown",
        is_self=data.get("isSelf") is True,
        first_name=_text(data, "firstName"),
        last_name=_text(data, "lastName"),
        email=_text(data, "email"),
    )


def _clock_time(value: Any) -> str | None:
    """A time of day as "HH:MM"; the cloud has also sent seconds."""
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    if len(parts) < 2 or not all(p.isdigit() for p in parts[:2]):
        return None
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    return f"{hour:02d}:{minute:02d}"


def parse_bedtime_schedule(data: dict[str, Any]) -> BedtimeSchedule | None:
    """Parse one schedule of GET .../tonieboxes/{id}/bedtime-schedules."""
    schedule_id = _text(data, "id")
    if schedule_id is None:
        return None
    days = data.get("days")
    return BedtimeSchedule(
        id=schedule_id,
        name=_text(data, "name") or "",
        sleep_time=_clock_time(data.get("sleepTime")),
        wakeup_time=_clock_time(data.get("wakeupTime")),
        days=tuple(
            d for d in WEEKDAYS if isinstance(days, list) and d in {str(x).lower() for x in days}
        ),
        enabled=data.get("enabled") is True,
        alarm_enabled=data.get("alarmEnabled") is True,
        alarm_tone=_text(data, "alarmTone"),
        alarm_volume=_integer(data.get("alarmVolume")),
        alarm_morning_light=_flag(data.get("alarmMorningLight")),
    )
