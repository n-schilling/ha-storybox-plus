"""The parsers of the cloud's payloads: lenient with what the cloud sends."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.storybox_plus.cloud.models import (
    VOLUME_LEVELS,
    Box,
    Chapter,
    Generation,
    Playback,
    Tonie,
    TonieDetails,
    TonieKind,
    Volume,
    normalize_mac,
    parse_battery,
    parse_box,
    parse_chapter,
    parse_content_tonie,
    parse_creative_tonie,
    parse_datetime,
    parse_disc,
    parse_household,
    parse_online,
    parse_playback,
    parse_playback_info,
    parse_sleep_timer,
    parse_volume,
)

from .conftest import (
    PLAYBACK_INFO_IMAGE,
    PLAYBACK_INFO_SERIES,
    TONIE_NAME,
    classic_box,
    content_tonie,
    creative_tonie,
    disc,
    playback_info,
    tb2_box,
)

EPOCH = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-04T10:00:00Z", EPOCH),
        ("2026-11-04T10:00:00+00:00", EPOCH),
        ("2026-11-04T12:00:00+02:00", EPOCH),
        ("2026-11-04T10:00:00", EPOCH),
        (EPOCH.timestamp(), EPOCH),
        (int(EPOCH.timestamp()), EPOCH),
        (int(EPOCH.timestamp() * 1000), EPOCH),
        (None, None),
        (True, None),
        ("yesterday", None),
        ("", None),
        ([1], None),
        (1e300, None),
    ],
)
def test_parse_datetime(value: Any, expected: datetime | None) -> None:
    """ISO strings with or without zone and epoch seconds or milliseconds; garbage is None."""
    assert parse_datetime(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        (" a1b2c3d4e5f6 ", "A1B2C3D4E5F6"),
        ("A1B2C3D4E5F6", "A1B2C3D4E5F6"),
    ],
)
def test_normalize_mac(value: str | None, expected: str | None) -> None:
    """MACs are upper case without surrounding blanks, as the push topics spell them."""
    assert normalize_mac(value) == expected


def test_parse_household() -> None:
    """A household needs an ID; the name has a fallback."""
    household = parse_household({"id": "hh1", "name": "Familie Muster"})
    assert household is not None
    assert (household.id, household.name) == ("hh1", "Familie Muster")
    assert parse_household({"name": "x"}) is None
    assert parse_household({"id": "hh2", "name": ""}).name == "Household"


def test_parse_box_toniebox_2() -> None:
    """A box with the feature tngSettings is a Toniebox 2, whatever the generation field says."""
    box = parse_box(tb2_box(), "hh1")
    assert box is not None
    assert box.generation is Generation.TONIEBOX_2
    assert box.live
    assert box.raw_generation == "tb2g2"
    assert box.household_id == "hh1"
    assert box.mac == "A1B2C3D4E5F6"
    assert box.online is True
    assert box.last_seen == EPOCH
    assert box.firmware == "1.2.3"
    assert box.color_id == "red"
    assert box.placed_tonie_id == "t1"
    assert box.settings.max_volume == 10
    assert box.settings.max_headphone_volume is None


def test_parse_box_classic() -> None:
    """A classic box has no online state and no MAC, only when it was last seen."""
    box = parse_box(classic_box(last_seen="2026-11-04T10:00:00Z"), "hh1")
    assert box is not None
    assert box.generation is Generation.CLASSIC
    assert not box.live
    assert box.raw_generation == "classic"
    assert box.mac is None
    assert box.online is None
    assert box.last_seen == EPOCH
    assert box.firmware == "3.1.0"
    assert box.placed_tonie_id is None


def test_parse_box_generation_field_does_not_decide() -> None:
    """The generation field alone makes no Toniebox 2; the feature flag does."""
    data = tb2_box()
    data["features"] = ["bedtime"]
    assert parse_box(data, "hh1").generation is Generation.CLASSIC
    data["features"] = "tngSettings"
    assert parse_box(data, "hh1").generation is Generation.CLASSIC
    data["generation"] = "classic"
    data["features"] = ["tngSettings"]
    assert parse_box(data, "hh1").generation is Generation.TONIEBOX_2


def test_parse_box_variants() -> None:
    """Other spellings the API has used are understood; nonsense is dropped."""
    assert parse_box({"name": "no id"}, "hh1") is None
    box = parse_box(
        {
            "id": "b",
            "mac_address": "aabbccddeeff",
            "onlineState": "offline",
            "placement": {"tonie": "t9"},
            "firmware": "2.0",
            "last_seen": 1762250400000,
            "maxVolume": 7.9,
            "maxHeadphoneVolume": 3,
        },
        "hh1",
    )
    assert box is not None
    assert box.name == "Toniebox"
    assert box.mac == "AABBCCDDEEFF"
    assert box.online is False
    assert box.placed_tonie_id == "t9"
    assert box.firmware == "2.0"
    assert box.last_seen == datetime(2025, 11, 4, 10, 0, tzinfo=UTC)
    assert box.settings.max_volume == 7
    assert box.settings.max_headphone_volume == 3
    assert box.raw_generation is None
    odd = parse_box(
        {
            "id": "c",
            "onlineState": "sleeping",
            "placement": {"tonie": None},
            "firmware": {"name": "fw-9"},
            "generation": 2,
        },
        "hh1",
    )
    assert odd is not None
    assert odd.online is None
    assert odd.placed_tonie_id is None
    assert odd.firmware == "fw-9"
    assert odd.raw_generation is None
    no_firmware = parse_box({"id": "d", "firmware": 5, "firmwareVersion": "1.0"}, "hh1")
    assert no_firmware is not None
    assert no_firmware.firmware == "1.0"
    assert parse_box({"id": "e", "firmware": {}}, "hh1").firmware is None


def test_parse_chapter() -> None:
    """A chapter needs an ID; the rest has fallbacks."""
    chapter = parse_chapter(
        {"id": "ch1", "title": "Song", "file": "f1", "seconds": 120.5, "transcoding": 1}
    )
    assert chapter == Chapter(id="ch1", title="Song", seconds=120.5, transcoding=True, file="f1")
    assert parse_chapter({"title": "no id"}) is None
    bare = parse_chapter({"id": "ch2", "seconds": "12"})
    assert bare == Chapter(id="ch2", title="", seconds=None, transcoding=False, file=None)


def test_parse_creative_tonie() -> None:
    """Creative figures carry their chapters and what is left on them."""
    tonie = parse_creative_tonie(creative_tonie(), "hh1")
    assert tonie is not None
    assert tonie.kind is TonieKind.CREATIVE
    assert tonie.household_id == "hh1"
    assert tonie.name == "Kreativ"
    assert tonie.image_url == "https://img.example.com/c1.png"
    assert tonie.locked is False
    assert [c.id for c in tonie.chapters] == ["ch1"]
    assert tonie.seconds == 120.5
    assert tonie.seconds_remaining == 5000
    assert tonie.chapters_remaining == 80
    assert tonie.transcoding is False
    assert parse_creative_tonie({"name": "no id"}, "hh1") is None
    sparse = parse_creative_tonie(
        {"id": "c2", "title": "By title", "locked": True, "chapters": "none", "transcoding": True},
        "hh1",
    )
    assert sparse is not None
    assert sparse.name == "By title"
    assert sparse.locked is True
    assert sparse.chapters == ()
    assert sparse.transcoding is True
    assert parse_creative_tonie({"id": "c3"}, "hh1").name == "Creative-Tonie"


def test_chapters_skip_broken_items() -> None:
    """Chapters without an ID or that are no objects are left out."""
    data = creative_tonie()
    data["chapters"] = [{"id": "a", "title": "A"}, "x", {"title": "no id"}, {"id": "b"}]
    tonie = parse_creative_tonie(data, "hh1")
    assert tonie is not None
    assert [c.id for c in tonie.chapters] == ["a", "b"]
    assert tonie.seconds == 0


def test_parse_content_tonie() -> None:
    """Bought figures come from the library query under their household, with chapter names."""
    tonie = parse_content_tonie(content_tonie(), "hh1")
    assert tonie is not None
    assert tonie.kind is TonieKind.CONTENT
    assert tonie.household_id == "hh1"
    assert tonie.name == "Schlummerjaguar"
    assert tonie.series == "Schlummerbande"
    assert tonie.image_url == "https://img.example.com/t1.png"
    assert tonie.language == "Deutsch"
    # The chapters have names only: their position is their ID, their length is unknown
    assert [(c.id, c.title, c.seconds) for c in tonie.chapters] == [
        ("0", "Kapitel 1", None),
        ("1", "Kapitel 2", None),
    ]
    # The library states the total length instead
    assert tonie.seconds_total == 500
    assert tonie.seconds == 500
    assert tonie.seconds_remaining is None
    # The household of the parent wins; the older connection query names it in the node
    assert parse_content_tonie(content_tonie(household_id="hh9"), "hh1").household_id == "hh1"
    assert parse_content_tonie(content_tonie(household_id="hh9")).household_id == "hh9"
    assert parse_content_tonie({"id": "t", "title": "no household"}) is None
    assert parse_content_tonie({"householdId": "hh1"}, "hh1") is None


def test_parse_content_tonie_variants() -> None:
    """The library query spells the language as a locale and may lack lengths or chapters."""
    data = content_tonie(
        chapters=[{"name": "A"}, {"title": "B"}, {"name": ""}, "x"], seconds_present=None
    )
    del data["languageName"]
    tonie = parse_content_tonie(data, "hh1")
    assert tonie is not None
    assert tonie.language == "de-de"
    assert [(c.id, c.title) for c in tonie.chapters] == [("0", "A"), ("1", "B"), ("2", "")]
    assert tonie.seconds_total is None
    assert tonie.seconds == 0
    odd = parse_content_tonie(content_tonie(chapters="none", seconds_present="500"), "hh1")
    assert odd is not None
    assert odd.chapters == ()
    assert odd.seconds == 0


def test_parse_content_tonie_fallbacks() -> None:
    """Without a title the series names the figure; the cover URL stands in for the image."""
    data = content_tonie()
    data.update({"title": None, "imageUrl": None, "coverUrl": "https://img.example.com/cover.png"})
    tonie = parse_content_tonie(data)
    assert tonie is not None
    assert tonie.name == "Schlummerbande"
    assert tonie.image_url == "https://img.example.com/cover.png"
    data.update({"series": "Schlummerbande", "lock": 1})
    tonie = parse_content_tonie(data)
    assert tonie is not None
    assert tonie.name == "Tonie"
    assert tonie.series is None
    assert tonie.locked is True


def test_parse_disc() -> None:
    """Discs have no chapters in the API; the disc image stands in for a missing cover."""
    parsed = parse_disc(disc())
    assert parsed is not None
    assert parsed.kind is TonieKind.DISC
    assert parsed.name == "Disc Eins"
    assert parsed.image_url == "https://img.example.com/d1.png"
    assert parsed.language == "de"
    assert parsed.chapters == ()
    data = disc()
    data.update({"title": "", "coverImageUrl": None, "discImageUrl": "https://img.example.com/x"})
    fallback = parse_disc(data)
    assert fallback is not None
    assert fallback.name == "Disc"
    assert fallback.image_url == "https://img.example.com/x"
    assert parse_disc({"id": "d"}) is None


def test_parse_playback_info() -> None:
    """The box tells title, series, picture, status and the chapters of the figure on it."""
    details = parse_playback_info(playback_info())
    assert details.title == TONIE_NAME
    assert details.series == PLAYBACK_INFO_SERIES
    assert details.image_url == PLAYBACK_INFO_IMAGE
    assert details.status == "available"
    # These chapters carry no IDs: their position is their identity
    assert [(c.id, c.title, c.seconds, c.transcoding) for c in details.chapters] == [
        ("0", "Box-Kapitel 1", 180.0, False),
        ("1", "Box-Kapitel 2", 240.0, False),
        ("2", "Box-Kapitel 3", 60.0, False),
    ]
    assert all(c.file is None for c in details.chapters)


def test_parse_playback_info_without_fields() -> None:
    """Missing or odd fields leave the details empty instead of failing."""
    assert parse_playback_info({}) == TonieDetails()
    sparse = parse_playback_info(
        {"title": "", "series": 5, "tonieImageUrl": None, "chapters": "none", "status": 1}
    )
    assert sparse == TonieDetails(title=None, series=None, image_url=None, chapters=(), status=None)
    # The title falls back to the tune's; items that are no objects are left out
    broken = parse_playback_info(
        playback_info(
            chapters=[
                {"title": "A", "tuneTitle": "Tune A"},
                {"tuneTitle": "Tune B", "seconds": "5"},
                {"title": "", "tuneTitle": "Tune C", "seconds": 5},
                {"coverUrl": "https://img/cover"},
                "x",
            ]
        )
    )
    assert [(c.id, c.title, c.seconds) for c in broken.chapters] == [
        ("0", "A", None),
        ("1", "Tune B", None),
        ("2", "Tune C", 5.0),
        ("3", "", None),
    ]


@pytest.mark.parametrize("status", ["available", "outdated", "unavailable", None, 5, ""])
def test_parse_playback_info_status(status: Any) -> None:
    """The status comes as the cloud spells it; anything but a text is unknown."""
    expected = status if isinstance(status, str) and status else None
    assert parse_playback_info(playback_info(status=status)).status == expected


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        (
            {"tonieImageUrl": "https://img/tonie", "coverUrl": "https://img/cover"},
            "https://img/tonie",
        ),
        ({"tonieImageUrl": None, "coverUrl": "https://img/cover"}, "https://img/cover"),
        (
            {"tonieImageUrl": "", "coverUrl": None, "imageUrl": "https://img/image"},
            "https://img/image",
        ),
        ({"coverUrl": 7, "imageUrl": ["https://img/list"]}, None),
    ],
)
def test_parse_playback_info_image_fallbacks(fields: dict[str, Any], expected: str | None) -> None:
    """The figure's own picture comes first, then the cover, then a plain image URL."""
    data = playback_info()
    del data["tonieImageUrl"]
    data.update(fields)
    assert parse_playback_info(data).image_url == expected


