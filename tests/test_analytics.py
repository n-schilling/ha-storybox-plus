"""Listening time as daily sums: counting, saving, pruning and the queries."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant.common import async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus.analytics import SAVE_DELAY, Analytics
from custom_components.storybox_plus.const import ANALYTICS_KEEP_DAYS

TZ = ZoneInfo("Europe/Berlin")
START = datetime(2026, 11, 4, 10, 0, tzinfo=TZ)
TODAY = "2026-11-04"
YESTERDAY = "2026-11-03"


class Clock:
    """A clock the test moves."""

    def __init__(self, start: datetime = START) -> None:
        self.value = start

    def now(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> Clock:
    """The clock of the counter."""
    return Clock()


@pytest.fixture
def store() -> Mock:
    """A store that remembers what was asked of it."""
    mock = Mock()
    mock.async_load = AsyncMock(return_value=None)
    mock.async_save = AsyncMock()
    mock.async_remove = AsyncMock()
    return mock


@pytest.fixture
async def analytics(store: Mock, clock: Clock) -> Analytics:
    """An empty counter."""
    counter = Analytics(store, clock.now)
    await counter.async_load()
    return counter


async def _loaded(store: Mock, clock: Clock, days: Any) -> Analytics:
    store.async_load.return_value = {"days": days}
    counter = Analytics(store, clock.now)
    await counter.async_load()
    return counter


def test_counts_while_playing(analytics: Analytics, clock: Clock) -> None:
    """Time is booked when ticked or stopped; the sums answer every query."""
    analytics.observe("box1", "t1", True)
    assert analytics.per_tonie() == {}
    clock.advance(60)
    analytics.tick()
    assert analytics.per_tonie() == {"t1": 60}
    clock.advance(30)
    analytics.tick()
    assert analytics.per_tonie() == {"t1": 90}
    clock.advance(10)
    analytics.observe("box1", "t1", False)
    analytics.observe("box1", "t1", False)
    clock.advance(500)
    analytics.tick()
    assert analytics.per_tonie() == {"t1": 100}
    assert analytics.per_box() == {"box1": 100}
    assert analytics.per_day() == {TODAY: 100}
    assert analytics.total() == 100
    assert analytics.first_day == date(2026, 11, 4)


def test_switching_the_figure_closes_the_count(analytics: Analytics, clock: Clock) -> None:
    """Another figure ends the first figure's span and starts its own."""
    analytics.observe("box1", "t1", True)
    clock.advance(60)
    analytics.observe("box1", "t2", True)
    clock.advance(40)
    analytics.observe("box1", "t2", False)
    assert analytics.per_tonie() == {"t1": 60, "t2": 40}


def test_two_boxes_count_apart(analytics: Analytics, clock: Clock) -> None:
    """Boxes count independently, also the same figure."""
    analytics.observe("box1", "t1", True)
    clock.advance(10)
    analytics.observe("box2", "t1", True)
    clock.advance(20)
    analytics.observe("box1", "t1", False)
    analytics.observe("box2", "t1", False)
    assert analytics.per_box() == {"box1": 30, "box2": 20}
    assert analytics.per_tonie() == {"t1": 50}
    clock.advance(100)
    analytics.tick()
    assert analytics.total() == 50


def test_nothing_counts_without_a_figure(analytics: Analytics, clock: Clock) -> None:
    """Playing without a known figure counts nothing and ends what was counted."""
    analytics.observe("box1", None, True)
    clock.advance(60)
    analytics.tick()
    assert analytics.total() == 0
    analytics.observe("box1", "t1", True)
    clock.advance(30)
    analytics.observe("box1", None, True)
    clock.advance(30)
    analytics.observe("box1", None, False)
    assert analytics.per_tonie() == {"t1": 30}


def test_pause_is_not_counted(analytics: Analytics, clock: Clock) -> None:
    """Only the time between start and pause counts."""
    analytics.observe("box1", "t1", True)
    clock.advance(10)
    analytics.observe("box1", "t1", False)
    clock.advance(100)
    analytics.observe("box1", "t1", True)
    analytics.observe("box1", "t1", True)
    clock.advance(5)
    analytics.observe("box1", "t1", False)
    assert analytics.total() == 15


def test_midnight_splits_the_span(analytics: Analytics, clock: Clock) -> None:
    """A span over midnight is booked on both days, in the clock's zone."""
    clock.value = datetime(2026, 11, 4, 23, 59, tzinfo=TZ)
    analytics.observe("box1", "t1", True)
    clock.advance(120)
    analytics.observe("box1", "t1", False)
    assert analytics.per_day() == {"2026-11-04": 60, "2026-11-05": 60}
    assert analytics.first_day == date(2026, 11, 4)


def test_tick_without_time_adds_nothing(analytics: Analytics, store: Mock) -> None:
    """A tick right after the start books nothing and marks nothing to save."""
    analytics.observe("box1", "t1", True)
    analytics.tick()
    assert analytics.per_tonie() == {}
    analytics.save_soon()
    store.async_delay_save.assert_not_called()


