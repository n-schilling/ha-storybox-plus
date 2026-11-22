"""Player commands from the page, headphones of a Toniebox 2, vouchers and content tokens."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.cloud import TOPIC_HEADPHONES
from custom_components.storybox_plus.cloud.models import parse_headphones
from custom_components.storybox_plus.const import DOMAIN

from .conftest import (
    BOX_ID,
    CLASSIC_BOX_ID,
    CREATIVE_ID,
    MAC,
    TONIE_ID,
    FakeCloud,
    PushChannels,
    tune,
)


async def _setup(
    hass: HomeAssistant, config_entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> Any:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return await hass_ws_client(hass)


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


def _command(command: str, value: int | None = None, box: str = BOX_ID) -> dict[str, Any]:
    message: dict[str, Any] = {"type": f"{DOMAIN}/box/command", "box_id": box, "command": command}
    if value is not None:
        message["value"] = value
    return message


# ---------------------------------------------------------------- player commands


async def test_commands_reach_the_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Each button of the card sends what the media player would send."""
    client = await _setup(hass, config_entry, hass_ws_client)
    channel = push.last
    channel.connect()
    channel.playback(TONIE_ID, chapter=0)
    for command, value in (
        ("pause", None),
        ("play", None),
        ("next", None),
        ("previous", None),
        ("volume", 4),
        ("sleep", 30),
        ("sleep_clear", None),
    ):
        result = await _call(client, _command(command, value))
        assert result["success"], (command, result)
    assert [(c, p) for _m, c, p in channel.commands] == [
        ("playback", {"action": "pause"}),
        ("playback", {"action": "start"}),
        ("playback", {"action": "setPosition", "chapter": 1, "ms": 0}),
        ("playback", {"action": "setPosition", "chapter": 0, "ms": 0}),
        ("volume", {"level": 4}),
        ("stl", {"state": "on", "duration": 1800}),
        ("stl", {"state": "off"}),
    ]
    assert all(m == MAC for m, _c, _p in channel.commands)


