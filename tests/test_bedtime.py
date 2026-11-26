"""Bedtime schedules: the next wake-up, the alarm armed every evening, the page's commands."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.storybox_plus import bedtime
from custom_components.storybox_plus.bedtime import armed_for, decide, due, next_alarm
from custom_components.storybox_plus.cloud import BedtimeSchedule, SleepTimer
from custom_components.storybox_plus.cloud.models import (
    parse_bedtime_schedule,
    parse_box,
    parse_sleep_timer,
)
from custom_components.storybox_plus.const import DOMAIN

from .conftest import BOX_ID, CLASSIC_BOX_ID, MAC, FakeCloud, PushChannels, entity_id

BERLIN = ZoneInfo("Europe/Berlin")
# A Monday evening in the box's time zone
MONDAY_EVENING = datetime(2026, 11, 9, 18, 0, tzinfo=BERLIN)
TUESDAY_WAKEUP = datetime(2026, 11, 10, 6, 30, tzinfo=BERLIN)
SCHOOL_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")


def schedule(
    schedule_id: str = "s1",
    wakeup: str = "06:30",
    days: tuple[str, ...] = SCHOOL_DAYS,
    enabled: bool = True,
    alarm: bool = True,
) -> BedtimeSchedule:
    """Return a parsed schedule."""
    return BedtimeSchedule(
        id=schedule_id,
        name="School",
        sleep_time="19:00",
        wakeup_time=wakeup,
        days=days,
        enabled=enabled,
        alarm_enabled=alarm,
        alarm_volume=40,
        alarm_morning_light=False,
    )


def raw_schedule(**kwargs: Any) -> dict[str, Any]:
    """Return a schedule as the cloud answers it."""
    data = {
        "id": "s1",
        "name": "School",
        "sleepTime": "19:00",
        "wakeupTime": "06:30",
        "days": list(SCHOOL_DAYS),
        "enabled": True,
        "alarmEnabled": True,
        "alarmTone": "alarmLoop1.opus",
        "alarmVolume": 40,
        "alarmMorningLight": False,
    }
    data.update(kwargs)
    return data


# ---------------------------------------------------------------- parsing


def test_parse_schedule() -> None:
    """The cloud's fields become a schedule; times lose their seconds, days keep the week's order."""
    parsed = parse_bedtime_schedule(
        raw_schedule(wakeupTime="06:30:00", days=["Friday", "monday", "holiday"])
    )
    assert parsed is not None
    assert parsed.wakeup_time == "06:30"
    assert parsed.days == ("monday", "friday")
    assert parsed.alarm.volume == 40
    assert parsed.alarm.morning_light is False
    assert parsed.alarm.tone == "alarmLoop1.opus"
    assert parse_bedtime_schedule({"name": "no id"}) is None
    sparse = parse_bedtime_schedule({"id": "x", "sleepTime": "25:00", "wakeupTime": None})
    assert sparse is not None
    assert (sparse.sleep_time, sparse.wakeup_time, sparse.enabled) == (None, None, False)
    # The alarm of a schedule that names nothing rings as the app's does
    assert sparse.alarm.volume == 100
    assert sparse.alarm.morning_light is True


def test_parse_box_and_timer() -> None:
    """A Toniebox 2 with the alarm feature rings alarms; the timer tells whether one is armed."""
    box = parse_box(
        {"id": "b", "features": ["tngSettings", "sleepTimerAlarm"], "timezone": "Europe/Berlin"},
        "hh",
    )
    assert box is not None
    assert box.alarm_capable
    assert box.timezone == "Europe/Berlin"
    classic = parse_box({"id": "c", "features": ["sleepTimerAlarm"]}, "hh")
    assert classic is not None
    assert not classic.alarm_capable
    armed = parse_sleep_timer(
        {"stl": {"state": "on", "duration": 60, "until": 1_800_000_000, "alarm": {"tone": "x"}}}
    )
    assert armed.running
    assert armed.alarm
    assert not parse_sleep_timer({"stl": {"state": "on", "alarm": None}}).alarm


# ---------------------------------------------------------------- the next wake-up


@pytest.mark.parametrize(
    ("schedules", "now", "expected"),
    [
        # The next school day's morning
        ((schedule(),), MONDAY_EVENING, TUESDAY_WAKEUP),
        # Friday evening: Monday morning
        (
            (schedule(),),
            datetime(2026, 11, 13, 20, 0, tzinfo=BERLIN),
            datetime(2026, 11, 16, 6, 30, tzinfo=BERLIN),
        ),
        # Before the wake-up on a school day: the same morning
        ((schedule(),), datetime(2026, 11, 10, 5, 0, tzinfo=BERLIN), TUESDAY_WAKEUP),
        # The earliest of several schedules
        (
            (
                schedule(),
                schedule("s2", "07:30", ("tuesday",)),
                schedule("s3", "06:00", ("tuesday",)),
            ),
            MONDAY_EVENING,
            datetime(2026, 11, 10, 6, 0, tzinfo=BERLIN),
        ),
        # Switched off, without alarm, without days: none
        ((schedule(enabled=False),), MONDAY_EVENING, None),
        ((schedule(alarm=False),), MONDAY_EVENING, None),
        ((schedule(days=()),), MONDAY_EVENING, None),
        ((), MONDAY_EVENING, None),
    ],
)
def test_next_alarm(
    schedules: tuple[BedtimeSchedule, ...], now: datetime, expected: datetime | None
) -> None:
    """The next wake-up over the enabled schedules with an alarm."""
    found = next_alarm(schedules, now)
    assert (found.at if found else None) == expected


def test_due_only_within_the_timers_reach() -> None:
    """An alarm is due once the box's timer reaches it, about 18 hours ahead."""
    assert due((schedule(),), MONDAY_EVENING) is not None
    assert due((schedule(),), datetime(2026, 11, 9, 11, 0, tzinfo=BERLIN)) is None
    assert due(None, MONDAY_EVENING) is None


