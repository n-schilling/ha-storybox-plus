"""Favourite chapters: the stars, their store, the modes, and how the box is steered by them."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import random
from typing import Any
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.storage import Store

from custom_components.storybox_plus import bedtime
from custom_components.storybox_plus.cloud import (
    BedtimeSchedule,
    Chapter,
    CloudConnectionError,
    Playback,
    Tonie,
    TonieKind,
    Tune,
)
from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.favourites import (
    FavouriteChapters,
    Favourites,
    Plan,
    following,
    order_of,
    preceding,
)

from .conftest import (
    BOX_ID,
    CLASSIC_BOX_ID,
    CREATIVE_ID,
    DISC_ID,
    HOUSEHOLD_ID,
    MAC,
    TONIE_ID,
    FakeCloud,
    PushChannels,
    entity_id,
    entry_for,
    tb2_box,
)

START = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def eight_chapters(cloud: FakeCloud) -> None:
    """The bought figure has eight chapters, the creative one three."""
    cloud.main.content_tonies[0]["chapters"] = [{"name": f"Kapitel {i}"} for i in range(1, 9)]
    cloud.main.creative_tonies[HOUSEHOLD_ID][0]["chapters"] = [
        {"id": f"ch{i}", "title": f"Song {i}", "file": f"f{i}", "seconds": 60, "transcoding": False}
        for i in range(1, 4)
    ]


def _tonie(kind: TonieKind = TonieKind.CONTENT, chapters: int = 5, ids: str = "abcde") -> Tonie:
    return Tonie(
        "t",
        "h",
        kind,
        "Figure",
        chapters=tuple(Chapter(ids[i], f"Chapter {i}") for i in range(chapters)),
    )


# ---------------------------------------------------------------- the order


def test_order() -> None:
    """The favourites first, one of them by chance, or only they."""
    assert order_of(Plan("only", (1, 3), 5)) == (1, 3)
    assert order_of(Plan("first", (1, 3), 5)) == (1, 3, 0, 2, 4)
    assert order_of(Plan("random", (1, 3), 5), first=3) == (3, 1, 0, 2, 4)
    # A first chapter that is no favourite any more gives way to one picked by chance
    picked = order_of(Plan("random", (1, 3, 4), 5), first=0, pick=random.Random(1))
    assert picked[0] in (1, 3, 4)
    assert sorted(picked) == [0, 1, 2, 3, 4]
    assert order_of(Plan("random", (2,), 3)) == (2, 0, 1)
    # Not the one of last time while there is another
    for seed in range(20):
        again = order_of(Plan("random", (1, 3), 5), pick=random.Random(seed), avoid=3)
        assert again[0] == 1
    assert order_of(Plan("random", (3,), 5), avoid=3)[0] == 3


def test_neighbours_in_the_order() -> None:
    """The chapter after and before one, also for a chapter outside the order."""
    order = (3, 1, 0, 2)
    assert [following(order, c) for c in order] == [1, 0, 2, None]
    assert [preceding(order, c) for c in order] == [3, 3, 1, 0]
    # Outside (only the favourites play): the next one behind it, the last one before it
    assert following((1, 4), 2) == 4
    assert following((1, 4), 5) is None
    assert preceding((1, 4), 2) == 1
    assert preceding((1, 4), 0) == 1


def test_positions_of_the_favourites() -> None:
    """Bought figures keep positions, creative ones the chapters themselves."""
    assert Favourites(None, (1, 7)).indexes(_tonie()) == (1,)
    assert Favourites(None, (1, 7)).indexes(_tonie(chapters=0)) == (1, 7)
    creative = _tonie(TonieKind.CREATIVE, ids="abcde")
    kept = Favourites("only", ids=("b", "e", "gone"))
    assert kept.indexes(creative) == (1, 4)
    # Arranged anew: the stars follow their chapters
    assert kept.indexes(_tonie(TonieKind.CREATIVE, ids="ebacd")) == (0, 1)
    assert kept.as_dict(creative) == {"mode": "only", "chapters": [1, 4]}
    assert kept.stored() == {"mode": "only", "ids": ["b", "e", "gone"]}


@pytest.mark.parametrize(
    ("clock", "expected"),
    [
        # Friday 27 November 2026; the wake-up days are Saturday and Sunday
        ("2026-11-27T19:59", False),
        ("2026-11-27T20:00", True),
        ("2026-11-28T06:59", True),
        ("2026-11-28T07:00", False),
        # Sunday evening: Monday is no wake-up day
        ("2026-11-29T21:00", False),
        # The nap on Friday afternoon
        ("2026-11-27T13:30", True),
        ("2026-11-28T13:30", False),
    ],
)
def test_asleep(clock: str, expected: bool) -> None:
    """A bedtime runs from the sleep time to the wake-up, over midnight too."""
    schedules = (
        BedtimeSchedule("s1", "Night", "20:00", "07:00", ("saturday", "sunday"), enabled=True),
        BedtimeSchedule("s2", "Nap", "13:00", "14:00", ("friday",), enabled=True),
        BedtimeSchedule("s3", "Off", "00:00", "23:59", ("friday", "saturday"), enabled=False),
        BedtimeSchedule("s4", "Open", "10:00", None, ("friday",), enabled=True),
        # An alarm alone, both times the same: no bedtime
        BedtimeSchedule("s5", "Alarm", "17:00", "17:00", ("friday", "saturday"), enabled=True),
    )
    now = datetime.fromisoformat(clock).replace(tzinfo=ZoneInfo("Europe/Berlin"))
    assert bedtime.asleep(schedules, now) is expected
    assert bedtime.asleep(None, now) is False


def test_asleep_reads_other_spellings_of_a_time() -> None:
    """One digit for the hour and seconds are read; what is no time skips the schedule."""
    now = datetime(2026, 11, 27, 8, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    days = ("friday",)
    assert bedtime.asleep((BedtimeSchedule("s", "", "7:30", "9:05:00", days, enabled=True),), now)
    for sleep, wakeup in (("late", "09:00"), ("07", "09:00"), ("07:00", "25:00"), ("", "")):
        odd = (BedtimeSchedule("s", "", sleep, wakeup, days, enabled=True),)
        assert bedtime.asleep(odd, now) is False


# ---------------------------------------------------------------- the store


def _store(hass: HomeAssistant) -> Store[dict[str, Any]]:
    return Store(hass, 1, "storybox_plus.test.favourites")


async def test_store_round_trip(hass: HomeAssistant) -> None:
    """Stars are kept sorted and without doubles; without stars and mode the figure is forgotten."""
    chapters = FavouriteChapters(_store(hass))
    await chapters.async_load()
    bought = _tonie()
    creative = Tonie(
        "c", "h", TonieKind.CREATIVE, "C", chapters=(Chapter("x", ""), Chapter("y", ""))
    )
    assert chapters.get("t") is None
    assert chapters.describe(bought) is None
    assert await chapters.async_set(bought, [4, 1, 4, 3], None) == Favourites(None, (1, 3, 4))
    assert await chapters.async_set(creative, [1], "only") == Favourites("only", (), ("y",))
    assert await chapters.async_star(bought, 0) is True
    assert await chapters.async_star(bought, 1) is False
    assert await chapters.async_star(bought, 3, True) is True
    assert chapters.indexes(bought) == (0, 3, 4)
    again = FavouriteChapters(_store(hass))
    await again.async_load()
    assert again.get("t") == Favourites(None, (0, 3, 4))
    assert again.describe(creative) == {"mode": "only", "chapters": [1]}
    # A mode alone is kept; neither is forgotten
    assert await again.async_set(bought, [], "off") == Favourites("off")
    assert await again.async_set(bought, [], None) is None
    assert again.get("t") is None


async def test_store_leaves_out_what_does_not_fit(hass: HomeAssistant) -> None:
    """Odd entries are dropped; lists of before the modes become "only" or "off"."""
    store = _store(hass)
    await store.async_save(
        {
            "tonies": {
                "on": {"active": True, "chapters": [2, "x", -1, True, 0]},
                "off": {"active": False, "chapters": [1]},
                "new": {"mode": "random", "ids": ["a", 3, "a"]},
                "odd-mode": {"mode": "loud", "chapters": [1]},
                "empty": {"mode": None, "chapters": []},
                "odd": {"chapters": "no"},
                "worse": "no",
            },
            "runs": {
                "b1": {"figure": "on", "first": 2, "base": 2, "started": True, "left": 5},
                "b2": {"figure": 7},
                "b3": "no",
            },
        }
    )
    chapters = FavouriteChapters(store)
    await chapters.async_load()
    assert chapters.get("on") == Favourites("only", (0, 2))
    assert chapters.get("off") == Favourites("off", (1,))
    assert chapters.get("new") == Favourites("random", (), ("a",))
    assert chapters.get("odd-mode") == Favourites(None, (1,))
    assert [chapters.get(k) for k in ("empty", "odd", "worse")] == [None, None, None]
    empty = FavouriteChapters(Store(hass, 1, "storybox_plus.other.favourites"))
    await empty.async_load()
    assert empty.get("on") is None


# ---------------------------------------------------------------- the steering, on its own


class Box:
    """One box that reports to the favourites; the plan can change while it plays."""

    def __init__(self, hass: HomeAssistant, plan: Plan | None, placed: bool = True) -> None:
        self.favourites = FavouriteChapters(_store(hass), random.Random(4))
        self.plan = plan
        self.now = START
        if placed:
            # The box is known and empty: the figure that comes is placed
            self.report(None, None)

    def report(self, chapter: int | None = 0, figure: str | None = "t", **fields: Any) -> Any:
        self.now += timedelta(seconds=fields.pop("after", 1))
        fields.setdefault("paused", False)
        playback = Playback(figure, chapter, received_at=self.now, **fields)
        return self.favourites.observe("box", playback, lambda _figure: self.plan)

    def play(self, *chapters: int) -> list[Any]:
        return [self.report(chapter) for chapter in chapters]


async def test_first_the_favourites_then_the_rest(hass: HomeAssistant) -> None:
    """Placed, the figure starts with its favourites and plays the other chapters after them."""
    box = Box(hass, Plan("first", (1, 3), 5))
    assert box.favourites.steering("box", "t") is None
    # Reports that do not play begin nothing
    assert box.report(0, paused=True) is None
    assert box.report(0, downloading=True) is None
    assert box.report(None) is None
    assert box.report(0) == ("jump", 1)
    assert box.favourites.steering("box", "t") == "first"
    assert box.favourites.first("box", "t") == 1
    # The box still reports the chapter it leaves while the command travels
    assert box.report(0, position=3.0) is None
    # The first favourite, then the chapter behind it: on to the second favourite
    assert box.play(1, 2) == [None, ("jump", 3)]
    # After the favourites the other chapters, the favourites left out
    assert box.play(3, 4) == [None, ("jump", 0)]
    assert box.play(0, 1) == [None, ("jump", 2)]
    assert box.play(2, 3) == [None, ("jump", 4)]
    assert box.report(4) is None
    # The figure ends with the order: nothing more
    assert box.report(4, ended=True) is None


async def test_the_order_goes_on_after_the_end_of_the_figure(hass: HomeAssistant) -> None:
    """A favourite at the very end: the box is started again for the other chapters."""
    box = Box(hass, Plan("first", (4,), 5))
    assert box.report(2) == ("jump", 4)
    assert box.report(4) is None
    assert box.report(4, ended=True) == ("play", 0)
    # Reported again while the command travels
    assert box.report(4, ended=True) is None
    assert box.play(0, 1, 2, 3) == [None, None, None, None]
    # The favourite comes round again: the order is over, the box pauses
    assert box.report(4) == ("pause", None)
    assert box.report(4, position=1.0) is None
    assert box.report(4, paused=True) is None
    # Play pressed then: the figure plays on, nothing is steered any more
    assert box.report(4) is None
    assert box.favourites.suspended("box", "t")
    assert box.favourites.steering("box", "t") is None
    assert box.report(4, ended=True) is None
    assert box.play(0, 1) == [None, None]


async def test_only_the_favourites(hass: HomeAssistant) -> None:
    """Every other chapter is left, forwards and backwards; after the last one the box pauses."""
    box = Box(hass, Plan("only", (1, 3), 8))
    assert box.report(0) == ("jump", 1)
    assert box.play(1, 2) == [None, ("jump", 3)]
    # A step back at the box from the second favourite: the first one
    assert box.play(3, 2) == [None, ("jump", 1)]
    # A step back from the first: it begins again
    assert box.play(1, 0) == [None, ("jump", 1)]
    assert box.play(1, 2, 3, 4) == [None, ("jump", 3), None, ("pause", None)]
    # The pause never arrived and the box moved on: sent again
    assert box.report(5) == ("pause", None)


async def test_only_the_favourites_begins_where_the_box_is(hass: HomeAssistant) -> None:
    """Placed on a favourite it plays on; behind the last one the first begins."""
    on_one = Box(hass, Plan("only", (1, 3), 8))
    assert on_one.report(3) is None
    behind = Box(hass, Plan("only", (1, 3), 8))
    assert behind.report(6) == ("jump", 1)


async def test_a_chapter_chosen_by_hand_plays(hass: HomeAssistant) -> None:
    """What Home Assistant sends the box to, or a hand picks elsewhere, is not left."""
    box = Box(hass, Plan("only", (1, 4), 8))
    assert box.report(1) is None
    # The buttons in Home Assistant follow the order
    assert box.favourites.neighbour("box", "t", 1) == 4
    assert box.favourites.neighbour("box", "t", -1) == 1
    assert box.favourites.neighbour("box", "other", 1) is None
    # The chapter list in Home Assistant: the chapter beside, no favourite
    box.favourites.chosen("box", "t", 2)
    assert box.report(2) is None
    assert box.favourites.neighbour("box", "t", 1) == 4
    assert box.favourites.neighbour("box", "t", -1) == 1
    # It runs out: on to the next favourite
    assert box.play(3, 4) == [("jump", 4), None]
    assert box.favourites.neighbour("box", "t", 1) is None
    # Picked in the app, two back: left alone, and after it the box pauses
    assert box.play(6, 7) == [None, ("pause", None)]
    # The box moved on before it got the chosen chapter: that one is let play, the
    # chosen one may still come
    again = Box(hass, Plan("only", (1, 4), 8))
    assert again.report(1) is None
    again.favourites.chosen("box", "t", 6)
    assert again.report(2) is None
    assert again.report(6) is None
    assert again.report(7) == ("pause", None)
    # It never comes: the chapter after is judged as ever
    never = Box(hass, Plan("only", (1, 4), 8))
    assert never.report(1) is None
    never.favourites.chosen("box", "t", 6)
    assert never.play(2, 3) == [None, ("jump", 4)]
    # Chosen before the figure was heard playing, or for a figure nothing is known of
    placed = Box(hass, Plan("first", (2,), 5))
    assert placed.report(0, paused=True) is None
    placed.favourites.chosen("box", "t", 3)
    assert placed.play(3, 4) == [None, None]
    unknown = Box(hass, Plan("first", (2,), 5), placed=False)
    unknown.favourites.chosen("box", "t", 3)
    unknown.favourites.chosen("box", None, 3)
    assert unknown.play(3, 4) == [None, None]
    # Taken off for long and chosen before it is back: the chosen chapter begins
    back = Box(hass, Plan("first", (2,), 5))
    assert back.report(0) == ("jump", 2)
    assert back.report(None, None) is None
    back.favourites.chosen("box", "t", 4)
    assert back.report(4, after=500) is None


async def test_a_command_that_did_not_arrive_is_sent_again(hass: HomeAssistant) -> None:
    """The box plays on in a chapter it was sent away from, or the cloud refused the command."""
    box = Box(hass, Plan("only", (1, 4), 8))
    assert box.play(1, 2) == [None, ("jump", 4)]
    assert box.report(3) == ("jump", 4)
    # Refused by the cloud: the very next report sends it again
    box.favourites.failed("box")
    box.favourites.failed("nobox")
    assert box.report(3) == ("jump", 4)
    assert box.play(4, 5) == [None, ("pause", None)]
    box.favourites.failed("box")
    assert box.report(5) == ("pause", None)
    # The same for the start after the end of the figure
    ending = Box(hass, Plan("first", (2,), 3))
    assert ending.play(2) == [None]
    assert ending.report(2, ended=True) == ("play", 0)
    ending.favourites.failed("box")
    assert ending.report(2, ended=True) == ("play", 0)


async def test_a_short_break_goes_on(hass: HomeAssistant) -> None:
    """The same figure placed again within two minutes plays on; later, or another, begins anew."""
    box = Box(hass, Plan("first", (2,), 4))
    assert box.report(0) == ("jump", 2)
    assert box.play(2, 3) == [None, ("jump", 0)]
    assert box.report(0) is None
    assert box.report(None, None) is None
    assert box.report(None, None) is None
    # Back after a minute, where it was
    assert box.report(0, after=60) is None
    assert box.report(1) is None
    assert box.report(None, None) is None
    assert box.report(1, after=121) == ("jump", 2)
    assert box.report(2) is None
    # Another figure in between
    assert box.report(0, "other") == ("jump", 2)
    assert box.report(2, "other") is None
    assert box.report(1) == ("jump", 2)


async def test_everything_today(hass: HomeAssistant) -> None:
    """The page lets the figure play everything until it is taken off, and ends that."""
    box = Box(hass, Plan("only", (1,), 4))
    # Before anything was reported: the figure counts as playing
    box.favourites.suspend("box", "t", True)
    assert box.favourites.suspended("box", "t")
    assert not box.favourites.suspended("box", "other")
    assert box.play(0, 2, 3) == [None, None, None]
    assert box.favourites.neighbour("box", "t", 1) is None
    assert box.favourites.first("box", "t") is None
    box.favourites.suspend("box", "t", False)
    # The chapter that plays is let run out
    assert box.report(3) is None
    assert box.favourites.steering("box", "t") == "only"
    # Taken off for long: steered anew
    assert box.report(None, None) is None
    box.favourites.suspend("box", "t", True)
    assert box.report(0, after=500) == ("jump", 1)
    # For another figure than the one known on the box
    box.favourites.suspend("box", "other", True)
    assert box.favourites.suspended("box", "other")


async def test_stars_change_while_the_figure_plays(hass: HomeAssistant) -> None:
    """A star set or taken off changes the order from the chapter that plays; nothing jumps."""
    box = Box(hass, None)
    assert box.play(0, 1) == [None, None]
    assert box.favourites.steering("box", "t") is None
    # The first star, on another chapter: the order begins behind the chapter that plays
    box.plan = Plan("only", (3,), 5)
    assert box.report(1) is None
    assert box.report(2) == ("jump", 3)
    # A second star while the box is on its way there
    box.plan = Plan("only", (3, 4), 5)
    assert box.play(3, 4) == [None, None]
    # The star of the chapter that plays is taken off: it runs out, then the box pauses
    box.plan = Plan("only", (3,), 5)
    assert box.report(4) is None
    # Switched off: nothing is steered
    box.plan = None
    assert box.play(0, 1, 2) == [None, None, None]


async def test_a_restart_changes_nothing(hass: HomeAssistant) -> None:
    """What a box plays is kept: after a restart the figure goes on, with its first chapter."""
    box = Box(hass, Plan("random", (1, 2, 3), 6))
    first = box.report(0)
    assert first is not None
    box.report(first[1])
    await box.favourites.async_save()
    after = FavouriteChapters(_store(hass), random.Random(9))
    await after.async_load()
    box.favourites = after
    # Nothing known of the order before the first report
    assert after.steering("box", "t") is None
    assert box.report(first[1]) is None
    assert after.first("box", "t") == first[1]
    # Suspended figures stay so
    after.suspend("box", "t", True)
    await after.async_save()
    again = FavouriteChapters(_store(hass))
    await again.async_load()
    assert again.suspended("box", "t")


async def test_a_box_that_never_gets_the_command_is_left_alone(hass: HomeAssistant) -> None:
    """After three refusals in a row the chapter plays; the chapter after it gets one try."""
    box = Box(hass, Plan("only", (1, 6), 8))
    assert box.play(1, 2) == [None, ("jump", 6)]
    box.favourites.failed("box")
    assert box.report(2) == ("jump", 6)
    box.favourites.failed("box")
    assert box.report(2) == ("jump", 6)
    box.favourites.failed("box")
    assert box.report(2) is None
    assert box.report(2, position=9.0) is None
    # The next chapter: one more try, and given up at once when it fails too
    assert box.report(3) == ("jump", 6)
    box.favourites.failed("box")
    assert box.report(3) is None
    # A command that arrives counts from the start again
    assert box.play(4, 6) == [("jump", 6), None]
    assert box.report(7) == ("pause", None)
    box.favourites.failed("box")
    assert box.report(7) == ("pause", None)


async def test_a_star_set_while_a_command_travels(hass: HomeAssistant) -> None:
    """The order changes while the box is sent somewhere: the next report is judged by the new one."""
    box = Box(hass, Plan("only", (1, 5), 8))
    assert box.play(1, 2) == [None, ("jump", 5)]
    # The command was lost, and chapter 4 gets a star meanwhile
    box.plan = Plan("only", (1, 4, 5), 8)
    assert box.report(2) == ("jump", 4)
    assert box.report(4) is None
    # The same for a pause on its way: the chapter behind the end is a favourite now
    assert box.play(5, 6) == [None, ("pause", None)]
    box.plan = Plan("only", (1, 4, 5, 6), 8)
    assert box.report(6) is None
    assert box.report(7) == ("pause", None)


async def test_another_favourite_at_the_front_each_time(hass: HomeAssistant) -> None:
    """Placed again, "random" does not begin with the favourite of last time."""
    box = Box(hass, Plan("random", (1, 3), 5))
    firsts = []
    for _ in range(6):
        box.report(0, after=500)
        firsts.append(box.favourites.first("box", "t"))
        box.report(None, None)
    assert firsts in ([1, 3, 1, 3, 1, 3], [3, 1, 3, 1, 3, 1])
    await box.favourites.async_save()
    after = FavouriteChapters(_store(hass))
    await after.async_load()
    box.favourites = after
    box.report(0, after=500)
    assert after.first("box", "t") != firsts[-1]


async def test_only_changes_are_written(hass: HomeAssistant) -> None:
    """Reports that change nothing of what is kept write nothing; boxes that left are forgotten."""
    box = Box(hass, Plan("only", (1,), 4))
    writes: list[int] = []
    box.favourites._store.async_delay_save = lambda *_: writes.append(1)  # type: ignore[method-assign]
    box.report(1)
    assert len(writes) == 1
    for position in (10.0, 20.0, 30.0):
        box.report(1, position=position)
    box.report(1, paused=True)
    assert len(writes) == 1
    box.report(None, None)
    box.report(None, None)
    assert len(writes) == 2
    assert box.report(1, after=10) is None
    assert len(writes) == 3


async def test_what_left_the_account_is_forgotten_after_a_while(hass: HomeAssistant) -> None:
    """One answer of the cloud without a box or a figure proves nothing."""
    box = Box(hass, Plan("random", (1, 2), 4))
    chapters = box.favourites
    await chapters.async_set(_tonie(), [1, 2], None)
    box.report(0)
    first = chapters.first("box", "t")
    now = 1_000_000.0
    # The box is missing from two polls and back with the third: nothing is lost
    chapters.keep(set(), {"t"}, now)
    chapters.keep(set(), {"t"}, now)
    chapters.keep({"box"}, {"t"}, now)
    chapters.keep(set(), {"t"}, now)
    chapters.keep(set(), {"t"}, now)
    assert chapters.first("box", "t") == first
    chapters.keep(set(), {"t"}, now)
    assert chapters.first("box", "t") is None
    # The figure is gone for weeks and comes back: its stars are there
    chapters.keep(set(), set(), now)
    chapters.keep(set(), set(), now + 29 * 24 * 3600)
    assert chapters.get("t") == Favourites(None, (1, 2))
    chapters.keep(set(), {"t"}, now + 29 * 24 * 3600)
    chapters.keep(set(), set(), now + 40 * 24 * 3600)
    assert chapters.get("t") == Favourites(None, (1, 2))
    # A month after it was last seen they go, and the store says since when it is missing
    await chapters.async_save()
    after = FavouriteChapters(_store(hass))
    await after.async_load()
    after.keep(set(), set(), now + 69 * 24 * 3600)
    assert after.get("t") == Favourites(None, (1, 2))
    after.keep(set(), set(), now + 71 * 24 * 3600)
    assert after.get("t") is None


async def test_the_pause_at_the_end_survives_a_restart(hass: HomeAssistant) -> None:
    """Play pressed after a restart still sets the figure free."""
    box = Box(hass, Plan("only", (1,), 4))
    assert box.play(1, 2) == [None, ("pause", None)]
    assert box.report(2, paused=True) is None
    await box.favourites.async_save()
    after = FavouriteChapters(_store(hass))
    await after.async_load()
    box.favourites = after
    assert box.report(2) is None
    assert after.suspended("box", "t")
    assert box.play(3, 0) == [None, None]


async def test_the_mode_alone_leaves_the_stars(hass: HomeAssistant) -> None:
    """A mode set without stars keeps those the figure has."""
    chapters = FavouriteChapters(_store(hass))
    bought = _tonie()
    creative = Tonie("c", "h", TonieKind.CREATIVE, "C", chapters=(Chapter("x", ""),))
    await chapters.async_set(bought, [1, 3], None)
    await chapters.async_star(creative, 0)
    assert await chapters.async_set_mode(bought, "only") == Favourites("only", (1, 3))
    assert await chapters.async_set_mode(creative, "off") == Favourites("off", (), ("x",))
    assert await chapters.async_set_mode(_tonie(chapters=2), "first") == Favourites("first", (1, 3))
    # Neither stars nor a mode: forgotten
    await chapters.async_set(bought, [], "only")
    assert await chapters.async_set_mode(bought, None) is None


async def test_chapters_of_a_creative_figure_that_share_an_id(hass: HomeAssistant) -> None:
    """The star goes by the chapter's ID: it is set and taken off for all that share it."""
    chapters = FavouriteChapters(_store(hass))
    twins = _tonie(TonieKind.CREATIVE, chapters=3, ids="aba")
    assert await chapters.async_star(twins, 0) is True
    assert chapters.indexes(twins) == (0, 2)
    assert await chapters.async_star(twins, 0) is False
    assert chapters.indexes(twins) == ()
    assert chapters.get("t") is None
    assert await chapters.async_star(twins, 2, True) is True
    assert await chapters.async_star(twins, 1, True) is True
    assert await chapters.async_star(twins, 1, True) is True
    # A chapter that is gone loses its star with the next change
    assert chapters.get("t") == Favourites(None, (), ("a", "b"))
    assert await chapters.async_star(_tonie(TonieKind.CREATIVE, chapters=2, ids="bc"), 1) is True
    assert chapters.get("t") == Favourites(None, (), ("b", "c"))
    # Back on the first figure, "c" is gone and "b" loses its star: nothing is left
    assert await chapters.async_star(twins, 1, False) is False
    assert chapters.get("t") is None


