"""Battery cycles of the Toniebox 2: counting, saving, the summary and the wiring in the integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus.battery import (
    JUMP_PERCENT,
    KEEP_CYCLES,
    MIN_SECONDS,
    MIN_USED_PERCENT,
    SAVE_DELAY,
    BatteryStats,
)
from custom_components.storybox_plus.const import DOMAIN

from .conftest import BOX_ID, HOUSEHOLD_ID, FakeCloud, PushChannels, classic_box

TZ = ZoneInfo("Europe/Berlin")
START = datetime(2026, 11, 4, 10, 0, tzinfo=TZ)
TODAY = "2026-11-04"
HOUR = 3600
EMPTY: dict[str, Any] = {"current": None, "cycles": [], "count": 0, "average_full_hours": None}


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
    return mock


@pytest.fixture
async def stats(store: Mock, clock: Clock) -> BatteryStats:
    """An empty counter."""
    counter = BatteryStats(store, clock.now)
    await counter.async_load()
    return counter


async def _loaded(store: Mock, clock: Clock, stored: Any) -> BatteryStats:
    store.async_load.return_value = stored
    counter = BatteryStats(store, clock.now)
    await counter.async_load()
    return counter


def test_discharge_until_charging_makes_a_cycle(stats: BatteryStats, clock: Clock) -> None:
    """Off the charger a cycle opens; charging closes it with its hours and the estimate."""
    stats.observe("box1", 100, False, True)
    assert stats.summary("box1") == {
        "current": {"hours": 0.0, "from": 100, "to": 100, "per_full": None},
        "cycles": [],
        "count": 0,
        "average_full_hours": None,
    }
    clock.advance(2 * HOUR)
    stats.observe("box1", 80, False, True)
    clock.advance(2 * HOUR)
    stats.observe("box1", 60, False, True)
    assert stats.summary("box1")["current"] == {
        "hours": 4.0,
        "from": 100,
        "to": 60,
        "per_full": 10.0,
    }
    stats.observe("box1", 60, True, True)
    assert stats.summary("box1") == {
        "current": None,
        "cycles": [{"day": TODAY, "hours": 4.0, "from": 100, "to": 60, "per_full": 10.0}],
        "count": 1,
        "average_full_hours": 10.0,
    }
    # While charging nothing is counted; the first report after it opens the next cycle
    clock.advance(HOUR)
    stats.observe("box1", 90, True, True)
    assert stats.summary("box1")["current"] is None
    stats.observe("box1", 100, False, True)
    assert stats.summary("box1")["current"] == {
        "hours": 0.0,
        "from": 100,
        "to": 100,
        "per_full": None,
    }
    assert stats.summary("box2") == EMPTY


def test_time_switched_off_does_not_count(stats: BatteryStats, clock: Clock) -> None:
    """Only the hours switched on count; a box that is off or shuts down keeps its cycle open."""
    stats.observe("box1", 100, False, True)
    clock.advance(HOUR)
    stats.observe("box1", 90, False, False)
    clock.advance(5 * HOUR)
    assert stats.summary("box1")["current"]["hours"] == 1.0
    stats.observe("box1", 90, False, True)
    clock.advance(HOUR)
    stats.observe("box1", 80, False, True)
    assert stats.summary("box1")["current"] == {
        "hours": 2.0,
        "from": 100,
        "to": 80,
        "per_full": 10.0,
    }
    # A box that shuts down reports only nulls: the clock stops until a level comes again
    stats.observe("box1", None, None, True)
    clock.advance(HOUR)
    assert stats.summary("box1")["current"]["hours"] == 2.0
    stats.observe("box1", None, None, True)
    clock.advance(HOUR)
    assert stats.summary("box1")["current"]["hours"] == 2.0
    stats.observe("box1", 80, False, True)
    clock.advance(HOUR / 2)
    stats.observe("box1", 70, False, True)
    stats.observe("box1", 70, True, True)
    assert stats.summary("box1")["cycles"] == [
        {"day": TODAY, "hours": 2.5, "from": 100, "to": 70, "per_full": 8.3}
    ]
    # Nulls without a cycle change nothing
    stats.observe("box2", None, None, True)
    assert stats.summary("box2") == EMPTY


def test_level_jump_closes_the_cycle(stats: BatteryStats, clock: Clock) -> None:
    """A level that jumps up means the box was charged, even without a charging report."""
    stats.observe("box1", 50, None, True)
    clock.advance(HOUR)
    stats.observe("box1", 40, None, True)
    # A small bump is noise and does not raise the lowest level either
    stats.observe("box1", 40 + JUMP_PERCENT - 1, None, True)
    assert stats.summary("box1")["current"] == {
        "hours": 1.0,
        "from": 50,
        "to": 40,
        "per_full": 10.0,
    }
    stats.observe("box1", 40 + JUMP_PERCENT, None, True)
    assert stats.summary("box1") == {
        "current": None,
        "cycles": [{"day": TODAY, "hours": 1.0, "from": 50, "to": 40, "per_full": 10.0}],
        "count": 1,
        "average_full_hours": 10.0,
    }


def test_level_of_the_charging_report_ends_the_cycle(stats: BatteryStats, clock: Clock) -> None:
    """The level the charger found is the end of the discharge; a higher one is already charged."""
    stats.observe("box1", 100, False, True)
    clock.advance(2 * HOUR)
    stats.observe("box1", 80, False, True)
    clock.advance(HOUR)
    stats.observe("box1", 70, True, True)
    assert stats.summary("box1")["cycles"] == [
        {"day": TODAY, "hours": 3.0, "from": 100, "to": 70, "per_full": 10.0}
    ]
    stats.observe("box1", 100, False, True)
    clock.advance(HOUR)
    stats.observe("box1", 60, False, True)
    stats.observe("box1", 65, True, True)
    assert stats.summary("box1")["cycles"][0] == {
        "day": TODAY,
        "hours": 1.0,
        "from": 100,
        "to": 60,
        "per_full": 2.5,
    }


def test_short_or_shallow_cycles_are_dropped(stats: BatteryStats, clock: Clock) -> None:
    """Cycles shorter than ten minutes or using less than five percent tell nothing."""
    stats.observe("box1", 100, False, True)
    clock.advance(MIN_SECONDS - 1)
    stats.observe("box1", 50, False, True)
    stats.observe("box1", 50, True, True)
    assert stats.summary("box1") == EMPTY
    stats.observe("box1", 100, False, True)
    clock.advance(10 * HOUR)
    stats.observe("box1", 100 - MIN_USED_PERCENT + 1, False, True)
    stats.observe("box1", 100 - MIN_USED_PERCENT + 1, True, True)
    assert stats.summary("box1") == EMPTY
    # The limits themselves are enough
    stats.observe("box1", 100, False, True)
    clock.advance(MIN_SECONDS)
    stats.observe("box1", 100 - MIN_USED_PERCENT, False, True)
    stats.observe("box1", 100 - MIN_USED_PERCENT, True, True)
    assert stats.summary("box1")["cycles"] == [
        {"day": TODAY, "hours": 0.17, "from": 100, "to": 95, "per_full": 3.4}
    ]


async def test_only_the_last_cycles_are_kept(
    stats: BatteryStats, clock: Clock, store: Mock
) -> None:
    """Older cycles make room; the summary shows the newest twenty and counts what is kept."""
    for day in range(KEEP_CYCLES + 5):
        clock.value = START + timedelta(days=day)
        stats.observe("box1", 100, False, True)
        clock.advance(HOUR)
        stats.observe("box1", 90, False, True)
        stats.observe("box1", 90, True, True)

    def day_of(offset: int) -> str:
        return (START + timedelta(days=offset)).date().isoformat()

    summary = stats.summary("box1")
    assert summary["count"] == KEEP_CYCLES
    assert len(summary["cycles"]) == 20
    assert summary["cycles"][0]["day"] == day_of(KEEP_CYCLES + 4)
    assert summary["cycles"][-1]["day"] == day_of(KEEP_CYCLES - 15)
    assert summary["average_full_hours"] == 10.0
    await stats.async_save()
    saved = store.async_save.await_args.args[0]["cycles"]["box1"]
    assert [c["day"] for c in saved] == [day_of(d) for d in range(5, KEEP_CYCLES + 5)]


async def test_summary(store: Mock, clock: Clock) -> None:
    """Cycles come newest first, twenty at most; the estimate averages the latest ten."""
    stored = [
        {"day": f"2026-10-{d:02d}", "hours": float(d), "from": 100, "to": 50, "per_full": 2.0 * d}
        for d in range(1, 26)
    ]
    stored[-1]["per_full"] = "unknown"
    stats = await _loaded(store, clock, {"cycles": {"box1": stored}})
    summary = stats.summary("box1")
    assert summary["count"] == 25
    assert [c["day"] for c in summary["cycles"]] == [f"2026-10-{d:02d}" for d in range(25, 5, -1)]
    # The newest ten minus the one without a usable estimate: 48 down to 32
    assert summary["average_full_hours"] == 40.0
    assert summary["current"] is None
    # A running cycle shows its hours; an estimate only once enough was used
    stats.observe("box1", 100, False, True)
    clock.advance(HOUR)
    stats.observe("box1", 100 - MIN_USED_PERCENT + 1, False, True)
    assert stats.summary("box1")["current"] == {
        "hours": 1.0,
        "from": 100,
        "to": 96,
        "per_full": None,
    }
    stats.observe("box1", 100 - MIN_USED_PERCENT, False, True)
    assert stats.summary("box1")["current"]["per_full"] == 20.0


def test_save_soon_only_when_something_changed(
    stats: BatteryStats, clock: Clock, store: Mock
) -> None:
    """Only a change schedules a write, and only one until the next change."""
    stats.save_soon()
    store.async_delay_save.assert_not_called()
    # Charging without a cycle is nothing to note
    stats.observe("box1", 80, True, True)
    stats.save_soon()
    store.async_delay_save.assert_not_called()
    stats.observe("box1", 80, False, True)
    stats.save_soon()
    stats.save_soon()
    store.async_delay_save.assert_called_once()
    data_func, delay = store.async_delay_save.call_args.args
    assert delay == SAVE_DELAY
    assert data_func() == {"cycles": {}, "open": {"box1": {"from": 80, "to": 80, "seconds": 0}}}
    # The same level while still on is nothing new
    clock.advance(10)
    stats.observe("box1", 80, False, True)
    stats.save_soon()
    assert store.async_delay_save.call_count == 1
    stats.tick()
    stats.save_soon()
    assert store.async_delay_save.call_count == 2
    assert data_func() == {"cycles": {}, "open": {"box1": {"from": 80, "to": 80, "seconds": 10}}}
    stats.observe("box1", 70, False, False)
    stats.save_soon()
    assert store.async_delay_save.call_count == 3


async def test_tick_and_save_round_trip(stats: BatteryStats, clock: Clock, store: Mock) -> None:
    """A tick books the time switched on; saving and loading keep the open cycle and the cycles."""
    stats.observe("box1", 100, False, True)
    stats.observe("box2", 60, False, True)
    clock.advance(HOUR)
    stats.observe("box2", 50, False, True)
    stats.observe("box2", 50, True, True)
    clock.advance(HOUR)
    stats.tick()
    assert stats.summary("box1")["current"]["hours"] == 2.0
    clock.advance(HOUR)
    await stats.async_save()
    store.async_save.assert_awaited_once_with(
        {
            "cycles": {
                "box2": [{"day": TODAY, "hours": 1.0, "from": 60, "to": 50, "per_full": 10.0}]
            },
            "open": {"box1": {"from": 100, "to": 100, "seconds": 3 * HOUR}},
        }
    )
    stats.save_soon()
    store.async_delay_save.assert_not_called()
    # The clock keeps running after the save
    clock.advance(HOUR)
    assert stats.summary("box1")["current"]["hours"] == 4.0

    # The next run reads it back; the open cycle continues once the box reports again
    again = await _loaded(store, clock, store.async_save.await_args.args[0])
    assert again.summary("box2")["count"] == 1
    assert again.summary("box1")["current"] == {
        "hours": 3.0,
        "from": 100,
        "to": 100,
        "per_full": None,
    }
    again.observe("box1", 80, False, True)
    clock.advance(HOUR)
    again.observe("box1", 80, True, True)
    assert again.summary("box1")["cycles"] == [
        {"day": TODAY, "hours": 4.0, "from": 100, "to": 80, "per_full": 20.0}
    ]


@pytest.mark.parametrize(
    "stored",
    [
        None,
        {},
        {"cycles": "junk", "open": "junk"},
        {"cycles": {"box1": "junk"}, "open": {"box1": {"from": "100", "to": 50}}},
        {"open": {"box1": {"from": 100}, "box2": "junk", "box3": {"to": 90}}},
    ],
)
async def test_load_without_usable_data(store: Mock, clock: Clock, stored: Any) -> None:
    """Missing or broken stored data means starting from nothing."""
    stats = await _loaded(store, clock, stored)
    assert stats.summary("box1") == EMPTY
    assert stats.summary("box2") == EMPTY
    stats.save_soon()
    store.async_delay_save.assert_not_called()


async def test_load_skips_junk_and_keeps_the_latest(store: Mock, clock: Clock) -> None:
    """Broken items are skipped, surplus cycles dropped, and open cycles need both levels."""
    cycles = [{"day": f"d{i}", "per_full": 1.0} for i in range(KEEP_CYCLES + 3)]
    stats = await _loaded(
        store,
        clock,
        {
            "cycles": {"box1": [*cycles, "junk", 5], "box2": {"not": "a list"}},
            "open": {
                "box1": {"from": 100, "to": 90, "seconds": None},
                "box2": {"from": 100, "to": 70, "seconds": "junk"},
                "box3": {"from": 100, "to": 60, "seconds": 1800},
            },
        },
    )
    summary = stats.summary("box1")
    assert summary["count"] == KEEP_CYCLES
    assert summary["cycles"][0]["day"] == f"d{KEEP_CYCLES + 2}"
    assert summary["average_full_hours"] == 1.0
    assert summary["current"] == {"hours": 0.0, "from": 100, "to": 90, "per_full": 0.0}
    assert stats.summary("box2")["current"] == {
        "hours": 0.0,
        "from": 100,
        "to": 70,
        "per_full": 0.0,
    }
    assert stats.summary("box3")["current"] == {
        "hours": 0.5,
        "from": 100,
        "to": 60,
        "per_full": 1.2,
    }


async def test_with_the_real_store(
    hass: HomeAssistant, hass_storage: dict[str, Any], clock: Clock
) -> None:
    """The delayed write lands in the store after the delay and is read back by the next run."""
    key = "storybox_plus.test.battery"
    store: Store[Any] = Store(hass, 1, key)
    stats = BatteryStats(store, clock.now)
    await stats.async_load()
    stats.observe("box1", 100, False, True)
    clock.advance(HOUR)
    stats.tick()
    stats.save_soon()
    assert key not in hass_storage
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=SAVE_DELAY + 1))
    await hass.async_block_till_done()
    assert hass_storage[key]["data"] == {
        "cycles": {},
        "open": {"box1": {"from": 100, "to": 100, "seconds": HOUR}},
    }
    again = BatteryStats(Store(hass, 1, key), clock.now)
    await again.async_load()
    assert again.summary("box1")["current"]["hours"] == 1.0


# -- in the integration --

CLASSIC_MAC = "0A1B2C3D4E5F"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _written(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Let the delayed write of the store happen."""
    freezer.tick(timedelta(seconds=SAVE_DELAY + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_push_messages_feed_the_cycles(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Battery and online messages of a Toniebox 2 count; a classic box has no battery."""
    freezer.move_to("2026-11-04T10:00:00+00:00")
    cloud.main.boxes[HOUSEHOLD_ID].append({**classic_box("box3", "Alt"), "macAddress": CLASSIC_MAC})
    await _setup(hass, config_entry)
    stats = config_entry.runtime_data.battery_stats
    channel = push.last

    channel.battery(100, "discharging")
    assert stats.summary(BOX_ID)["current"] == {
        "hours": 0.0,
        "from": 100,
        "to": 100,
        "per_full": None,
    }
    freezer.tick(timedelta(hours=1))
    channel.online(False)
    freezer.tick(timedelta(hours=5))
    channel.online(True)
    freezer.tick(timedelta(hours=1))
    channel.battery(80, "discharging")
    assert stats.summary(BOX_ID)["current"] == {
        "hours": 2.0,
        "from": 100,
        "to": 80,
        "per_full": 10.0,
    }
    channel.battery(None, None)
    freezer.tick(timedelta(hours=1))
    channel.battery(80, "charging")
    assert stats.summary(BOX_ID) == {
        "current": None,
        "cycles": [{"day": TODAY, "hours": 2.0, "from": 100, "to": 80, "per_full": 10.0}],
        "count": 1,
        "average_full_hours": 10.0,
    }
    # The classic box never counts, whatever its messages say
    channel.battery(50, "discharging", mac=CLASSIC_MAC)
    channel.online(False, mac=CLASSIC_MAC)
    assert stats.summary("box3") == EMPTY


async def test_battery_store_is_written_saved_and_removed(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """The store follows the polls and the unload, survives a restart and goes with the account."""
    freezer.move_to("2026-11-04T10:00:00+00:00")
    key = f"{DOMAIN}.{config_entry.entry_id}.battery"
    analytics_key = f"{DOMAIN}.{config_entry.entry_id}.analytics"
    chapters_key = f"{DOMAIN}.{config_entry.entry_id}.chapters"
    hass_storage[chapters_key] = {
        "version": 1,
        "minor_version": 1,
        "key": chapters_key,
        "data": {"tonies": {}},
    }
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator

    push.last.battery(100, "discharging")
    assert key not in hass_storage
    await _written(hass, freezer)
    assert hass_storage[key]["data"] == {
        "cycles": {},
        "open": {BOX_ID: {"from": 100, "to": 100, "seconds": 0}},
    }
    # A poll books the hour switched on so far
    freezer.tick(timedelta(hours=1) - timedelta(seconds=SAVE_DELAY + 1))
    await coordinator.async_refresh()
    await _written(hass, freezer)
    assert hass_storage[key]["data"]["open"] == {BOX_ID: {"from": 100, "to": 100, "seconds": HOUR}}

    # Unloading writes the running cycle at once
    freezer.tick(timedelta(minutes=30) - timedelta(seconds=SAVE_DELAY + 1))
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass_storage[key]["data"]["open"] == {
        BOX_ID: {"from": 100, "to": 100, "seconds": HOUR + HOUR // 2}
    }
    assert analytics_key in hass_storage

    # The next run continues the cycle
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    stats = config_entry.runtime_data.battery_stats
    assert stats.summary(BOX_ID)["current"] == {
        "hours": 1.5,
        "from": 100,
        "to": 100,
        "per_full": None,
    }
    push.last.battery(70, "discharging")
    push.last.battery(70, "charging")
    assert stats.summary(BOX_ID)["cycles"] == [
        {"day": TODAY, "hours": 1.5, "from": 100, "to": 70, "per_full": 5.0}
    ]

    # Removing the account forgets all three stores
    await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage
    assert analytics_key not in hass_storage
    assert chapters_key not in hass_storage


async def test_lost_push_channel_stops_the_clock(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Without the push channel nothing tells the box is on: those hours do not count."""
    freezer.move_to("2026-11-04T10:00:00+00:00")
    await _setup(hass, config_entry)
    stats = config_entry.runtime_data.battery_stats
    channel = push.last
    channel.connect(True)
    channel.battery(100, "discharging")
    freezer.tick(timedelta(hours=1))
    channel.connect(False)
    freezer.tick(timedelta(hours=6))
    stats.tick()
    assert stats.summary(BOX_ID)["current"]["hours"] == 1.0
    # Back: the retained messages switch the clock on again
    channel.connect(True)
    channel.battery(90, "discharging")
    freezer.tick(timedelta(hours=1))
    assert stats.summary(BOX_ID)["current"]["hours"] == 2.0