def test_decide() -> None:
    """Arm what is due unless armed; clear only an alarm of ours that nothing wants."""
    alarm = next_alarm((schedule(),), MONDAY_EVENING)
    assert alarm is not None
    armed = SleepTimer("on", until=TUESDAY_WAKEUP + timedelta(seconds=40), alarm=True)
    plain = SleepTimer("on", until=TUESDAY_WAKEUP, alarm=False)
    other = SleepTimer("on", until=TUESDAY_WAKEUP + timedelta(hours=1), alarm=True)
    assert armed_for(armed, TUESDAY_WAKEUP)
    assert decide(alarm, armed, None) is None
    assert decide(alarm, plain, None) == ("arm", alarm)
    assert decide(alarm, other, None) == ("arm", alarm)
    assert decide(alarm, None, None) == ("arm", alarm)
    assert decide(None, armed, TUESDAY_WAKEUP) == ("clear", None)
    # An alarm someone else armed stays
    assert decide(None, other, TUESDAY_WAKEUP) is None
    assert decide(None, armed, None) is None


# ---------------------------------------------------------------- arming


def _alarm_commands(push: PushChannels) -> list[tuple[str, dict[str, Any]]]:
    return [(c, p) for _mac, c, p in push.last.commands if c in ("stl", "alarm-preview")]


async def _setup(
    hass: HomeAssistant,
    cloud: FakeCloud,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    schedules: list[dict[str, Any]] | None = None,
    ws: WebSocketGenerator | None = None,
) -> Any:
    # The page's connection signs in before the clock is moved: its token is issued now
    client = await ws(hass) if ws is not None else None
    freezer.move_to(MONDAY_EVENING)
    cloud.main.schedules[BOX_ID] = schedules if schedules is not None else [raw_schedule()]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return client