# ---------------------------------------------------------------- the page


async def _ask(client: Any, msg: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(msg)
    return await client.receive_json()


def _set(tonie_id: str, chapters: list[int], mode: str | None = None) -> dict[str, Any]:
    return {
        "type": f"{DOMAIN}/favourites/set",
        "tonie_id": tonie_id,
        "chapters": chapters,
        "mode": mode,
    }


async def test_set_favourites(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The page sets the favourites of a figure and its mode, and reads them with the library."""
    client = await hass_ws_client(hass)
    result = await _ask(client, _set(TONIE_ID, [1, 0]))
    assert result["success"], result
    assert result["result"] == {"favourites": {"mode": None, "chapters": [0, 1]}}
    creative = await _ask(client, _set(CREATIVE_ID, [2], "only"))
    assert creative["result"] == {"favourites": {"mode": "only", "chapters": [2]}}
    assert setup_entry.runtime_data.favourites.get(CREATIVE_ID) == Favourites("only", (), ("ch3",))
    library = await _ask(client, {"type": f"{DOMAIN}/library"})
    by_id = {t["id"]: t for t in library["result"]["tonies"]}
    assert by_id[TONIE_ID]["favourites"] == {"mode": None, "chapters": [0, 1]}
    assert by_id[CREATIVE_ID]["favourites"] == {"mode": "only", "chapters": [2]}
    assert by_id[DISC_ID]["favourites"] is None
    # One star at a time
    star = {"type": f"{DOMAIN}/favourites/star", "tonie_id": TONIE_ID, "chapter": 4}
    assert (await _ask(client, star))["result"]["favourites"]["chapters"] == [0, 1, 4]
    assert (await _ask(client, star))["result"]["favourites"]["chapters"] == [0, 1]
    kept = await _ask(client, {**star, "chapter": 0, "favourite": True})
    assert kept["result"]["favourites"]["chapters"] == [0, 1]
    # The mode alone, as the figure's settings send it: the stars stay
    mode = {"type": f"{DOMAIN}/favourites/set", "tonie_id": TONIE_ID, "mode": "random"}
    assert (await _ask(client, mode))["result"] == {
        "favourites": {"mode": "random", "chapters": [0, 1]}
    }
    # Without stars the mode stays; without either the figure is forgotten
    off = await _ask(client, _set(TONIE_ID, [], "off"))
    assert off["result"] == {"favourites": {"mode": "off", "chapters": []}}
    assert (await _ask(client, _set(TONIE_ID, [])))["result"] == {"favourites": None}


async def test_stars_of_a_creative_figure_follow_their_chapters(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Arranged anew, the star is where its chapter went; a removed chapter loses it."""
    client = await hass_ws_client(hass)
    assert (await _ask(client, _set(CREATIVE_ID, [0, 2])))["success"]
    arranged = await _ask(
        client,
        {
            "type": f"{DOMAIN}/chapters/arrange",
            "tonie_id": CREATIVE_ID,
            "chapters": ["ch3", "ch2"],
        },
    )
    assert arranged["success"], arranged
    assert arranged["result"]["favourites"] == {"mode": None, "chapters": [0]}


@pytest.mark.parametrize(
    ("msg", "code"),
    [
        (_set("nope", [0]), "unknown_figure"),
        (_set(TONIE_ID, [0, 9]), "unknown_chapter"),
        (_set(CREATIVE_ID, [3]), "unknown_chapter"),
        (_set(TONIE_ID, [-1]), "invalid_format"),
        (_set(TONIE_ID, [0], "loud"), "invalid_format"),
        ({"type": f"{DOMAIN}/favourites/star", "tonie_id": "nope", "chapter": 0}, "unknown_figure"),
        (
            {"type": f"{DOMAIN}/favourites/star", "tonie_id": TONIE_ID, "chapter": 8},
            "unknown_chapter",
        ),
        ({"type": f"{DOMAIN}/box/favourites", "box_id": "nobox", "suspended": True}, "unknown_box"),
        (
            {"type": f"{DOMAIN}/box/favourites", "box_id": CLASSIC_BOX_ID, "suspended": True},
            "not_supported",
        ),
    ],
)
async def test_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    msg: dict[str, Any],
    code: str,
) -> None:
    """Unknown figures, boxes and chapters the figure does not have are refused."""
    client = await hass_ws_client(hass)
    result = await _ask(client, msg)
    assert not result["success"]
    assert result["error"]["code"] == code


@pytest.mark.parametrize(
    "msg",
    [
        _set(TONIE_ID, [0]),
        {"type": f"{DOMAIN}/favourites/star", "tonie_id": TONIE_ID, "chapter": 0},
        {"type": f"{DOMAIN}/box/favourites", "box_id": BOX_ID, "suspended": True},
    ],
)
async def test_the_page_needs_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
    msg: dict[str, Any],
) -> None:
    """The commands of the page are for administrators; every user has the actions."""
    client = await hass_ws_client(hass, access_token=hass_read_only_access_token)
    result = await _ask(client, msg)
    assert not result["success"]
    assert result["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------- the box


async def _settle(hass: HomeAssistant) -> None:
    """Let the steering task run; the push channel's endless loop is a background task too."""
    for _ in range(5):
        await asyncio.sleep(0)
    await hass.async_block_till_done()


def _jump(chapter: int) -> tuple[str, str, dict[str, Any]]:
    return (MAC, "playback", {"action": "setPosition", "chapter": chapter, "ms": 0})


PAUSE = (MAC, "playback", {"action": "pause"})
PLAY = (MAC, "playback", {"action": "start"})


async def _box(client: Any) -> dict[str, Any]:
    overview = await _ask(client, {"type": f"{DOMAIN}/overview"})
    return next(b for b in overview["result"]["boxes"] if b["id"] == BOX_ID)


async def test_box_is_steered_by_the_mode_of_the_account(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Favourites first unless the account or the figure says otherwise; the page shows it."""
    client = await hass_ws_client(hass)
    coordinator = setup_entry.runtime_data.coordinator
    tonie = coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [7], None)
    channel = push.last
    channel.connect()
    channel.removed()
    channel.playback(chapter=0)
    await _settle(hass)
    assert channel.commands == [_jump(7)]
    channel.playback(chapter=7)
    # The end of the figure: the other chapters follow
    channel.playback(chapter=7, ended=True)
    await _settle(hass)
    assert channel.commands[1:] == [_jump(0), PLAY]
    channel.playback(chapter=0)
    shown = (await _box(client))["playback"]
    assert shown["favourites"] == {
        "chapters": [7],
        "mode": "first",
        "paused_mode": None,
        "suspended": False,
    }
    assert [c["favourite"] for c in shown["chapter_list"]] == [False] * 7 + [True]
    # The account plays only the favourites from now on
    changed = await _ask(
        client,
        {
            "type": f"{DOMAIN}/preferences/set",
            "entry_id": setup_entry.entry_id,
            "favourites_mode": "only",
        },
    )
    assert changed["result"]["favourites_mode"] == "only"
    assert (await _box(client))["playback"]["favourites"]["mode"] == "only"
    channel.playback(chapter=1)
    await _settle(hass)
    assert channel.commands[3:] == [_jump(7)]
    # The figure has a mode of its own: off
    await setup_entry.runtime_data.favourites.async_set(tonie, [7], "off")
    assert (await _box(client))["playback"]["favourites"]["mode"] is None
    channel.playback(chapter=7)
    channel.playback(chapter=2)
    channel.removed()
    await _settle(hass)
    assert len(channel.commands) == 4


async def test_everything_today_from_the_page(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The page lets the figure on a box play everything, and steers it again."""
    client = await hass_ws_client(hass)
    tonie = setup_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [3], "only")
    channel = push.last
    channel.connect()
    nothing = await _ask(
        client, {"type": f"{DOMAIN}/box/favourites", "box_id": BOX_ID, "suspended": True}
    )
    # The cloud names the figure placed on the box even before the box reports
    assert nothing["success"], nothing
    channel.playback(chapter=3)
    answer = await _ask(
        client, {"type": f"{DOMAIN}/box/favourites", "box_id": BOX_ID, "suspended": True}
    )
    assert answer["result"]["playback"]["favourites"] == {
        "chapters": [3],
        "mode": None,
        "paused_mode": "only",
        "suspended": True,
    }
    channel.playback(chapter=4)
    await _settle(hass)
    assert channel.commands == []
    answer = await _ask(
        client, {"type": f"{DOMAIN}/box/favourites", "box_id": BOX_ID, "suspended": False}
    )
    assert answer["result"]["playback"]["favourites"]["mode"] == "only"
    channel.playback(chapter=5)
    await _settle(hass)
    assert channel.commands == [PAUSE]
    channel.removed()
    gone = await _ask(
        client, {"type": f"{DOMAIN}/box/favourites", "box_id": BOX_ID, "suspended": True}
    )
    assert gone["error"]["code"] == "nothing_plays"


async def test_only_the_favourites_within_a_bedtime(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The bedtime mode: favourites first by day, only they from the sleep time to the wake-up."""
    coordinator = setup_entry.runtime_data.coordinator
    box_state = coordinator.data.boxes[BOX_ID]
    box_state.schedules = (
        BedtimeSchedule(
            "s1",
            "Night",
            "19:00",
            "07:00",
            ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
            enabled=True,
        ),
    )
    tonie = coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [1], "bedtime")
    zone = ZoneInfo(box_state.box.timezone or "UTC")
    freezer.move_to(datetime(2026, 11, 27, 15, 0, tzinfo=zone))
    assert coordinator.favourite_mode(box_state, TONIE_ID) == "first"
    assert coordinator.favourite_mode(None, TONIE_ID) == "first"
    freezer.move_to(datetime(2026, 11, 27, 19, 30, tzinfo=zone))
    assert coordinator.favourite_mode(box_state, TONIE_ID) == "only"
    channel = push.last
    channel.connect()
    channel.playback(chapter=1)
    channel.playback(chapter=2)
    await _settle(hass)
    assert channel.commands == [PAUSE]


async def test_box_is_left_alone(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """No stars, a Tune on the figure, a figure nobody knows: nothing is sent."""
    coordinator = setup_entry.runtime_data.coordinator
    favourites = setup_entry.runtime_data.favourites
    channel = push.last
    channel.connect()
    channel.playback(chapter=0)
    channel.playback(chapter=0, tonie_id="unknown")
    channel.removed()
    await _settle(hass)
    assert channel.commands == []
    # The box plays the Tune that lies on the figure, not the figure's chapters
    await favourites.async_set(coordinator.data.tonies[TONIE_ID], [1], "only")
    coordinator.tunes = (Tune("tune1", "Lied", assigned=(TONIE_ID,)),)
    channel.playback(chapter=0)
    await _settle(hass)
    assert channel.commands == []
    assert coordinator.favourite_plan(coordinator.data.boxes[BOX_ID], TONIE_ID) is None
    # Nor do the stars show or change for what plays: the chapters are the Tune's
    player = entity_id(hass, "media_player", f"{BOX_ID}")
    state = hass.states.get(player)
    assert state is not None
    assert state.attributes["favourite"] is None
    assert {c["favourite"] for c in state.attributes["chapter_list"]} == {None}
    for action in ("set_favourite", "play_favourite"):
        with pytest.raises(ServiceValidationError) as refused:
            await hass.services.async_call(DOMAIN, action, {"entity_id": player}, blocking=True)
        assert refused.value.translation_key == "tune_plays"
    assert favourites.indexes(coordinator.data.tonies[TONIE_ID]) == (1,)
    coordinator.tunes = ()
    # A figure whose chapters nobody knows has no order of all chapters; only the favourites do
    disc = coordinator.data.tonies[DISC_ID]
    await favourites.async_set(disc, [1], "first")
    if not disc.chapters:
        assert coordinator.favourite_plan(coordinator.data.boxes[BOX_ID], DISC_ID) is None


async def test_a_refused_command_is_sent_with_the_next_report(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A command the channel cannot send is logged, not raised, and tried again."""
    tonie = setup_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [1], "only")
    channel = push.last
    channel.connect()
    channel.removed()
    channel.command_error = CloudConnectionError("gone")
    channel.playback(chapter=0)
    await _settle(hass)
    assert "not steered" in caplog.text
    assert channel.commands == []
    channel.command_error = None
    channel.playback(chapter=0, position=70.0)
    await _settle(hass)
    assert channel.commands == [_jump(1)]


async def test_the_buttons_follow_the_order(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Next and previous lead to the chapters of the order; a chapter from the list plays."""
    client = await hass_ws_client(hass)
    player = entity_id(hass, "media_player", f"{BOX_ID}")
    tonie = setup_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [1, 5], "only")
    channel = push.last
    channel.connect()
    channel.playback(chapter=1)
    await hass.services.async_call(
        "media_player", "media_next_track", {"entity_id": player}, blocking=True
    )
    assert channel.commands == [_jump(5)]
    channel.playback(chapter=5)
    command = {"type": f"{DOMAIN}/box/command", "box_id": BOX_ID}
    assert (await _ask(client, {**command, "command": "previous"}))["success"]
    assert channel.commands[-1] == _jump(1)
    channel.playback(chapter=1)
    # A chapter that is no favourite, from the list of the page and from the media browser
    assert (await _ask(client, {**command, "command": "chapter", "value": 2}))["success"]
    channel.playback(chapter=2)
    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": player,
            "media_content_type": "track",
            "media_content_id": f"chapter:{TONIE_ID}:3",
        },
        blocking=True,
    )
    channel.playback(chapter=3)
    await _settle(hass)
    assert channel.commands == [_jump(5), _jump(1), _jump(2), _jump(3)]
    # Behind the last favourite the next button leads to the chapter beside
    channel.playback(chapter=5)
    await hass.services.async_call(
        "media_player", "media_next_track", {"entity_id": player}, blocking=True
    )
    assert channel.commands[-1] == _jump(6)
    channel.playback(chapter=6)
    await _settle(hass)
    assert len(channel.commands) == 5


# ---------------------------------------------------------------- the actions


async def test_actions_of_every_user(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """A star for the chapter that plays, the next favourite, and the star as an attribute."""
    player = entity_id(hass, "media_player", f"{BOX_ID}")
    favourites = setup_entry.runtime_data.favourites
    tonie = setup_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    await favourites.async_set(tonie, [], "off")
    channel = push.last
    channel.connect()

    async def call(action: str, **data: Any) -> None:
        await hass.services.async_call(DOMAIN, action, {"entity_id": player, **data}, blocking=True)

    def star() -> Any:
        state = hass.states.get(player)
        assert state is not None
        return state.attributes["favourite"]

    channel.playback(chapter=2)
    assert star() is False
    with pytest.raises(ServiceValidationError) as nothing:
        await call("play_favourite")
    assert nothing.value.translation_key == "no_favourites"
    await call("set_favourite")
    assert star() is True
    assert favourites.indexes(tonie) == (2,)
    await call("set_favourite")
    assert star() is False
    await call("set_favourite", chapter=6, favourite=True)
    # As a script writes it: a word for the state
    await call("set_favourite", chapter=1, favourite="on")
    await call("set_favourite", chapter=1, favourite=True)
    assert favourites.indexes(tonie) == (0, 5)
    # The dashboard card draws its list of chapters from the media player
    state = hass.states.get(player)
    assert state is not None
    assert state.attributes["tonie_id"] == TONIE_ID
    assert [c["favourite"] for c in state.attributes["chapter_list"]] == [
        True,
        False,
        False,
        False,
        False,
        True,
        False,
        False,
    ]
    assert state.attributes["chapter_list"][1] == {
        "title": "Kapitel 2",
        "seconds": None,
        "favourite": False,
    }
    with pytest.raises(ServiceValidationError) as beyond:
        await call("set_favourite", chapter=9)
    assert beyond.value.translation_key == "unknown_chapter"
    # The next favourite behind the chapter that plays, then round to the first
    await call("play_favourite")
    assert channel.commands == [_jump(5), PLAY]
    channel.playback(chapter=5)
    assert star() is True
    await call("play_favourite")
    assert channel.commands[2:] == [_jump(0), PLAY]
    channel.command_error = CloudConnectionError("gone")
    with pytest.raises(HomeAssistantError) as failed:
        await call("play_favourite")
    assert failed.value.translation_key == "command_failed"
    channel.command_error = None
    # Without a chapter that plays there is none to mark
    channel.removed()
    assert star() is None
    gone = hass.states.get(player)
    assert gone is not None
    assert (gone.attributes["tonie_id"], gone.attributes["chapter_list"]) == (None, None)
    with pytest.raises(ServiceValidationError):
        await call("set_favourite")
    with pytest.raises(ServiceValidationError) as empty:
        await call("play_favourite")
    assert empty.value.translation_key == "nothing_plays"


async def test_runs_are_written_and_removed_with_the_account(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Unloading writes what the boxes play; the store goes with the account."""
    tonie = setup_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [1], "only")
    push.last.connect()
    push.last.playback(chapter=1)
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    key = f"{DOMAIN}.{setup_entry.entry_id}.favourites"
    assert hass_storage[key]["data"] == {
        "tonies": {TONIE_ID: {"mode": "only", "chapters": [1]}},
        "runs": {
            BOX_ID: {
                "figure": TONIE_ID,
                "first": 1,
                "started": True,
                "base": 1,
                "suspended": False,
                "left": None,
                "paused": None,
            }
        },
        "firsts": {},
        "gone": {},
    }


async def test_a_chapter_is_chosen_before_the_box_reports(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The figure the cloud names counts until the box itself says what it plays."""
    client = await hass_ws_client(hass)
    player = entity_id(hass, "media_player", f"{BOX_ID}")
    channel = push.last
    channel.connect()
    state = hass.states.get(player)
    assert state is not None
    assert state.attributes["tonie_id"] == TONIE_ID
    await hass.services.async_call(
        "media_player",
        "play_media",
        {
            "entity_id": player,
            "media_content_type": "track",
            "media_content_id": f"chapter:{TONIE_ID}:3",
        },
        blocking=True,
    )
    command = {"type": f"{DOMAIN}/box/command", "box_id": BOX_ID, "command": "chapter", "value": 4}
    assert (await _ask(client, command))["success"]
    assert channel.commands == [_jump(3), _jump(4)]
    # A chapter meant for one figure does not play another one's, nor a Tune's
    assert (await _ask(client, {**command, "tonie_id": DISC_ID}))["error"]["code"] == "other_figure"
    assert (await _ask(client, {**command, "tonie_id": TONIE_ID}))["success"]
    coordinator = setup_entry.runtime_data.coordinator
    coordinator.tunes = (Tune("tune1", "Lied", assigned=(TONIE_ID,)),)
    assert (await _ask(client, {**command, "tonie_id": TONIE_ID}))["error"]["code"] == "tune_plays"
    coordinator.tunes = ()
    assert len(channel.commands) == 3
    # Taken off, there is no figure to play a chapter of
    channel.removed()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": player,
                "media_content_type": "track",
                "media_content_id": f"chapter:{TONIE_ID}:3",
            },
            blocking=True,
        )
    assert (await _ask(client, command))["error"]["code"] == "nothing_plays"


async def test_one_account_steers_a_box_two_accounts_see(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """Two accounts of one household: the first one keeps the stars and steers the box."""
    second = entry_for(
        cloud.add_account(
            "second",
            households=[{"id": HOUSEHOLD_ID, "name": "Home"}],
            boxes={HOUSEHOLD_ID: [tb2_box()]},
            content_tonies=[cloud.main.content_tonies[0]],
        )
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    other = second.runtime_data.coordinator
    # A star set through the second account lands with the first
    assert await other.async_star(TONIE_ID, 5) is True
    tonie = other.data.tonies[TONIE_ID]
    assert setup_entry.runtime_data.favourites.indexes(tonie) == (5,)
    assert second.runtime_data.favourites.get(TONIE_ID) is None
    assert other.playing_stars(tonie) == (5,)
    first, latest = push.instances
    first.connect()
    latest.connect()
    first.removed()
    latest.removed()
    first.playback(chapter=0)
    latest.playback(chapter=0)
    await _settle(hass)
    assert first.commands == [_jump(5)]
    assert latest.commands == []
    # "Everything today" through either account reaches the one that steers
    other.suspend_favourites(BOX_ID, True)
    assert setup_entry.runtime_data.favourites.suspended(BOX_ID, TONIE_ID)


async def test_a_figure_found_playing_is_not_placed(hass: HomeAssistant) -> None:
    """Nothing known of a box: the figure on it plays on; an end found as it is starts nothing."""
    box = Box(hass, Plan("first", (2, 4), 8), placed=False)
    assert box.report(6) is None
    assert box.favourites.steering("box", "t") == "first"
    # From here on the order holds
    assert box.report(7) is None
    assert box.report(None, None) is None
    assert box.report(0, after=500) == ("jump", 2)
    # After a restart the end of the figure is found, not heard: the box stays silent
    assert box.play(2, 3) == [None, ("jump", 4)]
    assert box.report(4) is None
    await box.favourites.async_save()
    after = FavouriteChapters(_store(hass))
    await after.async_load()
    box.favourites = after
    assert box.report(7, ended=True) is None
    assert box.report(7, ended=True) is None
    # Heard playing first, another chapter than the one that ends: nothing either
    gap = Box(hass, Plan("first", (2, 4), 5))
    assert gap.report(2) is None
    assert gap.report(4, ended=True) is None


async def test_started_again_after_its_end(hass: HomeAssistant) -> None:
    """The order was over with the figure: play pressed then begins it anew."""
    box = Box(hass, Plan("only", (2, 4), 5))
    assert box.play(0, 2, 3, 4) == [("jump", 2), None, ("jump", 4), None]
    assert box.report(4, ended=True) is None
    assert box.report(0) == ("jump", 2)
    assert box.report(2) is None


async def test_a_pause_on_its_way_survives_a_restart(hass: HomeAssistant) -> None:
    """The pause was sent, not yet reported: after a restart one press of play sets the figure free."""
    box = Box(hass, Plan("only", (1, 2), 5))
    assert box.play(1, 2, 3) == [None, None, ("pause", None)]
    await box.favourites.async_save()
    after = FavouriteChapters(_store(hass))
    await after.async_load()
    box.favourites = after
    assert box.report(3, paused=True) is None
    assert box.report(3) is None
    assert after.suspended("box", "t")


async def test_the_buttons_know_the_order_after_a_restart(hass: HomeAssistant) -> None:
    """Before the box reports again, the plan is given to what it played."""
    box = Box(hass, Plan("only", (1, 4), 8))
    assert box.report(1) is None
    await box.favourites.async_save()
    after = FavouriteChapters(_store(hass))
    await after.async_load()
    assert after.neighbour("box", "t", 1) is None
    after.sync("box", "other", box.plan)
    assert after.neighbour("box", "t", 1) is None
    after.sync("box", "t", box.plan)
    assert after.neighbour("box", "t", 1) == 4
    assert after.first("box", "t") == 1


async def test_a_chapter_chosen_for_a_figure_that_begins_anew(hass: HomeAssistant) -> None:
    """The order was over with the figure: the chapter Home Assistant sends it to plays."""
    box = Box(hass, Plan("first", (1,), 3))
    assert box.play(0, 1) == [("jump", 1), None]
    assert box.report(2) == ("jump", 0)
    assert box.play(0, 1) == [None, ("jump", 2)]
    assert box.report(2) is None
    assert box.report(2, ended=True) is None
    # The chapter that just ended, again (repeat of one chapter): it is not the first favourite
    box.favourites.chosen("box", "t", 2)
    assert box.report(2) is None
    assert box.report(2, ended=True) is None
    # A command that did not reach the box is taken back: the figure begins with its order
    box.favourites.chosen("box", "t", 2)
    box.favourites.unchosen("box", 0)
    box.favourites.unchosen("box", 2)
    box.favourites.unchosen("nobox", 2)
    assert box.report(2) == ("jump", 1)


async def test_placed_again_after_the_pause_at_the_end(hass: HomeAssistant) -> None:
    """Lifted and put back within two minutes after the order was over: it begins anew."""
    box = Box(hass, Plan("only", (0, 1), 4))
    assert box.play(0, 1, 2) == [None, None, ("pause", None)]
    assert box.report(2, paused=True) is None
    assert box.report(None, None) is None
    # The box plays by itself where it was: no hand pressed play
    assert box.report(2, after=30) == ("jump", 0)
    assert not box.favourites.suspended("box", "t")
    assert box.report(0) is None


async def test_a_write_that_is_due_is_not_put_off(hass: HomeAssistant) -> None:
    """A figure placed is written within a second, whatever is written after it."""
    box = Box(hass, Plan("first", (2,), 4))
    delays: list[float] = []
    box.favourites._store.async_delay_save = lambda _data, delay: delays.append(delay)  # type: ignore[method-assign]
    assert box.report(0) == ("jump", 2)
    assert box.report(2) is None
    assert box.report(3) == ("jump", 0)
    assert delays[0] == 1
    assert all(delay <= 1 for delay in delays)
    assert len(delays) >= 2


async def test_a_command_of_home_assistant_that_fails_is_taken_back(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Next, a chapter from the list and the next favourite: refused by the cloud, nothing stays chosen."""
    client = await hass_ws_client(hass)
    player = entity_id(hass, "media_player", f"{BOX_ID}")
    coordinator = setup_entry.runtime_data.coordinator
    tonie = coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [1, 5], "only")
    channel = push.last
    channel.connect()
    channel.playback(chapter=1)
    channel.command_error = CloudConnectionError("gone")
    command = {"type": f"{DOMAIN}/box/command", "box_id": BOX_ID}
    assert (await _ask(client, {**command, "command": "chapter", "value": 3}))["error"]
    assert (await _ask(client, {**command, "command": "next"}))["error"]
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "play_favourite", {"entity_id": player}, blocking=True
        )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "media_player", "media_next_track", {"entity_id": player}, blocking=True
        )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": player,
                "media_content_type": "track",
                "media_content_id": f"chapter:{TONIE_ID}:3",
            },
            blocking=True,
        )
    channel.command_error = None
    # Nothing is chosen: the chapter behind the favourite is left at once
    channel.playback(chapter=2)
    await _settle(hass)
    assert channel.commands == [_jump(5)]


