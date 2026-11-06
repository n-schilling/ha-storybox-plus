"""The WebSocket commands of the page: overview, library and listening statistics."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
import threading
from typing import Any

import aiohttp
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator, WebSocketGenerator

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus import youtube
from custom_components.storybox_plus.const import CONF_ANALYTICS, DOMAIN
from custom_components.storybox_plus.websocket import _content_type

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
            {"id": "0", "title": "Kapitel 1", "seconds": None, "transcoding": False},
            {"id": "1", "title": "Kapitel 2", "seconds": None, "transcoding": False},
        ],
        "seconds_remaining": None,
        "chapters_remaining": None,
        "transcoding": False,
        "transcoding_errors": [],
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


# ---------------------------------------------------------------- chapters


def _creative_with_chapters(cloud: FakeCloud) -> None:
    """Give the creative figure three chapters, to rearrange them."""
    cloud.main.creative_tonies[HOUSEHOLD_ID][0]["chapters"] = [
        {"id": "ch1", "title": "Song", "file": "f1", "seconds": 120.5, "transcoding": False},
        {"id": "ch2", "title": "Story", "file": "f2", "seconds": 300, "transcoding": False},
        {"id": "ch3", "title": "Lullaby", "file": "f3", "seconds": 60, "transcoding": False},
    ]


async def test_arrange_chapters(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Order and deletions go to the cloud as one list; the page gets the figure as it is now."""
    _creative_with_chapters(cloud)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    result = await _ask(
        client,
        {"type": f"{DOMAIN}/chapters/arrange", "tonie_id": CREATIVE_ID, "chapters": ["ch3", "ch1"]},
    )
    assert result["success"], result
    assert [c["id"] for c in result["result"]["chapters"]] == ["ch3", "ch1"]
    assert result["result"]["transcoding"] is True
    assert result["result"]["on_box"] is None
    (patch,) = cloud.chapter_patches
    assert patch[:2] == (HOUSEHOLD_ID, CREATIVE_ID)
    assert patch[2] == {
        "chapters": [
            {"id": "ch3", "title": "Lullaby", "file": "f3", "seconds": 60, "transcoding": False},
            {"id": "ch1", "title": "Song", "file": "f1", "seconds": 120.5, "transcoding": False},
        ]
    }
    # The library knows the new order at once, without waiting for the next poll
    library = await _ask(client, {"type": f"{DOMAIN}/library"})
    creative = next(t for t in library["result"]["tonies"] if t["id"] == CREATIVE_ID)
    assert [c["title"] for c in creative["chapters"]] == ["Lullaby", "Song"]


async def test_arrange_chapters_answered_without_body(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """When the cloud answers a change with nothing, the figure is read again."""
    cloud.main.chapters_no_body = True
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/arrange", "tonie_id": CREATIVE_ID, "chapters": []}
    )
    assert result["success"], result
    assert result["result"]["chapters"] == []
    assert result["result"]["transcoding"] is True


@pytest.mark.parametrize(
    ("tonie_id", "chapters", "code"),
    [
        ("nope", ["ch1"], "unknown_figure"),
        (TONIE_ID, ["0"], "not_creative"),
        (CREATIVE_ID, ["ch1", "ch9"], "unknown_chapter"),
        (CREATIVE_ID, ["ch1", "ch1"], "unknown_chapter"),
    ],
)
async def test_arrange_chapters_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    tonie_id: str,
    chapters: list[str],
    code: str,
) -> None:
    """Unknown figures, bought figures and unknown or doubled chapters never reach the cloud."""
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/arrange", "tonie_id": tonie_id, "chapters": chapters}
    )
    assert not result["success"]
    assert result["error"]["code"] == code
    assert result["error"]["message"]
    assert not cloud.chapter_patches


async def test_arrange_chapters_cloud_error(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The cloud's refusal reaches the page with its codes; the library keeps the old chapters."""
    cloud.main.chapters_error = (429, {"retryInSeconds": 60})
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/arrange", "tonie_id": CREATIVE_ID, "chapters": []}
    )
    assert not result["success"]
    assert result["error"]["code"] == "cloud_error"
    assert "429" in result["error"]["message"]
    assert "retry in 60 s" in result["error"]["message"]
    library = await _ask(client, {"type": f"{DOMAIN}/library"})
    creative = next(t for t in library["result"]["tonies"] if t["id"] == CREATIVE_ID)
    assert [c["id"] for c in creative["chapters"]] == ["ch1"]


