"""The WebSocket commands of the page: overview, library and listening statistics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus.const import CONF_ANALYTICS, DOMAIN

from .conftest import (
    BOX_ID,
    BOX_NAME,
    CLASSIC_BOX_ID,
    CREATIVE_ID,
    CREATIVE_NAME,
    DISC_NAME,
    HOUSEHOLD_ID,
    HOUSEHOLD_NAME,
    TONIE_ID,
    TONIE_NAME,
    TONIE_SERIES,
    FakeCloud,
    PushChannels,
    content_tonie,
    entry_for,
    tb2_box,
)

OTHER_MAC = "0A1B2C3D4E5F"


async def _ask(client: Any, msg: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(msg)
    return await client.receive_json()


def _box(result: dict[str, Any], box_id: str) -> dict[str, Any]:
    return next(b for b in result["result"]["boxes"] if b["id"] == box_id)


async def test_overview(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The overview shows every account and box with the live state and what plays."""
    until = datetime(2026, 11, 4, 20, 0, tzinfo=UTC)
    channel = push.last
    channel.connect()
    channel.battery(80, "charging")
    channel.volume(7)
    channel.sleep_timer("on", until=until)
    channel.playback(chapter=1, duration=200.0, position=50.0)

    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/overview"})
    assert result["success"]
    assert result["result"]["entries"] == [
        {"entry_id": setup_entry.entry_id, "title": HOUSEHOLD_NAME, "loaded": True}
    ]
    assert result["result"]["push_connected"] is True
    box = _box(result, BOX_ID)
    playback = box.pop("playback")
    assert box == {
        "id": BOX_ID,
        "entry_id": setup_entry.entry_id,
        "name": BOX_NAME,
        "household": HOUSEHOLD_NAME,
        "generation": "toniebox_2",
        "firmware": "1.2.3",
        "online": True,
        "last_seen": "2026-11-04T10:00:00+00:00",
        "battery": 80,
        "charging": True,
        "volume": 7,
        "volume_max": 13,
        "sleep_timer": {"state": "on", "until": "2026-11-04T20:00:00+00:00"},
        "battery_stats": {"current": None, "cycles": [], "count": 0, "average_full_hours": None},
    }
    received_at = playback.pop("received_at")
    assert isinstance(received_at, str)
    assert playback == {
        "tonie_id": TONIE_ID,
        "tonie_name": TONIE_NAME,
        "image_url": f"https://img.example.com/{TONIE_ID}.png",
        "chapter": 1,
        "chapter_title": "Kapitel 2",
        "chapters": 2,
        "playing": True,
        "paused": False,
        "ended": False,
        "position": 50.0,
        "duration": 200.0,
    }
    classic = _box(result, CLASSIC_BOX_ID)
    assert classic["generation"] == "classic"
    assert classic["online"] is True
    assert classic["battery"] is None
    assert classic["volume"] is None
    assert classic["sleep_timer"] is None
    assert classic["playback"] is None
    assert classic["battery_stats"] is None


