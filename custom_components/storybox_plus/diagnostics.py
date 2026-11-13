"""Diagnostics for Storybox Plus.

People attach diagnostics to public issues, so they hold only what helps to
find a problem: no tokens, no account ID, no names of boxes or figures, no
addresses, nothing about what was listened to.
"""

from __future__ import annotations

from collections import Counter
import time
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_REFRESH_TOKEN, CONF_USER_ID
from .coordinator import StoryboxConfigEntry

TO_REDACT = {CONF_REFRESH_TOKEN, CONF_USER_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: StoryboxConfigEntry
) -> dict[str, Any]:
    """Return what helps to understand a problem, and nothing personal."""
    runtime = entry.runtime_data
    data = runtime.coordinator.data
    tokens = runtime.auth.tokens
    now = dt_util.utcnow()
    boxes: list[dict[str, Any]] = []
    if data is not None:
        for box_state in data.boxes.values():
            playback = box_state.playback
            boxes.append(
                {
                    "generation": box_state.box.generation.value,
                    "raw_generation": box_state.box.raw_generation,
                    "firmware": box_state.box.firmware,
                    "has_mac": box_state.box.mac is not None,
                    "online": box_state.online,
                    "battery_percent": box_state.battery.percent if box_state.battery else None,
                    "battery_status": box_state.battery.status if box_state.battery else None,
                    "charging": box_state.battery.charging if box_state.battery else None,
                    "volume_level": box_state.volume.level if box_state.volume else None,
                    "features": list(box_state.box.features),
                    "has_timezone": box_state.box.timezone is not None,
                    "schedules": (
                        None if box_state.schedules is None else len(box_state.schedules)
                    ),
                    "sleep_timer": (
                        {
                            "state": box_state.sleep_timer.state,
                            "alarm": box_state.sleep_timer.alarm,
                        }
                        if box_state.sleep_timer
                        else None
                    ),
                    "figure_placed": box_state.tonie_id is not None,
                    "playing": box_state.playing,
                    "chapter": playback.chapter if playback else None,
                    "last_push_age_s": (
                        int((now - box_state.last_push).total_seconds())
                        if box_state.last_push
                        else None
                    ),
                }
            )
    analytics = runtime.analytics
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "tokens": {
            "access_expires_in_s": int(tokens.access_expires_in()) if tokens else None,
            "refresh_expires_in_s": (
                None
                if tokens is None or tokens.refresh_expires_at is None
                else int(tokens.refresh_expires_at - time.time())
            ),
            "offline_token": tokens is not None and tokens.refresh_expires_at is None,
            "scope": tokens.scope if tokens else None,
        },
        "push_connected": runtime.push.connected,
        "backend_version": runtime.coordinator.backend_version,
        "backend_tested": runtime.coordinator.backend_tested,
        "preferences": runtime.preferences.as_dict(),
        "polled_at_age_s": (
            int((now - data.polled_at).total_seconds()) if data and data.polled_at else None
        ),
        "households": len(data.households) if data else None,
        "tonies": (dict(Counter(t.kind.value for t in data.tonies.values())) if data else None),
        "boxes": boxes,
        "analytics": (
            None
            if analytics is None
            else {
                "days": len(analytics.per_day()),
                "first_day": analytics.first_day.isoformat() if analytics.first_day else None,
                "total_seconds": analytics.total(),
            }
        ),
    }