@pytest.mark.parametrize(
    ("status", "charging"),
    [
        ("charging", True),
        ("Charging", True),
        ("fastCharging", True),
        ("discharging", False),
        ("notCharging", False),
        ("not_charging", False),
        ("full", False),
        ("idle", False),
        ("plugged", None),
        ("charged", None),
        ("fully_charged", None),
        ("charge_complete", None),
        (None, None),
        (7, None),
    ],
)
def test_parse_battery_status(status: Any, charging: bool | None) -> None:
    """The status text decides whether the box charges; unknown texts decide nothing."""
    battery = parse_battery({"percent": 80, "status": status})
    assert battery.charging is charging
    assert battery.percent == 80
    assert battery.status == (status if isinstance(status, str) else None)


@pytest.mark.parametrize(
    ("percent", "expected"), [(80, 80), (79.6, 79), (None, None), ("80", None), (True, None)]
)
def test_parse_battery_percent(percent: Any, expected: int | None) -> None:
    """The percentage is a number or nothing; a box that shuts down sends only nulls."""
    assert parse_battery({"percent": percent, "status": None}).percent == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"onlineState": "online"}, True),
        ({"onlineState": "OFFLINE"}, False),
        ({"state": "online"}, True),
        ({"onlineState": "asleep"}, None),
        ({}, None),
        ({"onlineState": True}, None),
    ],
)
def test_parse_online(data: dict[str, Any], expected: bool | None) -> None:
    """Online or offline, in any case; anything else is unknown."""
    assert parse_online(data) is expected


