"""The wake-up light: one alarm at a time of its own, set by an action or on the page."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.storybox_plus import bedtime
from custom_components.storybox_plus.bedtime import OneTimeAlarm, due, next_alarm, next_at
from custom_components.storybox_plus.cloud import Alarm
from custom_components.storybox_plus.const import DOMAIN

from .conftest import BOX_ID, FakeCloud, PushChannels, entity_id
from .test_bedtime import (
    BERLIN,
    MONDAY_EVENING,
    TUESDAY_WAKEUP,
    _alarm_commands,
    _later,
    _setup,
    raw_schedule,
    schedule,
)

NINE_PM = datetime(2026, 11, 9, 21, 0, tzinfo=BERLIN)
LIGHT = Alarm("alarmLoop3.opus", 70, False)


def test_next_alarm_with_the_wake_up_light() -> None:
    """Of the schedules and the wake-up light, the earlier rings first; a past light counts not."""
    early = OneTimeAlarm(NINE_PM, LIGHT)
    found = next_alarm((schedule(),), MONDAY_EVENING, early)
    assert found is not None
    assert (found.at, found.alarm, found.schedule) == (NINE_PM, LIGHT, None)
    late = OneTimeAlarm(TUESDAY_WAKEUP + timedelta(hours=1), LIGHT)
    found = next_alarm((schedule(),), MONDAY_EVENING, late)
    assert found is not None
    assert found.schedule is not None
    assert found.at == TUESDAY_WAKEUP
    # Without schedules the light alone; once it has passed, nothing
    assert next_alarm(None, MONDAY_EVENING, early) is not None
    assert next_alarm(None, NINE_PM, early) is None
    # Due within the timer's reach only
    far = OneTimeAlarm(MONDAY_EVENING + timedelta(days=2), LIGHT)
    assert due(None, MONDAY_EVENING, far) is None
    assert due(None, MONDAY_EVENING, early) is not None


def test_next_at() -> None:
    """A time of day is the next one: today while it is to come, else tomorrow."""
    assert next_at(time(21, 0), MONDAY_EVENING) == NINE_PM
    assert next_at(time(6, 30), MONDAY_EVENING) == TUESDAY_WAKEUP
    assert next_at(time(18, 0), MONDAY_EVENING) == MONDAY_EVENING + timedelta(days=1)


async def _set(hass: HomeAssistant, **data: Any) -> None:
    await hass.services.async_call(
        DOMAIN,
        "set_wake_up_light",
        {"entity_id": entity_id(hass, "media_player", BOX_ID), **data},
        blocking=True,
    )


async def test_action_arms_it_and_it_is_forgotten_once_rung(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Set for 21:00, the box gets the alarm with the chosen tone; afterwards it is gone."""
    await _setup(hass, cloud, config_entry, freezer, schedules=[])
    push.last.connect()
    await _set(hass, time="21:00", tone="sound_hopper", volume=70, morning_light=False)
    sensor = entity_id(hass, "sensor", f"{BOX_ID}_next_alarm")
    state = hass.states.get(sensor)
    assert state.state == NINE_PM.astimezone(UTC).isoformat()
    assert state.attributes["wake_up_light"] is True
    assert state.attributes["due"] is True
    # A box that is online and settled gets it at once
    await hass.async_block_till_done()
    seconds = int((NINE_PM - datetime.now(UTC)).total_seconds())
    assert _alarm_commands(push) == [
        ("alarm-preview", {"tone": None}),
        (
            "stl",
            {
                "state": "on",
                "duration": seconds,
                "oneTimeAlarm": True,
                "alarm": {"morningLight": False, "tone": "alarmLoop3.opus", "volume": 70},
            },
        ),
    ]
    push.last.sleep_timer("on", until=NINE_PM, alarm=True)
    coordinator = config_entry.runtime_data.coordinator
    assert BOX_ID in coordinator.preferences.wake_up_light

    freezer.move_to(NINE_PM + timedelta(minutes=6))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert BOX_ID not in coordinator.preferences.wake_up_light
    assert hass.states.get(sensor).state == STATE_UNKNOWN
    # Nothing of ours to clear: it rang
    assert _alarm_commands(push)[-1][0] == "stl"
    assert _alarm_commands(push)[-1][1]["state"] == "on"


