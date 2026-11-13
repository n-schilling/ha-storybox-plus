"""Settings of a box: parsed from the cloud, shown on the page, changed by administrators."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.cloud.models import parse_box, parse_box_settings
from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.coordinator import setting_supported

from .conftest import BOX_ID, CLASSIC_BOX_ID, FakeCloud, PushChannels

LIVE_SETTINGS = {
    "maxVolume": 75,
    "maxHeadphoneVolume": 50,
    "lightringBrightness": 60,
    "bedtimeLightringBrightness": 10,
    "bedtimeMaxVolume": 40,
    "bedtimeMaxHeadphoneVolume": 30,
    "skippingEnabled": True,
    "skippingDirection": "right",
    "scrubbingEnabled": False,
    "language": "de",
    "ageMode": "3+",
    "settingsApplied": True,
    "offlineMode": False,
}
CLASSIC_SETTINGS = {
    "maxVolume": 100,
    "maxHeadphoneVolume": 75,
    "accelerometerEnabled": True,
    "tapDirection": "left",
    "ledLevel": "dimmed",
    "settingsApplied": False,
}


def test_parse_settings() -> None:
    """Named settings are taken; values of the wrong kind count as unnamed."""
    settings = parse_box_settings(
        {**LIVE_SETTINGS, "scrubbingEnabled": "yes", "ledLevel": 3, "lightringBrightness": "60"}
    )
    assert settings.max_volume == 75
    assert settings.lightring_brightness is None
    assert settings.skipping_enabled is True
    assert settings.scrubbing_enabled is None
    assert settings.led_level is None
    assert settings.language == "de"
    assert settings.offline_mode is False
    assert settings.settings_applied is True
    empty = parse_box_settings({})
    assert empty.max_volume is None
    assert empty.settings_applied is None


def test_setting_supported() -> None:
    """A setting belongs to a generation or to a feature flag."""
    live = parse_box({"id": "b", "features": ["tngSettings", "language"]}, "hh")
    classic = parse_box({"id": "c", "features": ["ageMode"]}, "hh")
    assert live is not None
    assert classic is not None
    assert setting_supported(live, "max_volume")
    assert setting_supported(live, "lightring_brightness")
    assert not setting_supported(live, "led_level")
    assert setting_supported(live, "language")
    assert not setting_supported(live, "age_mode")
    assert setting_supported(classic, "led_level")
    assert not setting_supported(classic, "skipping_enabled")
    assert setting_supported(classic, "age_mode")
    assert not setting_supported(classic, "language")
    assert not setting_supported(classic, "nonsense")


async def _setup(
    hass: HomeAssistant,
    cloud: FakeCloud,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> Any:
    cloud.main.box(BOX_ID).update(LIVE_SETTINGS)
    cloud.main.box(BOX_ID)["features"].extend(["language", "ageMode"])
    cloud.main.box(CLASSIC_BOX_ID).update(CLASSIC_SETTINGS)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return await hass_ws_client(hass)


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


async def test_overview_shows_the_settings_of_each_generation(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Each box shows the settings it has, and whether it has taken them."""
    client = await _setup(hass, cloud, config_entry, hass_ws_client)
    result = await _call(client, {"type": f"{DOMAIN}/overview"})
    boxes = {b["id"]: b for b in result["result"]["boxes"]}
    assert boxes[BOX_ID]["settings"] == {
        "values": {
            "max_volume": 75,
            "max_headphone_volume": 50,
            "lightring_brightness": 60,
            "bedtime_lightring_brightness": 10,
            "bedtime_max_volume": 40,
            "bedtime_max_headphone_volume": 30,
            "skipping_enabled": True,
            "skipping_direction": "right",
            "scrubbing_enabled": False,
            "age_mode": "3+",
            "language": "de",
        },
        "offline_mode": False,
        "applied": True,
    }
    assert boxes[CLASSIC_BOX_ID]["settings"] == {
        "values": {
            "max_volume": 100,
            "max_headphone_volume": 75,
            "accelerometer_enabled": True,
            "tap_direction": "left",
            "led_level": "dimmed",
        },
        "offline_mode": None,
        "applied": False,
    }