async def _later(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_alarm_armed_once_the_channel_is_up(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The due alarm goes to the box as the app sends it, a moment after the channel came up."""
    await _setup(hass, cloud, config_entry, freezer)
    push.last.connect()
    await hass.async_block_till_done()
    assert _alarm_commands(push) == []
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    seconds = int((TUESDAY_WAKEUP - datetime.now(UTC)).total_seconds())
    assert _alarm_commands(push) == [
        ("alarm-preview", {"tone": None}),
        (
            "stl",
            {
                "state": "on",
                "duration": seconds,
                "oneTimeAlarm": True,
                "alarm": {"morningLight": False, "tone": "alarmLoop1.opus", "volume": 40},
            },
        ),
    ]
    # The box confirms: nothing more is sent, not even after the retry time
    push.last.sleep_timer("on", until=TUESDAY_WAKEUP, alarm=True)
    await _later(hass, freezer, bedtime.RETRY.total_seconds() + 10)
    assert len(_alarm_commands(push)) == 2


async def test_alarm_tried_a_few_times_then_left(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A box that never confirms is asked a few times, then again when it comes online anew."""
    await _setup(hass, cloud, config_entry, freezer)
    push.last.connect()
    for _ in range(bedtime.TRIES + 2):
        await _later(hass, freezer, bedtime.RETRY.total_seconds() + 10)
    stl = [p for c, p in _alarm_commands(push) if c == "stl"]
    assert len(stl) == bedtime.TRIES
    assert caplog.text.count("did not confirm its alarm") == 1
    push.last.online(False)
    push.last.online(True)
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    assert len([c for c, _ in _alarm_commands(push) if c == "stl"]) == bedtime.TRIES + 1


async def test_alarm_waits_for_the_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """An offline box gets nothing; once online, it gets the alarm after a moment."""
    await _setup(hass, cloud, config_entry, freezer)
    push.last.connect()
    push.last.online(False)
    await _later(hass, freezer, 60)
    assert _alarm_commands(push) == []
    push.last.online(True)
    await _later(hass, freezer, 5)
    assert _alarm_commands(push) == []
    await _later(hass, freezer, bedtime.SETTLE.total_seconds())
    assert [c for c, _ in _alarm_commands(push)] == ["alarm-preview", "stl"]


async def test_alarm_not_due_yet_and_classic_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Saturday has no school-day alarm in reach; nothing is sent."""
    freezer.move_to(datetime(2026, 11, 14, 10, 0, tzinfo=BERLIN))
    cloud.main.schedules[BOX_ID] = [raw_schedule()]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    push.last.connect()
    await _later(hass, freezer, 60)
    assert _alarm_commands(push) == []
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.due_alarm(CLASSIC_BOX_ID) is None
    assert coordinator.due_alarm("nobox") is None


async def test_switched_off_schedule_clears_our_alarm(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The alarm the integration armed goes when its schedule is switched off on the page."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)
    push.last.connect()
    await _later(hass, freezer, bedtime.SETTLE.total_seconds() + 1)
    push.last.sleep_timer("on", until=TUESDAY_WAKEUP, alarm=True)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/bedtime/save", "box_id": BOX_ID, "schedule_id": "s1", "enabled": False}
    )
    result = await client.receive_json()
    assert result["success"], result
    await hass.async_block_till_done()
    assert cloud.schedule_changes == [("PATCH", BOX_ID, "s1", {"enabled": False})]
    assert result["result"]["bedtime"]["next_alarm"] is None
    assert result["result"]["bedtime"]["schedules"][0]["enabled"] is False
    assert _alarm_commands(push)[-1] == ("stl", {"state": "off"})


async def test_schedules_kept_when_a_read_fails(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A failed read of the schedules keeps the last ones and costs the poll nothing."""
    await _setup(hass, cloud, config_entry, freezer)
    coordinator = config_entry.runtime_data.coordinator
    cloud.main.schedules_status = 500
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.data.boxes[BOX_ID].schedules is not None
    assert len(coordinator.data.boxes[BOX_ID].schedules or ()) == 1


async def test_sleep_commands_refused_while_an_alarm_is_due(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The sleep timer and switching off would cancel the alarm; they are refused with the time."""
    await _setup(hass, cloud, config_entry, freezer)
    push.last.connect()
    player = entity_id(hass, "media_player", BOX_ID)
    for domain, service, data in (
        (DOMAIN, "set_sleep_timer", {"minutes": 30}),
        (DOMAIN, "clear_sleep_timer", {}),
        ("media_player", "turn_off", {}),
    ):
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                domain, service, {"entity_id": player, **data}, blocking=True
            )
        assert err.value.translation_key == "alarm_due"
        assert err.value.translation_placeholders == {"time": "06:30"}
    assert not [c for _m, c, _p in push.last.commands if c in ("sleep",)]


async def test_sleep_timer_allowed_without_alarm(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Without a due alarm the sleep timer works as before."""
    await _setup(hass, cloud, config_entry, freezer, [raw_schedule(alarmEnabled=False)])
    push.last.connect()
    await hass.services.async_call(
        DOMAIN,
        "set_sleep_timer",
        {"entity_id": entity_id(hass, "media_player", BOX_ID), "minutes": 30},
        blocking=True,
    )
    assert push.last.commands[-1] == (MAC, "stl", {"state": "on", "duration": 1800})


# ---------------------------------------------------------------- the page


async def test_overview_tells_the_next_alarm(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The overview names the schedules, the next alarm and whether the box has it."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)

    async def bedtime_of_box() -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
        result = await client.receive_json()
        return next(b for b in result["result"]["boxes"] if b["id"] == BOX_ID)["bedtime"]

    seen = await bedtime_of_box()
    assert seen["schedules"] == [
        {
            "id": "s1",
            "name": "School",
            "sleep_time": "19:00",
            "wakeup_time": "06:30",
            "days": list(SCHOOL_DAYS),
            "enabled": True,
            "alarm_enabled": True,
            "alarm_volume": 40,
            "alarm_morning_light": False,
        }
    ]
    assert seen["next_alarm"] == {
        "at": TUESDAY_WAKEUP.isoformat(),
        "schedule_id": "s1",
        "armed": False,
        "due": True,
    }
    push.last.connect()
    push.last.sleep_timer("on", until=TUESDAY_WAKEUP, alarm=True)
    assert (await bedtime_of_box())["next_alarm"]["armed"] is True


async def test_next_alarm_sensor(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The sensor names the next alarm and moves on to the one after it once it rang."""
    await _setup(hass, cloud, config_entry, freezer)
    sensor = entity_id(hass, "sensor", f"{BOX_ID}_next_alarm")
    assert hass.states.get(sensor).attributes["device_class"] == "timestamp"
    assert hass.states.get(sensor).state == TUESDAY_WAKEUP.astimezone(UTC).isoformat()
    # Monday evening the alarm is within the timer's reach
    assert hass.states.get(sensor).attributes["due"] is True
    # A Toniebox 1 rings no alarm
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, f"{config_entry.entry_id}_{CLASSIC_BOX_ID}_next_alarm"
        )
        is None
    )

    freezer.move_to(TUESDAY_WAKEUP + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    wednesday = TUESDAY_WAKEUP + timedelta(days=1)
    assert hass.states.get(sensor).state == wednesday.astimezone(UTC).isoformat()
    # A day ahead it is not due yet; it becomes so by the clock alone
    assert hass.states.get(sensor).attributes["due"] is False
    freezer.move_to(wednesday - bedtime.ARM_WINDOW + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).attributes["due"] is True


async def test_next_alarm_sensor_without_alarm(
    hass: HomeAssistant,
    cloud: FakeCloud,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Without a bedtime that rings there is no next alarm."""
    await _setup(hass, cloud, config_entry, freezer, schedules=[raw_schedule(enabled=False)])
    sensor = entity_id(hass, "sensor", f"{BOX_ID}_next_alarm")
    assert hass.states.get(sensor).state == STATE_UNKNOWN


async def test_save_new_schedule_and_delete(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A new schedule goes to the cloud with the cloud's names; deleting removes it."""
    client = await _setup(hass, cloud, config_entry, freezer, [], ws=hass_ws_client)
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/bedtime/save",
            "box_id": BOX_ID,
            "name": "Weekend",
            "sleep_time": "20:00",
            "wakeup_time": "08:00",
            "days": ["sunday", "saturday", "sunday"],
            "alarm_enabled": True,
            "alarm_volume": 30,
            "alarm_morning_light": True,
        }
    )
    result = await client.receive_json()
    assert result["success"], result
    assert cloud.schedule_changes == [
        (
            "POST",
            BOX_ID,
            None,
            {
                "name": "Weekend",
                "sleepTime": "20:00",
                "wakeupTime": "08:00",
                "days": ["saturday", "sunday"],
                "alarmEnabled": True,
                "alarmVolume": 30,
                "alarmMorningLight": True,
                "enabled": True,
            },
        )
    ]
    (created,) = result["result"]["bedtime"]["schedules"]
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/bedtime/delete", "box_id": BOX_ID, "schedule_id": created["id"]}
    )
    result = await client.receive_json()
    assert result["success"], result
    assert result["result"]["bedtime"]["schedules"] == []
    assert cloud.schedule_changes[-1] == ("DELETE", BOX_ID, created["id"], None)


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ({"type": f"{DOMAIN}/bedtime/save", "box_id": "nobox", "name": "x"}, "unknown_box"),
        (
            {"type": f"{DOMAIN}/bedtime/delete", "box_id": "nobox", "schedule_id": "s1"},
            "unknown_box",
        ),
        (
            {
                "type": f"{DOMAIN}/bedtime/save",
                "box_id": CLASSIC_BOX_ID,
                "schedule_id": "s1",
                "enabled": True,
            },
            "no_alarm",
        ),
        (
            {
                "type": f"{DOMAIN}/bedtime/save",
                "box_id": BOX_ID,
                "schedule_id": "nope",
                "enabled": True,
            },
            "unknown_schedule",
        ),
        (
            {"type": f"{DOMAIN}/bedtime/delete", "box_id": BOX_ID, "schedule_id": "nope"},
            "unknown_schedule",
        ),
        (
            {"type": f"{DOMAIN}/bedtime/save", "box_id": BOX_ID, "name": "no times"},
            "invalid_format",
        ),
        (
            {
                "type": f"{DOMAIN}/bedtime/save",
                "box_id": BOX_ID,
                "schedule_id": "s1",
                "wakeup_time": "6:30",
            },
            "invalid_format",
        ),
        (
            {
                "type": f"{DOMAIN}/bedtime/save",
                "box_id": BOX_ID,
                "schedule_id": "s1",
                "days": ["someday"],
            },
            "invalid_format",
        ),
    ],
)
async def test_schedule_refusals(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Unknown boxes and schedules, boxes without alarms and bad fields are refused."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)
    await client.send_json_auto_id(message)
    result = await client.receive_json()
    assert not result["success"]
    assert result["error"]["code"] == code
    assert cloud.schedule_changes == []


async def test_schedule_cloud_error(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A change the cloud refuses comes back as cloud_error."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)
    cloud.main.rest_status = 500
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/bedtime/save", "box_id": BOX_ID, "schedule_id": "s1", "enabled": False}
    )
    result = await client.receive_json()
    assert result["error"]["code"] == "cloud_error"


async def test_schedule_commands_need_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user: Any,
) -> None:
    """Somebody who is no administrator changes no schedule."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)
    hass_admin_user.groups = []
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/bedtime/delete", "box_id": BOX_ID, "schedule_id": "s1"}
    )
    result = await client.receive_json()
    assert result["error"]["code"] == "unauthorized"
    assert cloud.schedule_changes == []