def test_parse_volume() -> None:
    """The level is an integer or unknown; the fraction maps 13 levels to 0..1."""
    assert parse_volume({"level": 7, "hardwarePercentage": 55}) == Volume(level=7)
    assert parse_volume({}) == Volume(level=None)
    assert Volume(level=None).fraction is None
    assert Volume(level=0).fraction == 0.0
    assert Volume(level=VOLUME_LEVELS).fraction == 1.0
    assert Volume(level=7).fraction == pytest.approx(7 / 13)
    assert Volume(level=20).fraction == 1.0
    assert Volume(level=-2).fraction == 0.0


def test_parse_playback_while_playing() -> None:
    """While playing the position follows from when the chapter will end."""
    now = EPOCH.timestamp()
    playback = parse_playback(
        {
            "tonie": "t1",
            "paused": False,
            "chapter": 1,
            "chapterUntilMs": (now + 150) * 1000,
            "chapterDuration": 200,
            "ended": False,
            "downloading": False,
        },
        now=now,
    )
    assert playback.tonie_id == "t1"
    assert playback.chapter == 1
    assert playback.paused is False
    assert playback.ended is False
    assert playback.downloading is False
    assert playback.duration == 200
    assert playback.position == pytest.approx(50)
    assert playback.received_at == EPOCH
    assert playback.playing