async def test_change_settings(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Only the given settings go to the cloud, with its names; the answer is kept."""
    client = await _setup(hass, cloud, config_entry, hass_ws_client)
    result = await _call(
        client,
        {
            "type": f"{DOMAIN}/box/settings",
            "box_id": BOX_ID,
            "name": "  Sleeping room ",
            "max_volume": 74,
            "lightring_brightness": 20,
            "skipping_enabled": False,
        },
    )
    assert result["success"], result
    assert cloud.box_patches == [
        (
            BOX_ID,
            {
                "name": "Sleeping room",
                "maxVolume": 74,
                "lightringBrightness": 20,
                "skippingEnabled": False,
            },
        )
    ]
    box = result["result"]
    assert box["name"] == "Sleeping room"
    assert box["settings"]["values"]["max_volume"] == 74
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.data.boxes[BOX_ID].box.settings.lightring_brightness == 20


async def test_change_settings_without_answer_reads_the_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """When the cloud answers a change without the box, the box is read again."""
    client = await _setup(hass, cloud, config_entry, hass_ws_client)
    cloud.main.box_patch_no_body = True
    result = await _call(
        client,
        {"type": f"{DOMAIN}/box/settings", "box_id": CLASSIC_BOX_ID, "led_level": "off"},
    )
    assert result["success"], result
    assert result["result"]["settings"]["values"]["led_level"] == "off"


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ({"box_id": "nobox", "max_volume": 50}, "unknown_box"),
        ({"box_id": BOX_ID, "led_level": "off"}, "not_supported"),
        ({"box_id": CLASSIC_BOX_ID, "lightring_brightness": 10}, "not_supported"),
        ({"box_id": CLASSIC_BOX_ID, "language": "de"}, "not_supported"),
        ({"box_id": BOX_ID}, "invalid_format"),
        ({"box_id": CLASSIC_BOX_ID, "max_volume": 60}, "invalid_value"),
        ({"box_id": BOX_ID, "max_volume": 0}, "invalid_format"),
        ({"box_id": BOX_ID, "lightring_brightness": 101}, "invalid_format"),
        ({"box_id": BOX_ID, "bedtime_max_volume": 0}, "invalid_format"),
        ({"box_id": BOX_ID, "skipping_direction": "up"}, "invalid_format"),
        ({"box_id": BOX_ID, "name": "   "}, "invalid_format"),
        ({"box_id": BOX_ID, "offline_mode": True}, "invalid_format"),
    ],
)
async def test_settings_refusals(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Unknown boxes, settings of another generation, read-only and bad values are refused."""
    client = await _setup(hass, cloud, config_entry, hass_ws_client)
    result = await _call(client, {"type": f"{DOMAIN}/box/settings", **message})
    assert not result["success"]
    assert result["error"]["code"] == code
    assert cloud.box_patches == []


async def test_settings_cloud_error(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A change the cloud refuses comes back as cloud_error."""
    client = await _setup(hass, cloud, config_entry, hass_ws_client)
    cloud.main.rest_status = 400
    result = await _call(
        client, {"type": f"{DOMAIN}/box/settings", "box_id": BOX_ID, "max_volume": 25}
    )
    assert result["error"]["code"] == "cloud_error"


async def test_settings_need_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_admin_user: Any,
) -> None:
    """Somebody who is no administrator changes no setting."""
    client = await _setup(hass, cloud, config_entry, hass_ws_client)
    hass_admin_user.groups = []
    result = await _call(
        client, {"type": f"{DOMAIN}/box/settings", "box_id": BOX_ID, "max_volume": 25}
    )
    assert result["error"]["code"] == "unauthorized"
    assert cloud.box_patches == []