async def _upload(hass_client: ClientSessionGenerator, name: str, content: bytes) -> str:
    """Upload a file as the page does, through Home Assistant's own endpoint."""
    http = await hass_client()
    # Browsers send the file name as it is; aiohttp would percent-encode the space
    data = aiohttp.FormData(quote_fields=False)
    data.add_field("file", content, filename=name, content_type="audio/mpeg")
    response = await http.post("/api/file_upload", data=data)
    assert response.status == 200, await response.text()
    return str((await response.json())["file_id"])


async def test_add_chapter(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
) -> None:
    """A file uploaded to Home Assistant goes to the cloud's storage and becomes a chapter."""
    file_id = await _upload(hass_client, "Gute Nacht.mp3", b"ID3 lullaby")
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add", "tonie_id": CREATIVE_ID, "file_id": file_id}
    )
    assert result["success"], result
    chapters = result["result"]["chapters"]
    assert [c["title"] for c in chapters] == ["Song", "Gute Nacht"]
    assert chapters[1]["transcoding"] is True
    assert result["result"]["transcoding"] is True
    assert cloud.upload_tickets == 1
    (upload,) = cloud.s3_uploads
    assert upload["bearer"] is False
    assert upload["fields"] == [
        ("key", None, None, len("uploads/file-1")),
        ("policy", None, None, len("signed")),
        ("file", "Gute Nacht.mp3", "audio/mpeg", len(b"ID3 lullaby")),
    ]
    (added,) = cloud.chapter_adds
    assert added == (
        HOUSEHOLD_ID,
        CREATIVE_ID,
        {"title": "Gute Nacht", "file": "file-1", "type": "file"},
    )
    # The uploaded file is gone from Home Assistant once taken
    again = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add", "tonie_id": CREATIVE_ID, "file_id": file_id}
    )
    assert not again["success"]
    assert again["error"]["code"] == "unknown_file"


async def test_add_chapter_with_title_and_type(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
) -> None:
    """A given title wins over the file name; the content type follows the file's ending."""
    file_id = await _upload(hass_client, "track01.M4A", b"audio")
    client = await hass_ws_client(hass)
    result = await _ask(
        client,
        {
            "type": f"{DOMAIN}/chapters/add",
            "tonie_id": CREATIVE_ID,
            "file_id": file_id,
            "title": "  Lied  ",
        },
    )
    assert result["success"], result
    (upload,) = cloud.s3_uploads
    assert upload["fields"][-1][:3] == ("file", "track01.M4A", "audio/mp4")
    assert cloud.chapter_adds[0][2]["title"] == "Lied"


@pytest.mark.parametrize(
    ("tonie_id", "content", "code"),
    [
        ("nope", b"audio", "unknown_figure"),
        (TONIE_ID, b"audio", "not_creative"),
        (CREATIVE_ID, b"", "empty_file"),
    ],
)
async def test_add_chapter_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
    tonie_id: str,
    content: bytes,
    code: str,
) -> None:
    """Unknown or bought figures and empty files never reach the cloud."""
    file_id = await _upload(hass_client, "a.mp3", content)
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add", "tonie_id": tonie_id, "file_id": file_id}
    )
    assert not result["success"]
    assert result["error"]["code"] == code
    assert cloud.upload_tickets == 0
    assert not cloud.chapter_adds


async def test_add_chapter_storage_refuses(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
) -> None:
    """A refusal of the storage reaches the page; no chapter is added."""
    cloud.s3_status = 403
    file_id = await _upload(hass_client, "a.mp3", b"audio")
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add", "tonie_id": CREATIVE_ID, "file_id": file_id}
    )
    assert not result["success"]
    assert result["error"]["code"] == "cloud_error"
    assert "403" in result["error"]["message"]
    assert not cloud.chapter_adds


