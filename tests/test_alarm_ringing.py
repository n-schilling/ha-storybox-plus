"""What the box says about its alarm: how it is set, and when it rings and stops."""

from __future__ import annotations

from typing import Any

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.cloud import Alarm
from custom_components.storybox_plus.cloud.models import parse_sleep_timer
from custom_components.storybox_plus.const import DOMAIN

from .conftest import BOX_ID, FakeCloud, PushChannels, entity_id
from .test_bedtime import TUESDAY_WAKEUP, _setup


def test_the_timer_carries_the_alarm_settings() -> None:
    """The box reports the alarm with the timer; what it leaves out is the app's default."""
    timer = parse_sleep_timer(
        {
            "stl": {
                "state": "on",
                "duration": 900,
                "until": 1795872151,
                "alarm": {"volume": 40, "morningLight": False, "tone": "alarmLoop3.opus"},
            }
        }
    )
    assert timer.alarm == Alarm("alarmLoop3.opus", 40, False)
    assert parse_sleep_timer({"stl": {"state": "on", "alarm": {"volume": 140}}}).alarm == Alarm(
        volume=100
    )
    assert parse_sleep_timer({"stl": {"state": "on", "alarm": {}}}).alarm is None
    assert parse_sleep_timer({"stl": {"state": "off", "defaultDuration": 1800}}).alarm is None


async def test_ringing_sensor(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """On while the alarm rings, with its tone; off once stopped on the box or gone offline."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)
    sensor = entity_id(hass, "binary_sensor", f"{BOX_ID}_alarm_ringing")

    async def box() -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
        result = await client.receive_json()
        return next(b for b in result["result"]["boxes"] if b["id"] == BOX_ID)

    push.last.connect()
    push.last.online(True)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == STATE_OFF
    assert hass.states.get(sensor).attributes["tone"] is None

    push.last.ring("alarmLoop3.opus")
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == STATE_ON
    assert hass.states.get(sensor).attributes["tone"] == "sound_hopper"
    assert (await box())["ringing"] == "alarmLoop3.opus"

    # Stopped with an ear
    push.last.ring(None)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == STATE_OFF
    assert (await box())["ringing"] is None

    # A box that goes offline rings no more
    push.last.ring("alarmLoop1.opus")
    push.last.online(False)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == STATE_OFF


async def test_the_alarm_on_the_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The next alarm says how it rings and whether the box carries it; the box's own settings show too."""
    client = await _setup(hass, cloud, config_entry, freezer, ws=hass_ws_client)
    sensor = entity_id(hass, "sensor", f"{BOX_ID}_next_alarm")
    attributes = hass.states.get(sensor).attributes
    # The school day's alarm rings Morgenglanz at 40 %, without the sunrise light
    assert (attributes["armed"], attributes["tone"], attributes["volume"]) == (
        False,
        "morning_glow",
        40,
    )
    assert attributes["morning_light"] is False

    push.last.connect()
    carried = Alarm("alarmLoop1.opus", 40, False)
    push.last.sleep_timer("on", until=TUESDAY_WAKEUP, alarm=carried)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).attributes["armed"] is True
    await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
    result = await client.receive_json()
    box = next(b for b in result["result"]["boxes"] if b["id"] == BOX_ID)
    assert box["sleep_timer"]["alarm"] == {
        "tone": "alarmLoop1.opus",
        "volume": 40,
        "morning_light": False,
    }
