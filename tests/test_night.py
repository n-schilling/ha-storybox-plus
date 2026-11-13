"""Night mode of the light ring: the phases, the store, and the light ring set on the change."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.night import NightMode, NightModes, next_change, phase

from .conftest import BOX_ID, CLASSIC_BOX_ID, FakeCloud, PushChannels

BERLIN = ZoneInfo("Europe/Berlin")
EVENING = datetime(2026, 11, 9, 22, 0, tzinfo=BERLIN)
OVERNIGHT = NightMode(enabled=True, start="19:00", end="07:00", night=10, day=60)


@pytest.mark.parametrize(
    ("mode", "at", "expected"),
    [
        (OVERNIGHT, "22:00", "night"),
        (OVERNIGHT, "03:00", "night"),
        (OVERNIGHT, "19:00", "night"),
        (OVERNIGHT, "07:00", "day"),
        (OVERNIGHT, "12:00", "day"),
        (NightMode(True, "13:00", "15:00", 5, 50), "14:00", "night"),
        (NightMode(True, "13:00", "15:00", 5, 50), "15:00", "day"),
        (NightMode(True, "13:00", "13:00", 5, 50), "13:00", "day"),
    ],
)
def test_phase(mode: NightMode, at: str, expected: str) -> None:
    """The span may cross midnight; its end belongs to the day."""
    hour, minute = (int(p) for p in at.split(":"))
    assert phase(mode, EVENING.replace(hour=hour, minute=minute)) == expected


def test_next_change() -> None:
    """The next start or end, whichever comes first."""
    assert next_change(OVERNIGHT, EVENING) == datetime(2026, 11, 10, 7, 0, tzinfo=BERLIN)
    noon = EVENING.replace(hour=12)
    assert next_change(OVERNIGHT, noon) == EVENING.replace(hour=19)


async def test_store_round_trip(hass: HomeAssistant) -> None:
    """Modes and the applied phase survive; unreadable entries are left out."""
    store: Store[dict[str, Any]] = Store(hass, 1, "storybox_plus.test.night")
    await store.async_save(
        {
            "boxes": {
                "bad": {"enabled": True, "start": "x"},
                "old": {**OVERNIGHT.as_dict(), "applied": "maybe"},
            }
        }
    )
    modes = NightModes(store)
    await modes.async_load()
    assert modes.get("bad") is None
    assert modes.get("old") == OVERNIGHT
    await modes.async_set("b", NightMode(True, "20:00", "06:00", 0, 80, applied="night"))
    await modes.async_applied("b", "day")
    await modes.async_applied("nobox", "day")
    again = NightModes(Store(hass, 1, "storybox_plus.test.night"))
    await again.async_load()
    assert again.get("b") == NightMode(True, "20:00", "06:00", 0, 80, applied="day")


async def _setup(
    hass: HomeAssistant,
    cloud: FakeCloud,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    ws: WebSocketGenerator,
    stored: dict[str, Any] | None = None,
) -> Any:
    client = await ws(hass)
    freezer.move_to(EVENING)
    if stored is not None:
        hass_storage_key = f"storybox_plus.{config_entry.entry_id}.night"
        await Store(hass, 1, hass_storage_key).async_save({"boxes": stored})
    cloud.main.box(BOX_ID)["lightringBrightness"] = 60
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return client


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


def _night_message(**kwargs: Any) -> dict[str, Any]:
    return {
        "type": f"{DOMAIN}/night/set",
        "box_id": BOX_ID,
        "enabled": True,
        "start": "19:00",
        "end": "07:00",
        "night": 10,
        "day": 60,
        **kwargs,
    }


def _rings(cloud: FakeCloud) -> list[int]:
    return [p["lightringBrightness"] for _box, p in cloud.box_patches if "lightringBrightness" in p]


async def test_night_mode_dims_and_restores(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Set at night, the ring dims at once; at the end of the span it comes back, once."""
    client = await _setup(hass, cloud, config_entry, freezer, hass_ws_client)
    result = await _call(client, _night_message())
    assert result["success"], result
    await hass.async_block_till_done()
    assert _rings(cloud) == [10]
    overview = await _call(client, {"type": f"{DOMAIN}/overview"})
    box = next(b for b in overview["result"]["boxes"] if b["id"] == BOX_ID)
    assert box["night"] == {
        "mode": {
            "enabled": True,
            "start": "19:00",
            "end": "07:00",
            "night": 10,
            "day": 60,
            "applied": "night",
        },
        "phase": "night",
    }
    # Polls during the night change nothing
    await config_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _rings(cloud) == [10]
    freezer.move_to(datetime(2026, 11, 10, 7, 0, 1, tzinfo=BERLIN))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _rings(cloud) == [10, 60]
    classic = next(b for b in overview["result"]["boxes"] if b["id"] == CLASSIC_BOX_ID)
    assert classic["night"] is None


async def test_switched_off_at_night_restores_the_ring(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Switching the night mode off at night brings the normal brightness back now."""
    client = await _setup(hass, cloud, config_entry, freezer, hass_ws_client)
    await _call(client, _night_message())
    await hass.async_block_till_done()
    result = await _call(client, _night_message(enabled=False))
    assert result["success"], result
    await hass.async_block_till_done()
    assert _rings(cloud) == [10, 60]
    assert result["result"]["night"]["phase"] is None


async def test_missed_change_made_up_at_start(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The store says day was applied; it is night at the start, so the ring dims."""
    await _setup(
        hass,
        cloud,
        config_entry,
        freezer,
        hass_ws_client,
        {BOX_ID: {**OVERNIGHT.as_dict(), "applied": "day"}},
    )
    assert _rings(cloud) == [10]


async def test_refused_change_tried_again(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A change the cloud refuses is not noted as applied and is sent with the next poll."""
    client = await _setup(hass, cloud, config_entry, freezer, hass_ws_client)
    cloud.main.rest_status = 500
    await _call(client, _night_message())
    await hass.async_block_till_done()
    assert _rings(cloud) == []
    assert config_entry.runtime_data.night_modes.get(BOX_ID).applied is None
    cloud.main.rest_status = None
    await config_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _rings(cloud) == [10]


@pytest.mark.parametrize(
    ("message", "code"),
    [
        (_night_message(box_id="nobox"), "unknown_box"),
        (_night_message(box_id=CLASSIC_BOX_ID), "not_supported"),
        (_night_message(start="07:00"), "invalid_format"),
        (_night_message(night=101), "invalid_format"),
        (_night_message(end="7:00"), "invalid_format"),
    ],
)
async def test_night_refusals(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Unknown boxes, the classic box, an empty span and bad values are refused."""
    client = await _setup(hass, cloud, config_entry, freezer, hass_ws_client)
    result = await _call(client, message)
    assert result["error"]["code"] == code
    assert config_entry.runtime_data.night_modes.get(BOX_ID) is None
