"""The WebSocket commands of the page.

For administrators only: the page shows the whole account, the figures and
the listening statistics.
"""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import require_admin, websocket_command
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .cloud import VOLUME_LEVELS, Tonie
from .const import DOMAIN
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator

DATA_WEBSOCKET: HassKey[bool] = HassKey(f"{DOMAIN}_websocket")


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the commands once per run of Home Assistant."""
    if DATA_WEBSOCKET in hass.data:
        return
    hass.data[DATA_WEBSOCKET] = True
    async_register_command(hass, websocket_overview)
    async_register_command(hass, websocket_library)
    async_register_command(hass, websocket_analytics)


def _loaded_entries(hass: HomeAssistant) -> list[StoryboxConfigEntry]:
    entries: list[StoryboxConfigEntry] = hass.config_entries.async_entries(DOMAIN)
    return [e for e in entries if e.state is ConfigEntryState.LOADED]


def _tonie_dict(tonie: Tonie, on_box: str | None) -> dict[str, Any]:
    return {
        "id": tonie.id,
        "household_id": tonie.household_id,
        "kind": tonie.kind.value,
        "name": tonie.name,
        "series": tonie.series,
        "image_url": tonie.image_url,
        "language": tonie.language,
        "locked": tonie.locked,
        "seconds": tonie.seconds,
        "chapters": [
            {"id": c.id, "title": c.title, "seconds": c.seconds, "transcoding": c.transcoding}
            for c in tonie.chapters
        ],
        "seconds_remaining": tonie.seconds_remaining,
        "chapters_remaining": tonie.chapters_remaining,
        "transcoding": tonie.transcoding,
        "on_box": on_box,
    }


def _box_dict(
    entry: StoryboxConfigEntry, coordinator: StoryboxCoordinator, box_state: BoxState
) -> dict[str, Any]:
    box = box_state.box
    playback: dict[str, Any] | None = None
    if box_state.playback is not None and box_state.playback.tonie_id is not None:
        play = box_state.playback
        tonie = coordinator.tonie(play.tonie_id)
        chapter_title = None
        if tonie and play.chapter is not None and 0 <= play.chapter < len(tonie.chapters):
            chapter_title = tonie.chapters[play.chapter].title
        playback = {
            "tonie_id": play.tonie_id,
            "tonie_name": tonie.name if tonie else None,
            "image_url": tonie.image_url if tonie else None,
            "chapter": play.chapter,
            "chapter_title": chapter_title,
            "chapters": len(tonie.chapters) if tonie else None,
            "playing": play.playing,
            "paused": play.paused,
            "ended": play.ended,
            "position": play.position,
            "duration": play.duration,
            "received_at": play.received_at.isoformat(),
        }
    elif box.placed_tonie_id is not None and box_state.playback is None:
        tonie = coordinator.tonie(box.placed_tonie_id)
        playback = {
            "tonie_id": box.placed_tonie_id,
            "tonie_name": tonie.name if tonie else None,
            "image_url": tonie.image_url if tonie else None,
            "chapter": None,
            "chapter_title": None,
            "chapters": len(tonie.chapters) if tonie else None,
            "playing": False,
            "paused": None,
            "ended": None,
            "position": None,
            "duration": None,
            "received_at": None,
        }
    household = coordinator.data.households.get(box.household_id)
    return {
        "id": box.id,
        "entry_id": entry.entry_id,
        "name": box.name,
        "household": household.name if household else None,
        "generation": box.generation.value,
        "firmware": box.firmware,
        "online": box_state.online,
        "last_seen": box.last_seen.isoformat() if box.last_seen else None,
        "battery": box_state.battery.percent if box_state.battery else None,
        "charging": box_state.battery.charging if box_state.battery else None,
        "volume": box_state.volume.level if box_state.volume else None,
        "volume_max": VOLUME_LEVELS,
        "sleep_timer": (
            {
                "state": box_state.sleep_timer.state,
                "until": (
                    box_state.sleep_timer.until.isoformat() if box_state.sleep_timer.until else None
                ),
            }
            if box_state.sleep_timer
            else None
        ),
        "playback": playback,
        "battery_stats": coordinator.battery_stats.summary(box.id) if box.live else None,
    }


@require_admin
@websocket_command({probatio.Required("type"): f"{DOMAIN}/overview"})
@callback
def websocket_overview(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the accounts and their boxes with the live state."""
    all_entries: list[StoryboxConfigEntry] = hass.config_entries.async_entries(DOMAIN)
    boxes: list[dict[str, Any]] = []
    push_connected = False
    for entry in _loaded_entries(hass):
        coordinator = entry.runtime_data.coordinator
        push_connected = push_connected or coordinator.data.push_connected
        boxes.extend(_box_dict(entry, coordinator, b) for b in coordinator.data.boxes.values())
    connection.send_result(
        msg["id"],
        {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "title": e.title,
                    "loaded": e.state is ConfigEntryState.LOADED,
                }
                for e in all_entries
            ],
            "push_connected": push_connected,
            "boxes": boxes,
        },
    )


