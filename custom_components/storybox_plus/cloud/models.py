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
    placed_tonie_id: str | None = None
    max_volume: int | None = None
    max_headphone_volume: int | None = None
    raw_generation: str | None = None

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
    """The volume of a Toniebox 2, from the push channel."""

    level: int | None

    @property
    def fraction(self) -> float | None:
        """Return the level as 0..1."""
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
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def playing(self) -> bool:
        """Return whether audio is playing right now."""
        return (
            self.tonie_id is not None
            and self.paused is False
            and not self.ended
            and not self.downloading
        )


@dataclass(frozen=True, slots=True)
class SleepTimer:
    """The sleep timer of a Toniebox 2, from the push channel."""

    state: str | None
    duration: int | None = None
    until: datetime | None = None


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
    features = data.get("features")
    live = isinstance(features, list) and "tngSettings" in features
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
        placed_tonie_id=placed,
        max_volume=_integer(data.get("maxVolume")),
        max_headphone_volume=_integer(data.get("maxHeadphoneVolume")),
        raw_generation=_text(data, "generation"),
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
    return Volume(level=_integer(data.get("level")))


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
        duration=duration,
        position=position,
        received_at=datetime.fromtimestamp(now, UTC),
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
    )