async def test_load_coerces_and_prunes(store: Mock, clock: Clock) -> None:
    """Stored sums are read as integers; days older than the limit are dropped."""
    old = (START.date() - timedelta(days=ANALYTICS_KEEP_DAYS + 1)).isoformat()
    kept = (START.date() - timedelta(days=ANALYTICS_KEEP_DAYS)).isoformat()
    analytics = await _loaded(
        store,
        clock,
        {
            old: {"box1": {"t1": 999}},
            kept: {"box1": {"t1": "120"}},
            YESTERDAY: {"box1": {"t1": 30.0, "t2": 5}},
        },
    )
    assert analytics.per_day() == {kept: 120, YESTERDAY: 35}
    assert analytics.per_tonie() == {"t1": 150, "t2": 5}
    assert all(isinstance(s, int) for s in analytics.per_tonie().values())
    assert analytics.first_day == date.fromisoformat(kept)
    # The pruning is something to save
    analytics.save_soon()
    store.async_delay_save.assert_called_once()


@pytest.mark.parametrize("stored", [None, {}, {"days": "broken"}, {"other": {}}])
async def test_load_without_usable_data(store: Mock, clock: Clock, stored: Any) -> None:
    """Missing or broken stored data means starting from nothing."""
    store.async_load.return_value = stored
    analytics = Analytics(store, clock.now)
    await analytics.async_load()
    assert analytics.per_day() == {}
    assert analytics.first_day is None
    assert analytics.total() == 0
    assert analytics.per_tonie() == {}
    analytics.save_soon()
    store.async_delay_save.assert_not_called()


async def test_queries_over_the_last_days(store: Mock, clock: Clock) -> None:
    """The day filter counts back from today; the ranking breaks ties by ID."""
    week_ago = (START.date() - timedelta(days=7)).isoformat()
    analytics = await _loaded(
        store,
        clock,
        {
            week_ago: {"box1": {"t1": 700, "t3": 50}},
            YESTERDAY: {"box1": {"t2": 100}, "box2": {"t1": 100}},
            TODAY: {"box1": {"t1": 10, "t4": 100}},
        },
    )
    assert analytics.per_day(1) == {TODAY: 110}
    assert analytics.per_day(2) == {YESTERDAY: 200, TODAY: 110}
    assert analytics.per_day(8) == analytics.per_day()
    assert analytics.total(2) == 310
    assert analytics.per_tonie(2) == {"t1": 110, "t2": 100, "t4": 100}
    assert analytics.per_box(2) == {"box1": 210, "box2": 100}
    assert analytics.per_tonie() == {"t1": 810, "t2": 100, "t3": 50, "t4": 100}


def test_save_soon_writes_once_per_change(analytics: Analytics, clock: Clock, store: Mock) -> None:
    """Only a change schedules a write, and only one until the next change."""
    analytics.observe("box1", "t1", True)
    clock.advance(10)
    analytics.tick()
    analytics.save_soon()
    analytics.save_soon()
    store.async_delay_save.assert_called_once()
    data_func, delay = store.async_delay_save.call_args.args
    assert delay == SAVE_DELAY
    assert data_func() == {
        "days": {TODAY: {"box1": {"t1": 10}}},
        "chapters": {},
        "hours": {TODAY: {"box1": {"10": 10}}},
        "placements": {},
        "active": {},
    }
    clock.advance(5)
    analytics.tick()
    analytics.save_soon()
    assert store.async_delay_save.call_count == 2


async def test_async_save_books_what_plays(analytics: Analytics, clock: Clock, store: Mock) -> None:
    """Saving now includes the running span and keeps counting it."""
    analytics.observe("box1", "t1", True)
    clock.advance(42)
    await analytics.async_save()
    store.async_save.assert_awaited_once_with(
        {
            "days": {TODAY: {"box1": {"t1": 42}}},
            "chapters": {},
            "hours": {TODAY: {"box1": {"10": 42}}},
            "placements": {},
            "active": {},
        }
    )
    clock.advance(8)
    await analytics.async_save()
    assert store.async_save.await_args.args[0]["days"] == {TODAY: {"box1": {"t1": 50}}}
    analytics.save_soon()
    store.async_delay_save.assert_not_called()


async def test_with_the_real_store(
    hass: HomeAssistant, hass_storage: dict[str, Any], clock: Clock
) -> None:
    """The delayed write lands in the store after the delay and is read back."""
    key = "storybox_plus.test.analytics"
    store: Store[Any] = Store(hass, 1, key)
    analytics = Analytics(store, clock.now)
    await analytics.async_load()
    analytics.observe("box1", "t1", True, 2)
    clock.advance(30)
    analytics.tick()
    analytics.save_soon()
    assert key not in hass_storage
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=SAVE_DELAY + 1))
    await hass.async_block_till_done()
    assert hass_storage[key]["data"] == {
        "days": {TODAY: {"box1": {"t1": 30}}},
        "chapters": {TODAY: {"t1": {"2": 30}}},
        "hours": {TODAY: {"box1": {"10": 30}}},
        "placements": {},
        "active": {},
    }

    again = Analytics(Store(hass, 1, key), clock.now)
    await again.async_load()
    assert again.total() == 30