async def test_refresh_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A creative figure is read again on request, bought figures and unknown ones are refused."""
    raw = cloud.main.creative_tonies[HOUSEHOLD_ID][0]
    raw["transcoding"] = False
    raw["chapters"][0]["seconds"] = 99
    raw["transcodingErrors"] = [{"reason": "wrongFormat", "deletedChapters": [{"title": "x"}]}]
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/figure/refresh", "tonie_id": CREATIVE_ID})
    assert result["success"], result
    assert result["result"]["chapters"][0]["seconds"] == 99
    assert result["result"]["transcoding_errors"] == ["wrongFormat"]
    for tonie_id, code in (("nope", "unknown_figure"), (TONIE_ID, "not_creative")):
        refused = await _ask(client, {"type": f"{DOMAIN}/figure/refresh", "tonie_id": tonie_id})
        assert not refused["success"]
        assert refused["error"]["code"] == code
    # A figure the cloud no longer has
    cloud.main.creative_tonies[HOUSEHOLD_ID].clear()
    gone = await _ask(client, {"type": f"{DOMAIN}/figure/refresh", "tonie_id": CREATIVE_ID})
    assert not gone["success"]
    assert gone["error"]["code"] == "unknown_figure"


VIDEO_ID = "jNQXAC9IVRw"
VIDEO_URL = f"https://youtu.be/{VIDEO_ID}"
VIDEO = youtube.Video(id=VIDEO_ID, title="Me at the zoo", seconds=19)


def _fake_youtube(
    monkeypatch: pytest.MonkeyPatch,
    video: youtube.Video = VIDEO,
    probe_error: Exception | None = None,
    hold: threading.Event | None = None,
) -> dict[str, Any]:
    """Stand in for the yt-dlp wrapper: a canned video, a written file, the calls kept.

    With `hold`, the download waits for the cancel event (or the hold) instead
    of finishing, as a long download would.
    """
    seen: dict[str, Any] = {"calls": [], "folder": None}

    def probe(url: str) -> youtube.Video:
        seen["calls"].append(("probe", url))
        if probe_error is not None:
            raise probe_error
        return video

    def download(
        url: str, folder: Path, progress: youtube.Progress, cancelled: threading.Event
    ) -> Path:
        seen["calls"].append(("download", url))
        seen["folder"] = folder
        assert folder.is_dir()
        assert folder.name.startswith(f"{DOMAIN}_")
        if hold is not None:
            hold.set()
            assert cancelled.wait(5)
            raise youtube.YouTubeCancelled("The download was cancelled")
        progress(10, 20)
        path = folder / f"{video.id}.m4a"
        path.write_bytes(b"aac")
        return path

    monkeypatch.setattr(youtube, "probe", probe)
    monkeypatch.setattr(youtube, "download", download)
    return seen


async def _events_until_end(client: Any) -> list[dict[str, Any]]:
    """Collect the events of a subscription up to "done" or "error"."""
    events: list[dict[str, Any]] = []
    while True:
        message = await client.receive_json()
        assert message["type"] == "event", message
        events.append(message["event"])
        if message["event"]["stage"] in ("done", "error"):
            return events


async def test_add_link(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A YouTube link is read, fetched and uploaded as a chapter; the page hears every stage."""
    seen = _fake_youtube(monkeypatch)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL}
    )
    result = await client.receive_json()
    assert result["success"], result
    events = await _events_until_end(client)
    about = {"title": "Me at the zoo", "seconds": 19}
    assert events[:4] == [
        {"stage": "probe"},
        {"stage": "download", **about, "done": 0, "total": None},
        {"stage": "download", **about, "done": 10, "total": 20},
        {"stage": "upload", **about, "done": 0, "total": 3},
    ]
    assert events[4]["stage"] == "done"
    figure = events[4]["figure"]
    assert [c["title"] for c in figure["chapters"]] == ["Song", "Me at the zoo"]
    assert figure["transcoding"] is True
    assert seen["calls"] == [("probe", VIDEO_URL), ("download", VIDEO_URL)]
    # The file went to the cloud as M4A and the folder is gone
    (upload,) = cloud.s3_uploads
    assert upload["fields"][-1] == ("file", f"{VIDEO_ID}.m4a", "audio/mp4", 3)
    (added,) = cloud.chapter_adds
    assert added[2] == {"title": "Me at the zoo", "file": "file-1", "type": "file"}
    assert not seen["folder"].exists()
    # The subscription ends when the page unsubscribes
    await client.send_json_auto_id({"type": "unsubscribe_events", "subscription": result["id"]})
    assert (await client.receive_json())["success"]