def test_parse_playback_while_paused() -> None:
    """While paused the message carries the position itself, which wins."""
    now = EPOCH.timestamp()
    playback = parse_playback(
        {
            "tonie": {"id": "t1"},
            "paused": True,
            "chapter": 0,
            "chapterPositionMs": 42_000,
            "chapterUntilMs": (now + 1) * 1000,
            "chapterDuration": 200,
        },
        now=now,
    )
    assert playback.tonie_id == "t1"
    assert playback.position == 42
    assert playback.paused is True
    assert not playback.playing


def test_parse_playback_clamps_position() -> None:
    """A position outside the chapter is clamped to it."""
    now = EPOCH.timestamp()
    late = parse_playback(
        {"tonie": "t1", "chapterUntilMs": (now - 10) * 1000, "chapterDuration": 200}, now=now
    )
    assert late.position == 200
    early = parse_playback(
        {"tonie": "t1", "chapterUntilMs": (now + 500) * 1000, "chapterDuration": 200}, now=now
    )
    assert early.position == 0
    negative = parse_playback({"tonie": "t1", "chapterPositionMs": -5}, now=now)
    assert negative.position == 0
    assert negative.duration is None


def test_parse_playback_without_position() -> None:
    """Without a duration the end time tells no position; without any field nothing is known."""
    now = EPOCH.timestamp()
    playback = parse_playback({"tonie": "t1", "chapterUntilMs": (now + 5) * 1000}, now=now)
    assert playback.position is None
    assert playback.duration is None
    empty = parse_playback({}, now=now)
    assert empty.tonie_id is None
    assert empty.chapter is None
    assert empty.paused is None
    assert not empty.playing
    assert parse_playback({"tonieId": "t2"}, now=now).tonie_id == "t2"
    assert parse_playback({"id": "t3"}, now=now).tonie_id == "t3"
    assert parse_playback({"tonie": {"name": "no id"}}, now=now).tonie_id is None
    assert parse_playback({"tonie": "", "paused": "no"}, now=now).paused is None


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"contentVersion": 1730000000}, 1730000000),
        ({"CONTENT_VERSION": 42.0}, 42),
        ({}, None),
        ({"contentVersion": "1730000000"}, None),
        ({"contentVersion": True}, None),
        ({"contentVersion": None, "version": 7}, 7),
    ],
)
def test_parse_playback_content_version(fields: dict[str, Any], expected: int | None) -> None:
    """The content version is any integer under a key that mentions a version; else unknown."""
    playback = parse_playback({"tonie": "t1", **fields}, now=EPOCH.timestamp())
    assert playback.content_version == expected
    assert playback.tonie_id == "t1"