async def test_a_box_that_wakes_with_a_figure(hass: HomeAssistant) -> None:
    """A sleeping box wakes when a figure is placed: after its sleep the order begins."""
    box = Box(hass, Plan("first", (2,), 5), placed=False)
    # Nothing known of the box but that it is switched off
    box.favourites.away("box", box.now.timestamp())
    box.favourites.away("box", box.now.timestamp() + 5)
    assert box.report(0, paused=None, after=600) is None
    assert box.report(0) == ("jump", 2)
    assert box.play(2, 3) == [None, ("jump", 0)]
    # It falls asleep and wakes a moment later: the figure goes on
    box.favourites.away("box", box.now.timestamp())
    assert box.report(0, after=60) is None
    assert box.report(1) is None
    # After a longer sleep it begins anew
    box.favourites.away("box", box.now.timestamp())
    assert box.report(1, after=3600) == ("jump", 2)


async def test_the_box_is_switched_on_with_its_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Offline for a while, then awake with the figure on it: the favourites come first."""
    coordinator = setup_entry.runtime_data.coordinator
    tonie = coordinator.data.tonies[TONIE_ID]
    await setup_entry.runtime_data.favourites.async_set(tonie, [5], None)
    channel = push.last
    channel.connect()
    channel.playback(chapter=3)
    await _settle(hass)
    # Found playing: nothing jumps
    assert channel.commands == []
    # The box says it is offline once more while it is awake: no sleep
    channel.online(False)
    channel.playback(chapter=3, position=60.0)
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await _settle(hass)
    freezer.tick(timedelta(minutes=10))
    channel.playback(chapter=4, position=0.0)
    await _settle(hass)
    assert channel.commands == []
    # It goes to sleep and stays so
    channel.online(False)
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await _settle(hass)
    freezer.tick(timedelta(hours=2))
    # Woken by the figure: what it reports first does not play yet, "offline" comes once more
    channel.playback(chapter=4, paused=None)
    channel.online(False)
    channel.playback(chapter=4)
    await _settle(hass)
    assert channel.commands == [_jump(5)]
