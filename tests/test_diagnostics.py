"""Diagnostics: what helps with a problem, and nothing personal."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import re

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.const import CONF_ANALYTICS
from custom_components.storybox_plus.diagnostics import async_get_config_entry_diagnostics

from .conftest import (
    BOX_NAME,
    CLASSIC_BOX_NAME,
    CREATIVE_NAME,
    DISC_NAME,
    EMAIL,
    HOUSEHOLD_NAME,
    MAC,
    PASSWORD,
    TONIE_NAME,
    TONIE_SERIES,
    USER_ID,
    FakeCloud,
    PushChannels,
    entry_for,
)


async def test_diagnostics_hold_nothing_personal(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """No tokens, account ID, addresses, names, pictures or timestamps; only counts and states."""
    channel = push.last
    channel.connect()
    channel.battery(80, "charging")
    channel.volume(7)
    channel.sleep_timer("on", until=datetime(2026, 11, 4, 20, 0, tzinfo=UTC))
    channel.playback(chapter=1)

    diag = await async_get_config_entry_diagnostics(hass, setup_entry)
    text = json.dumps(diag)

    for secret in (
        cloud.main.refresh_token,
        "refresh-main",
        "access-main",
        USER_ID,
        PASSWORD,
        EMAIL,
        MAC,
        MAC.lower(),
        "a1:b2:c3",
        HOUSEHOLD_NAME,
        BOX_NAME,
        CLASSIC_BOX_NAME,
        TONIE_NAME,
        TONIE_SERIES,
        CREATIVE_NAME,
        DISC_NAME,
        "img.example.com",
        "t1",
    ):
        assert secret not in text, secret
    assert not re.search(r"\d{4}-\d{2}-\d{2}", text)

    assert diag["entry"] == {"refresh_token": "**REDACTED**", "user_id": "**REDACTED**"}
    assert diag["options"] == {}
    assert diag["tokens"]["offline_token"] is True
    assert diag["tokens"]["refresh_expires_in_s"] is None
    assert 0 < diag["tokens"]["access_expires_in_s"] <= 300
    assert diag["tokens"]["scope"] == "openid offline_access"
    assert diag["push_connected"] is True
    assert diag["polled_at_age_s"] == 0
    assert diag["households"] == 1
    assert diag["tonies"] == {"content": 1, "creative": 1, "disc": 1}
    assert diag["analytics"] == {"days": 0, "first_day": None, "total_seconds": 0}
    tb2, classic = diag["boxes"]
    assert tb2 == {
        "generation": "toniebox_2",
        "raw_generation": "tb2g2",
        "firmware": "1.2.3",
        "has_mac": True,
        "online": True,
        "battery_percent": 80,
        "battery_status": "charging",
        "charging": True,
        "volume_level": 7,
        "features": ["tngSettings", "bedtime", "volumeLimit", "sleepTimerAlarm"],
        "has_timezone": True,
        "schedules": 0,
        "sleep_timer": {"state": "on", "alarm": False},
        "figure_placed": True,
        "playing": True,
        "chapter": 1,
        "last_push_age_s": 0,
    }
    assert classic == {
        "generation": "classic",
        "raw_generation": "classic",
        "firmware": "3.1.0",
        "has_mac": False,
        "online": True,
        "battery_percent": None,
        "battery_status": None,
        "charging": None,
        "volume_level": None,
        "features": ["volumeLimit"],
        "has_timezone": False,
        "schedules": None,
        "sleep_timer": None,
        "figure_placed": False,
        "playing": False,
        "chapter": None,
        "last_push_age_s": None,
    }


async def test_diagnostics_without_counting_and_with_a_session_token(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels
) -> None:
    """Switched-off statistics and an expiring refresh token are shown as such."""
    cloud.main.offline_tokens = False
    entry = entry_for(cloud.main, options={CONF_ANALYTICS: False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["options"] == {CONF_ANALYTICS: False}
    assert diag["analytics"] is None
    assert diag["tokens"]["offline_token"] is False
    assert 1700 < diag["tokens"]["refresh_expires_in_s"] <= 1800
    assert diag["tokens"]["scope"] == "openid"
    assert diag["push_connected"] is False
    assert diag["boxes"][0]["figure_placed"] is True
    assert diag["boxes"][0]["playing"] is False