@pytest.mark.parametrize(
    ("message", "code"),
    [
        (_command("play", box="nobox"), "unknown_box"),
        (_command("play", box=CLASSIC_BOX_ID), "not_supported"),
        (_command("next"), "nothing_plays"),
        (_command("volume"), "invalid_command"),
        (_command("volume", 14), "invalid_format"),
        (_command("sleep"), "invalid_command"),
        (_command("sleep", 0), "invalid_command"),
        (_command("jump"), "invalid_format"),
    ],
)
async def test_command_refusals(
    hass: HomeAssistant,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Unknown boxes, the classic box, nothing on the box and missing values are refused."""
    client = await _setup(hass, config_entry, hass_ws_client)
    push.last.connect()
    push.last.removed()
    result = await _call(client, message)
    assert result["error"]["code"] == code
    assert push.last.commands == []


async def test_command_not_sent(
    hass: HomeAssistant,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Without the push channel the box gets nothing, and the page hears why."""
    client = await _setup(hass, config_entry, hass_ws_client)
    result = await _call(client, _command("pause"))
    assert result["error"]["code"] == "cloud_error"


async def test_sleep_timer_refused_while_an_alarm_is_due(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The sleep timer buttons would cancel the alarm of a bedtime; they are refused."""
    client = await hass_ws_client(hass)
    freezer.move_to(datetime(2026, 11, 9, 18, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    cloud.main.schedules[BOX_ID] = [
        {
            "id": "s1",
            "name": "School",
            "sleepTime": "19:00",
            "wakeupTime": "06:30",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "enabled": True,
            "alarmEnabled": True,
        }
    ]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    push.last.connect()
    result = await _call(client, _command("sleep", 30))
    assert result["error"]["code"] == "alarm_due"
    result = await _call(client, _command("sleep_clear"))
    assert result["error"]["code"] == "alarm_due"


# ---------------------------------------------------------------- headphones


def test_parse_headphones() -> None:
    """The first connected pair counts; an empty list means none."""
    parsed = parse_headphones({"connected": [{"type": "bluetooth", "battery": 70, "color": "red"}]})
    assert (parsed.connected, parsed.kind, parsed.battery) == (True, "bluetooth", 70)
    assert not parse_headphones({"connected": []}).connected
    assert not parse_headphones({}).connected
    assert parse_headphones({"connected": ["x"]}).connected
    assert parse_headphones({"connected": [{"battery": 300}]}).battery is None


async def test_headphones_on_the_card(
    hass: HomeAssistant,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The overview names connected headphones; a box switched off names none."""
    client = await _setup(hass, config_entry, hass_ws_client)
    channel = push.last
    channel.connect()
    channel.send(
        TOPIC_HEADPHONES, parse_headphones({"connected": [{"type": "bluetooth", "battery": 55}]})
    )

    async def headphones() -> Any:
        result = await _call(client, {"type": f"{DOMAIN}/overview"})
        return next(b for b in result["result"]["boxes"] if b["id"] == BOX_ID)["headphones"]

    assert await headphones() == {"connected": True, "kind": "bluetooth", "battery": 55}
    channel.online(False)
    assert await headphones() is None


# ---------------------------------------------------------------- vouchers and content tokens


async def test_redeem_voucher(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A good voucher brings Tunes, read anew at once; a bad one is the cloud's error."""
    cloud.main.tunes = [tune()]
    client = await _setup(hass, config_entry, hass_ws_client)
    result = await _call(
        client,
        {
            "type": f"{DOMAIN}/voucher/redeem",
            "entry_id": config_entry.entry_id,
            "code": " GOOD-CODE ",
        },
    )
    assert result["result"]["count"] == 1
    assert [t["title"] for t in result["result"]["tunes"]] == ["Bakabu", "New Tune"]
    result = await _call(
        client,
        {"type": f"{DOMAIN}/voucher/redeem", "entry_id": config_entry.entry_id, "code": "a/b c"},
    )
    assert result["error"]["code"] == "cloud_error"
    assert cloud.vouchers == ["GOOD-CODE", "a/b c"]
    result = await _call(
        client, {"type": f"{DOMAIN}/voucher/redeem", "entry_id": "nope", "code": "X"}
    )
    assert result["error"]["code"] == "unknown_entry"


async def test_redeem_token(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A content token goes to a creative figure, which is read anew; others are refused."""
    client = await _setup(hass, config_entry, hass_ws_client)
    result = await _call(
        client,
        {"type": f"{DOMAIN}/figure/redeem_token", "tonie_id": CREATIVE_ID, "token": "toniesong"},
    )
    assert result["success"], result
    assert result["result"]["id"] == CREATIVE_ID
    assert cloud.tokens == [(CREATIVE_ID, {"token": "toniesong"})]
    result = await _call(
        client,
        {"type": f"{DOMAIN}/figure/redeem_token", "tonie_id": CREATIVE_ID, "token": "wrong"},
    )
    assert result["error"]["code"] == "cloud_error"
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/redeem_token", "tonie_id": TONIE_ID, "token": "x"}
    )
    assert result["error"]["code"] == "not_creative"
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/redeem_token", "tonie_id": "nope", "token": "x"}
    )
    assert result["error"]["code"] == "unknown_figure"


async def test_a_chapter_is_chosen_from_the_list(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The overview names the chapters of what is on the box; one of them is jumped to."""
    client = await _setup(hass, config_entry, hass_ws_client)
    channel = push.last
    channel.connect()
    channel.playback(TONIE_ID, chapter=0)
    await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
    overview = (await client.receive_json())["result"]
    chapters = next(b for b in overview["boxes"] if b["id"] == BOX_ID)["playback"]["chapter_list"]
    assert len(chapters) > 1
    assert set(chapters[0]) == {"title", "seconds"}

    last = len(chapters) - 1
    assert (await _call(client, _command("chapter", last)))["success"]
    assert channel.commands[-1][1:] == (
        "playback",
        {"action": "setPosition", "chapter": last, "ms": 0},
    )
    sent = len(channel.commands)
    result = await _call(client, _command("chapter", last + 1))
    assert result["error"]["code"] == "invalid_value"
    channel.removed()
    result = await _call(client, _command("chapter", 0))
    assert result["error"]["code"] == "nothing_plays"
    assert len(channel.commands) == sent