def test_chapters_and_hours(analytics: Analytics, clock: Clock) -> None:
    """Chapters are counted on their own; a span across the hour lands in both hours."""
    clock.advance(50 * 60)  # 10:50
    analytics.observe("box1", "t1", True, 0)
    clock.advance(20 * 60)  # 11:10, chapter 1 begins
    analytics.observe("box1", "t1", True, 1)
    clock.advance(5 * 60)
    analytics.observe("box1", "t2", True, None)
    clock.advance(60)
    analytics.observe("box1", None, False)
    assert analytics.per_chapter() == {("t1", 0): 1200, ("t1", 1): 300}
    grid = analytics.per_weekday_hour()
    weekday = START.weekday()
    assert grid[weekday][10] == 600
    assert grid[weekday][11] == 600 + 300 + 60
    assert sum(map(sum, grid)) == 1560
    assert analytics.per_chapter(1) == analytics.per_chapter()
    clock.advance(3 * 86400)
    assert analytics.per_chapter(1) == {}
    assert sum(map(sum, analytics.per_weekday_hour(1))) == 0


def test_hours_per_box_and_the_window_before(analytics: Analytics, clock: Clock) -> None:
    """Hours are kept per box; the window before counts only once it was counted in full."""
    analytics.observe("box1", "t1", True)
    clock.advance(600)
    analytics.observe("box1", None, False)
    analytics.observe("box2", "t2", True)
    clock.advance(300)
    analytics.observe("box2", None, False)
    weekday = START.weekday()
    assert analytics.per_weekday_hour(7, "box1")[weekday][10] == 600
    assert analytics.per_weekday_hour(7, "box2")[weekday][10] == 300
    assert analytics.per_weekday_hour(7)[weekday][10] == 900
    assert analytics.hour_boxes(7) == {"box1", "box2"}
    assert analytics.hour_boxes() == {"box1", "box2"}
    # Counted for one day only: the 7 days before were not counted
    assert analytics.total_before(7) is None
    # 13 days later the 7 days before begin with the first counted day
    clock.advance(13 * 86400)
    assert analytics.total_before(7) == 900
    assert analytics.total_before(1) == 0
    assert analytics.hour_boxes(1) == set()


async def test_hours_of_another_shape_are_left_out(store: Mock, clock: Clock) -> None:
    """Hours stored without boxes are not read; the rest still is."""
    store.async_load = AsyncMock(
        return_value={
            "days": {TODAY: {"box1": {"t1": 60}}},
            "hours": {TODAY: {"10": 60}, YESTERDAY: "x"},
        }
    )
    counter = Analytics(store, clock.now)
    await counter.async_load()
    assert counter.per_tonie() == {"t1": 60}
    assert sum(map(sum, counter.per_weekday_hour())) == 0


async def test_placements(store: Mock, clock: Clock) -> None:
    """Every placing counts once per figure and day; the day filter counts back from today."""
    week_ago = (START.date() - timedelta(days=7)).isoformat()
    store.async_load = AsyncMock(
        return_value={
            "days": {},
            "placements": {
                week_ago: {"box1": {"t1": "4"}},
                YESTERDAY: "broken",
                TODAY: {"box1": {"t2": 1}, "box2": "x"},
            },
        }
    )
    counter = Analytics(store, clock.now)
    await counter.async_load()
    counter.placed("box1", "t2")
    counter.placed("box2", "t1")
    assert counter.placements_per_tonie(1) == {"t2": 2, "t1": 1}
    assert counter.placements_per_tonie() == {"t1": 5, "t2": 2}
    counter.save_soon()
    data_func, _ = store.async_delay_save.call_args.args
    assert data_func()["placements"][TODAY] == {"box1": {"t2": 2}, "box2": {"t1": 1}}


async def test_keep_days_can_change(store: Mock, clock: Clock) -> None:
    """A shorter time drops older days at once; 0 keeps every day."""
    far = (START.date() - timedelta(days=1000)).isoformat()
    year = (START.date() - timedelta(days=400)).isoformat()
    analytics = Analytics(store, clock.now, keep_days=0)
    store.async_load.return_value = {
        "days": {far: {"box1": {"t1": 10}}, year: {"box1": {"t1": 20}}}
    }
    await analytics.async_load()
    assert set(analytics.per_day()) == {far, year}
    analytics.set_keep_days(730)
    assert set(analytics.per_day()) == {year}
    store.async_delay_save.assert_called()
    analytics.set_keep_days(365)
    assert analytics.per_day() == {}