async def test_five_minutes_ahead_at_least(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The box drops an alarm closer than five minutes: none is sent that late, and it is missed."""
    await _setup(hass, cloud, config_entry, freezer, schedules=[])
    push.last.connect()
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    # Exactly five minutes ahead is taken, and a moment's delay does not shorten it
    at = datetime.now(BERLIN).replace(microsecond=0) + bedtime.LEAD
    await _set(hass, datetime=at.strftime("%Y-%m-%d %H:%M:%S"))
    freezer.tick(timedelta(seconds=2))
    await hass.async_block_till_done()
    assert [p["duration"] for c, p in _alarm_commands(push) if c == "stl"] == [300]

    # A box that comes online less than five minutes before misses it
    push.last.connect(False)
    await hass.async_block_till_done()
    sent = len(_alarm_commands(push))
    at = datetime.now(BERLIN).replace(microsecond=0) + timedelta(minutes=30)
    await _set(hass, datetime=at.strftime("%Y-%m-%d %H:%M:%S"))
    freezer.move_to(at - timedelta(minutes=4))
    push.last.connect()
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    await _later(hass, freezer, bedtime.RETRY.total_seconds() + 10)
    assert len(_alarm_commands(push)) == sent


async def test_the_earlier_alarm_is_armed_first(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A wake-up light after the bedtime's alarm waits; one before it goes first."""
    await _setup(hass, cloud, config_entry, freezer)
    push.last.connect()
    await _set(hass, datetime="2026-11-10 07:15:00")
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    stl = [p for c, p in _alarm_commands(push) if c == "stl"]
    # The school day's alarm at 06:30, with its own tone and volume
    assert stl[-1]["alarm"] == {"morningLight": False, "tone": "alarmLoop1.opus", "volume": 40}
    push.last.sleep_timer("on", until=TUESDAY_WAKEUP, alarm=True)

    await _set(hass, time="22:00", tone="good_morning_beat")
    await hass.async_block_till_done()
    stl = [p for c, p in _alarm_commands(push) if c == "stl"]
    assert stl[-1]["alarm"] == {"morningLight": True, "tone": "alarmLoop5.opus", "volume": 100}
    assert stl[-1]["duration"] == int(
        (datetime(2026, 11, 9, 22, 0, tzinfo=BERLIN) - datetime.now(UTC)).total_seconds()
    )


async def test_clearing_takes_it_off_the_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Cleared, the alarm the box carries for it goes too, even when the integration forgot arming it."""
    await _setup(hass, cloud, config_entry, freezer, schedules=[])
    push.last.connect()
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    await _set(hass, time="21:00")
    push.last.sleep_timer("on", until=NINE_PM, alarm=True)
    coordinator = config_entry.runtime_data.coordinator
    # As after a restart: the integration no longer knows it armed it
    coordinator._armed.clear()
    await _later(hass, freezer, bedtime.RETRY.total_seconds() + 10)
    await hass.services.async_call(
        DOMAIN,
        "clear_wake_up_light",
        {"entity_id": entity_id(hass, "media_player", BOX_ID)},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert _alarm_commands(push)[-1] == ("stl", {"state": "off"})
    assert coordinator.preferences.wake_up_light == {}


async def test_refusals(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A time less than five minutes ahead is refused; while the light is due, the sleep timer is."""
    await _setup(hass, cloud, config_entry, freezer, schedules=[])
    push.last.connect()
    for at in ("2026-11-09 17:00", "2026-11-09 18:04"):
        with pytest.raises(ServiceValidationError) as err:
            await _set(hass, datetime=f"{at}:00")
        assert err.value.translation_key == "alarm_too_soon"
        assert err.value.translation_placeholders == {"time": at}
    await _set(hass, time="21:00")
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "set_sleep_timer",
            {"entity_id": entity_id(hass, "media_player", BOX_ID), "minutes": 30},
            blocking=True,
        )
    assert err.value.translation_key == "alarm_due"
    assert err.value.translation_placeholders == {"time": "21:00"}


async def test_kept_across_a_restart(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The wake-up light lives in the store and survives a reload of the entry."""
    await _setup(hass, cloud, config_entry, freezer, schedules=[])
    await _set(hass, time="21:00", tone="birdsong", volume=55)
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    light = config_entry.runtime_data.coordinator.wake_up_light(BOX_ID)
    assert light == OneTimeAlarm(NINE_PM, Alarm("alarmLoop2.opus", 55, True))


async def test_page_sets_and_clears_it(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The page sets it in the box's own time and gets the box back with it."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client, schedules=[])
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/alarm/set",
            "box_id": BOX_ID,
            "at": "2026-11-09 21:15",
            "tone": "alarmLoop4.opus",
            "volume": 80,
            "morning_light": True,
        }
    )
    result = await client.receive_json()
    assert result["success"], result
    seen = result["result"]["bedtime"]
    assert seen["wake_up_light"] == {
        "at": "2026-11-09T21:15:00+01:00",
        "tone": "alarmLoop4.opus",
        "volume": 80,
        "morning_light": True,
    }
    assert seen["next_alarm"]["schedule_id"] is None
    assert seen["next_alarm"]["due"] is True

    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/alarm/set",
            "box_id": BOX_ID,
            "at": "2026-11-09 07:00",
            "tone": "alarmLoop1.opus",
            "volume": 80,
            "morning_light": True,
        }
    )
    result = await client.receive_json()
    assert result["error"]["code"] == "alarm_too_soon"

    await client.send_json_auto_id({"type": f"{DOMAIN}/alarm/clear", "box_id": BOX_ID})
    result = await client.receive_json()
    assert result["success"], result
    assert result["result"]["bedtime"]["wake_up_light"] is None
    assert result["result"]["bedtime"]["next_alarm"] is None

    await client.send_json_auto_id({"type": f"{DOMAIN}/alarm/clear", "box_id": "nobox"})
    result = await client.receive_json()
    assert result["error"]["code"] == "unknown_box"


async def test_page_commands_need_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user: Any,
) -> None:
    """Somebody who is no administrator sets no wake-up light on the page."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client, schedules=[])
    hass_admin_user.groups = []
    await client.send_json_auto_id({"type": f"{DOMAIN}/alarm/clear", "box_id": BOX_ID})
    result = await client.receive_json()
    assert result["error"]["code"] == "unauthorized"


async def test_schedule_takes_a_tone(
    hass: HomeAssistant,
    cloud: FakeCloud,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A bedtime's alarm tone is one of the app's; the cloud gets it as alarmTone."""
    client = await _setup(
        hass, cloud, config_entry, freezer, ws=hass_ws_client, schedules=[raw_schedule()]
    )
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/bedtime/save",
            "box_id": BOX_ID,
            "schedule_id": "s1",
            "alarm_tone": "alarmLoop2.opus",
        }
    )
    result = await client.receive_json()
    assert result["success"], result
    assert cloud.schedule_changes == [("PATCH", BOX_ID, "s1", {"alarmTone": "alarmLoop2.opus"})]
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/bedtime/save",
            "box_id": BOX_ID,
            "schedule_id": "s1",
            "alarm_tone": "x.opus",
        }
    )
    result = await client.receive_json()
    assert result["error"]["code"] == "invalid_format"