async def test_overview_before_any_push(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Before the channel speaks, the figure the cloud lists as placed is shown without a position."""
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/overview"})
    assert result["result"]["push_connected"] is False
    box = _box(result, BOX_ID)
    assert box["battery"] is None
    assert box["sleep_timer"] is None
    assert box["playback"] == {
        "tonie_id": TONIE_ID,
        "tonie_name": TONIE_NAME,
        "image_url": f"https://img.example.com/{TONIE_ID}.png",
        "chapter": None,
        "chapter_title": None,
        "chapters": 2,
        "playing": False,
        "paused": None,
        "ended": None,
        "position": None,
        "duration": None,
        "received_at": None,
    }


async def test_overview_with_unknown_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A figure the library does not know is shown by its ID only; a removed one not at all."""
    push.last.playback(tonie_id="unknown-figure", chapter=3)
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/overview"})
    playback = _box(result, BOX_ID)["playback"]
    assert playback["tonie_id"] == "unknown-figure"
    assert playback["tonie_name"] is None
    assert playback["image_url"] is None
    assert playback["chapter"] == 3
    assert playback["chapter_title"] is None
    assert playback["chapters"] is None

    push.last.removed()
    result = await _ask(client, {"type": f"{DOMAIN}/overview"})
    assert _box(result, BOX_ID)["playback"] is None


async def test_overview_lists_accounts_that_failed(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """An account that is not loaded is listed as such and brings no boxes."""
    broken = cloud.add_account("broken", refresh_refused=True)
    entry = entry_for(broken)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR

    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/overview"})
    assert [(e["entry_id"], e["loaded"]) for e in result["result"]["entries"]] == [
        (setup_entry.entry_id, True),
        (entry.entry_id, False),
    ]
    assert {b["entry_id"] for b in result["result"]["boxes"]} == {setup_entry.entry_id}


async def test_library(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The library lists households and every figure, sorted by name, with where it stands."""
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/library"})
    assert result["success"]
    assert result["result"]["households"] == [
        {"id": HOUSEHOLD_ID, "name": HOUSEHOLD_NAME, "entry_id": setup_entry.entry_id}
    ]
    tonies = result["result"]["tonies"]
    assert [t["name"] for t in tonies] == [DISC_NAME, CREATIVE_NAME, TONIE_NAME]
    assert tonies[2] == {
        "id": TONIE_ID,
        "household_id": HOUSEHOLD_ID,
        "kind": "content",
        "name": TONIE_NAME,
        "series": TONIE_SERIES,
        "image_url": f"https://img.example.com/{TONIE_ID}.png",
        "language": "Deutsch",
        "locked": False,
        "seconds": 500,
        "chapters": [
            {"id": "k1", "title": "Kapitel 1", "seconds": 300, "transcoding": False},
            {"id": "k2", "title": "Kapitel 2", "seconds": 200, "transcoding": False},
        ],
        "seconds_remaining": None,
        "chapters_remaining": None,
        "transcoding": False,
        "on_box": BOX_ID,
    }
    creative = tonies[1]
    assert creative["id"] == CREATIVE_ID
    assert creative["kind"] == "creative"
    assert creative["seconds_remaining"] == 5000
    assert creative["chapters_remaining"] == 80
    assert creative["on_box"] is None
    assert tonies[0]["kind"] == "disc"
    assert tonies[0]["chapters"] == []


async def test_analytics(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The statistics rank figures, sum days and boxes, and name what is known."""
    today = dt_util.now().date().isoformat()
    channel = push.last
    channel.connect()
    channel.playback(paused=False)
    freezer.tick(timedelta(seconds=120))
    channel.playback(tonie_id="unknown-figure", paused=False)
    freezer.tick(timedelta(seconds=30))
    channel.playback(tonie_id="unknown-figure", paused=True)

    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/analytics"})
    assert result["success"]
    assert result["result"] == {
        "enabled": True,
        "days": None,
        "first_day": today,
        "total_seconds": 150,
        "top": [
            {
                "tonie_id": TONIE_ID,
                "name": TONIE_NAME,
                "image_url": f"https://img.example.com/{TONIE_ID}.png",
                "kind": "content",
                "seconds": 120,
            },
            {
                "tonie_id": "unknown-figure",
                "name": None,
                "image_url": None,
                "kind": None,
                "seconds": 30,
            },
        ],
        "per_day": [{"day": today, "seconds": 150}],
        "per_box": [{"box_id": BOX_ID, "name": BOX_NAME, "seconds": 150}],
    }

    result = await _ask(client, {"type": f"{DOMAIN}/analytics", "days": 1, "limit": 1})
    assert result["result"]["days"] == 1
    assert [t["tonie_id"] for t in result["result"]["top"]] == [TONIE_ID]
    assert result["result"]["total_seconds"] == 150


async def test_analytics_switched_off(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Without counting the statistics say so and are empty."""
    entry = entry_for(cloud.main, options={CONF_ANALYTICS: False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/analytics", "days": None})
    assert result["result"] == {
        "enabled": False,
        "days": None,
        "first_day": None,
        "total_seconds": 0,
        "top": [],
        "per_day": [],
        "per_box": [],
    }


@pytest.mark.parametrize(
    "fields",
    [{"days": 0}, {"days": 3661}, {"days": "7"}, {"limit": 0}, {"limit": 101}, {"limit": None}],
)
async def test_analytics_rejects_bad_ranges(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    fields: dict[str, Any],
) -> None:
    """Days and limit must be within their ranges."""
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/analytics", **fields})
    assert not result["success"]
    assert result["error"]["code"] == "invalid_format"


async def test_analytics_sums_over_accounts(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Two accounts are added up: days, boxes and figures, with the earliest first day."""
    yesterday = (dt_util.now().date() - timedelta(days=1)).isoformat()
    today = dt_util.now().date().isoformat()
    second = cloud.add_account(
        "second",
        households=[{"id": "hh2", "name": "Zweite"}],
        boxes={"hh2": [tb2_box("box9", name="Oma", mac=OTHER_MAC, placed=None)]},
        content_tonies=[content_tonie("t9", name="Oma Tonie", household_id="hh2")],
    )
    entry = entry_for(second)
    key = f"{DOMAIN}.{entry.entry_id}.analytics"
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {"days": {yesterday: {"box9": {"t9": 600}}}},
    }
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    first, latest = push.instances
    first.connect()
    latest.connect()
    first.playback(paused=False)
    latest.playback(tonie_id="t9", paused=False, mac=OTHER_MAC)
    freezer.tick(timedelta(seconds=100))
    first.playback(paused=True)
    latest.playback(tonie_id="t9", paused=True, mac=OTHER_MAC)

    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/analytics", "limit": 5})
    body = result["result"]
    assert body["first_day"] == yesterday
    assert body["total_seconds"] == 800
    assert [(t["tonie_id"], t["name"], t["seconds"]) for t in body["top"]] == [
        ("t9", "Oma Tonie", 700),
        (TONIE_ID, TONIE_NAME, 100),
    ]
    assert body["per_day"] == [{"day": yesterday, "seconds": 600}, {"day": today, "seconds": 200}]
    assert body["per_box"] == [
        {"box_id": "box9", "name": "Oma", "seconds": 700},
        {"box_id": BOX_ID, "name": BOX_NAME, "seconds": 100},
    ]

    overview = await _ask(client, {"type": f"{DOMAIN}/overview"})
    assert len(overview["result"]["entries"]) == 2
    assert {b["id"] for b in overview["result"]["boxes"]} == {BOX_ID, CLASSIC_BOX_ID, "box9"}
    library = await _ask(client, {"type": f"{DOMAIN}/library"})
    assert [h["name"] for h in library["result"]["households"]] == [HOUSEHOLD_NAME, "Zweite"]
    assert len(library["result"]["tonies"]) == 4


@pytest.mark.parametrize("command", ["overview", "library", "analytics"])
async def test_non_admins_are_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
    command: str,
) -> None:
    """The page's data is for administrators only."""
    client = await hass_ws_client(hass, access_token=hass_read_only_access_token)
    result = await _ask(client, {"type": f"{DOMAIN}/{command}"})
    assert not result["success"]
    assert result["error"]["code"] == "unauthorized"