def test_parse_playback_uses_the_clock() -> None:
    """Without a given moment the message counts as received now."""
    before = datetime.now(UTC)
    playback = parse_playback({"tonie": "t1"})
    assert before <= playback.received_at <= datetime.now(UTC)


@pytest.mark.parametrize(
    ("fields", "playing"),
    [
        ({"paused": False}, True),
        ({"paused": True}, False),
        ({"paused": None}, False),
        ({"paused": False, "ended": True}, False),
        ({"paused": False, "downloading": True}, False),
        ({"tonie_id": None, "paused": False}, False),
    ],
)
def test_playback_playing(fields: dict[str, Any], playing: bool) -> None:
    """Audio plays only with a figure, not paused, not ended, not downloading."""
    values: dict[str, Any] = {"tonie_id": "t1", **fields}
    assert Playback(**values).playing is playing


def test_parse_sleep_timer() -> None:
    """The sleep timer comes nested under stl with an epoch end."""
    timer = parse_sleep_timer({"stl": {"state": "on", "duration": 600, "until": 1762250400}})
    assert timer.state == "on"
    assert timer.duration == 600
    assert timer.until == datetime(2025, 11, 4, 10, 0, tzinfo=UTC)
    assert parse_sleep_timer({}).state is None
    assert parse_sleep_timer({"stl": "off"}).until is None


def test_tonie_seconds_ignores_unknown_lengths() -> None:
    """The total length counts the chapters whose length is known."""
    tonie = Tonie(
        id="t",
        household_id="hh1",
        kind=TonieKind.CONTENT,
        name="T",
        chapters=(Chapter("a", "A", 10.5), Chapter("b", "B", None), Chapter("c", "C", 4)),
    )
    assert tonie.seconds == 14.5
    # A total the library states wins over the sum of the chapters
    assert replace(tonie, seconds_total=42).seconds == 42
    assert replace(tonie, seconds_total=0).seconds == 0
    assert Box("b", "hh1", "B", None, Generation.CLASSIC).live is False


def test_creative_tonie_transcoding_errors() -> None:
    """The reasons of a failed conversion are kept, as the cloud names them; the rest is dropped."""
    data = creative_tonie()
    data["transcodingErrors"] = [
        {"reason": "wrongFormat", "deletedChapters": [{"title": "x"}]},
        {"reason": "tooLong", "deletedChapters": [{"title": "y", "seconds": 10}]},
        {"deletedChapters": []},
        "x",
    ]
    tonie = parse_creative_tonie(data, "hh1")
    assert tonie is not None
    assert tonie.transcoding_errors == ("wrongFormat", "tooLong")
    data["transcodingErrors"] = "none"
    assert parse_creative_tonie(data, "hh1").transcoding_errors == ()