@pytest.mark.parametrize(
    ("tonie_id", "url", "video", "probe_error", "code", "message"),
    [
        (TONIE_ID, VIDEO_URL, VIDEO, None, "not_creative", "Only creative figures take chapters"),
        (
            CREATIVE_ID,
            "https://example.com/watch?v=x",
            VIDEO,
            None,
            "not_youtube",
            "Only links to YouTube videos are taken",
        ),
        (
            CREATIVE_ID,
            VIDEO_URL,
            youtube.Video(id=VIDEO_ID, title="Long", seconds=6000),
            None,
            "too_long",
            "The video lasts 1:40:00, the figure has 1:23:20 left",
        ),
        (
            CREATIVE_ID,
            VIDEO_URL,
            VIDEO,
            youtube.YouTubeError("Video unavailable"),
            "video_error",
            "Video unavailable",
        ),
        (CREATIVE_ID, VIDEO_URL, VIDEO, RuntimeError("boom"), "unknown_error", "boom"),
    ],
)
async def test_add_link_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tonie_id: str,
    url: str,
    video: youtube.Video,
    probe_error: Exception | None,
    code: str,
    message: str,
) -> None:
    """What is refused, or fails, ends the subscription with an error event; nothing is fetched."""
    seen = _fake_youtube(monkeypatch, video=video, probe_error=probe_error)
    client = await hass_ws_client(hass)
    with caplog.at_level(logging.ERROR):
        await client.send_json_auto_id(
            {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": tonie_id, "url": url}
        )
        assert (await client.receive_json())["success"]
        events = await _events_until_end(client)
    assert events[-1] == {"stage": "error", "code": code, "message": message}
    assert ("download", url) not in seen["calls"]
    assert not cloud.chapter_adds
    assert ("Adding a chapter from YouTube failed" in caplog.text) is (code == "unknown_error")


async def test_add_link_unknown_figure_and_cloud_error(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A figure of no account is refused at once; a refusal of the cloud ends with its words."""
    _fake_youtube(monkeypatch)
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": "nope", "url": VIDEO_URL}
    )
    assert not result["success"]
    assert result["error"]["code"] == "unknown_figure"
    cloud.main.chapters_error = (429, {"retryInSeconds": 30})
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL}
    )
    assert (await client.receive_json())["success"]
    events = await _events_until_end(client)
    assert events[-1]["stage"] == "error"
    assert events[-1]["code"] == "cloud_error"
    assert "429" in events[-1]["message"]
    assert "retry in 30 s" in events[-1]["message"]


async def test_add_link_stops_when_the_page_unsubscribes(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsubscribing while the download runs cancels it; no chapter is added and nothing more is sent."""
    hold = threading.Event()
    seen = _fake_youtube(monkeypatch, hold=hold)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL}
    )
    result = await client.receive_json()
    assert result["success"]
    assert (await client.receive_json())["event"] == {"stage": "probe"}
    assert (await client.receive_json())["event"]["stage"] == "download"
    # The download thread is waiting for the cancel event now
    await hass.async_add_executor_job(hold.wait, 5)
    await client.send_json_auto_id({"type": "unsubscribe_events", "subscription": result["id"]})
    assert (await client.receive_json())["success"]
    # The task ends quietly: the next answer is the one to the next command
    await asyncio.sleep(0)
    await hass.async_block_till_done()
    overview = await _ask(client, {"type": f"{DOMAIN}/overview"})
    assert overview["success"]
    assert overview["type"] == "result"
    assert not cloud.chapter_adds
    assert not seen["folder"].exists()


@pytest.mark.parametrize(
    "msg",
    [
        {"type": f"{DOMAIN}/chapters/arrange", "tonie_id": CREATIVE_ID, "chapters": []},
        {"type": f"{DOMAIN}/chapters/add", "tonie_id": CREATIVE_ID, "file_id": "x"},
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL},
        {"type": f"{DOMAIN}/figure/refresh", "tonie_id": CREATIVE_ID},
    ],
)
async def test_chapter_commands_need_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
    msg: dict[str, Any],
) -> None:
    """Changing chapters is for administrators only."""
    client = await hass_ws_client(hass, access_token=hass_read_only_access_token)
    result = await _ask(client, msg)
    assert not result["success"]
    assert result["error"]["code"] == "unauthorized"
    assert not cloud.chapter_patches
    assert not cloud.chapter_adds


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("a.mp3", "audio/mpeg"),
        ("a.M4B", "audio/mp4"),
        ("a.opus", "audio/ogg"),
        ("a.flac", "audio/flac"),
        ("a.wma", "audio/x-ms-wma"),
        ("a.aiff", "audio/x-aiff"),
        ("a.txt", "audio/mpeg"),
        ("noending", "audio/mpeg"),
    ],
)
def test_content_type_by_ending(filename: str, content_type: str) -> None:
    """The upload's content type follows the file ending; unknown ones count as MP3."""
    assert _content_type(filename) == content_type