@require_admin
@websocket_command({probatio.Required("type"): f"{DOMAIN}/library"})
@callback
def websocket_library(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the households and figures of all accounts."""
    households: list[dict[str, Any]] = []
    tonies: list[dict[str, Any]] = []
    for entry in _loaded_entries(hass):
        data = entry.runtime_data.coordinator.data
        on_box = {b.tonie_id: b.box.id for b in data.boxes.values() if b.tonie_id}
        households.extend(
            {"id": h.id, "name": h.name, "entry_id": entry.entry_id}
            for h in data.households.values()
        )
        tonies.extend(_tonie_dict(t, on_box.get(t.id)) for t in data.tonies.values())
    tonies.sort(key=lambda t: str(t["name"]).lower())
    connection.send_result(msg["id"], {"households": households, "tonies": tonies})


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/analytics",
        probatio.Optional("days"): probatio.Any(
            None, probatio.All(int, probatio.Range(min=1, max=3660))
        ),
        probatio.Optional("limit", default=10): probatio.All(int, probatio.Range(min=1, max=100)),
    }
)
@callback
def websocket_analytics(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the listening statistics over the last days (None: since the setup)."""
    days: int | None = msg.get("days")
    limit: int = msg["limit"]
    enabled = False
    first_day: str | None = None
    per_tonie: dict[str, int] = {}
    per_box: dict[str, int] = {}
    per_day: dict[str, int] = {}
    names: dict[str, Any] = {}
    box_names: dict[str, str] = {}
    for entry in _loaded_entries(hass):
        runtime = entry.runtime_data
        data = runtime.coordinator.data
        names.update({t.id: t for t in data.tonies.values()})
        box_names.update({b.box.id: b.box.name for b in data.boxes.values()})
        if runtime.analytics is None:
            continue
        enabled = True
        if runtime.analytics.first_day and (
            first_day is None or runtime.analytics.first_day.isoformat() < first_day
        ):
            first_day = runtime.analytics.first_day.isoformat()
        for tonie_id, seconds in runtime.analytics.per_tonie(days).items():
            per_tonie[tonie_id] = per_tonie.get(tonie_id, 0) + seconds
        for box_id, seconds in runtime.analytics.per_box(days).items():
            per_box[box_id] = per_box.get(box_id, 0) + seconds
        for day, seconds in runtime.analytics.per_day(days).items():
            per_day[day] = per_day.get(day, 0) + seconds
    top = sorted(per_tonie.items(), key=lambda item: (-item[1], item[0]))[:limit]
    connection.send_result(
        msg["id"],
        {
            "enabled": enabled,
            "days": days,
            "first_day": first_day,
            "total_seconds": sum(per_day.values()),
            "top": [
                {
                    "tonie_id": tonie_id,
                    "name": names[tonie_id].name if tonie_id in names else None,
                    "image_url": names[tonie_id].image_url if tonie_id in names else None,
                    "kind": names[tonie_id].kind.value if tonie_id in names else None,
                    "seconds": seconds,
                }
                for tonie_id, seconds in top
            ],
            "per_day": [{"day": d, "seconds": s} for d, s in sorted(per_day.items())],
            "per_box": [
                {"box_id": b, "name": box_names.get(b), "seconds": s}
                for b, s in sorted(per_box.items(), key=lambda item: -item[1])
            ],
        },
    )
