"""The WebSocket commands of the page.

For administrators only: the page shows the whole account, the figures and
the listening statistics, and changes the chapters of creative figures.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import logging
import mimetypes
from pathlib import Path
from typing import Any

import probatio

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import (
    async_response,
    require_admin,
    websocket_command,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from . import fetcher
from .cloud import VOLUME_LEVELS, CloudError, Tonie, TonieKind
from .const import DOMAIN
from .coordinator import (
    BoxState,
    ChapterError,
    CloudState,
    StoryboxConfigEntry,
    StoryboxCoordinator,
)
from .favourites import Favourites
from .fetcher import FetchCancelled, FetcherError, FetcherUnavailable

_LOGGER = logging.getLogger(__name__)

DATA_WEBSOCKET: HassKey[bool] = HassKey(f"{DOMAIN}_websocket")

# The content type of an upload by its file ending; the platform's own table
# differs between systems (.m4a alone has three spellings)
_AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".wma": "audio/x-ms-wma",
}

# What the page is told when a chapter change is refused
_CHAPTER_MESSAGES = {
    "unknown_figure": "The figure is not in any account",
    "not_creative": "Only creative figures take chapters",
    "unknown_chapter": "The chapter list names chapters the figure does not have",
    "unknown_file": "The uploaded file is not there any more",
    "empty_file": "The uploaded file is empty",
    "fetcher_missing": "The Media Fetcher app is not installed or not running",
    "invalid_url": "Only web links (http or https) can be fetched",
    "not_bought": "Favourites are for bought figures; the chapters of creative figures are arranged instead",
}


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the commands once per run of Home Assistant."""
    if DATA_WEBSOCKET in hass.data:
        return
    hass.data[DATA_WEBSOCKET] = True
    async_register_command(hass, websocket_overview)
    async_register_command(hass, websocket_library)
    async_register_command(hass, websocket_analytics)
    async_register_command(hass, websocket_arrange_chapters)
    async_register_command(hass, websocket_add_chapter)
    async_register_command(hass, websocket_add_link)
    async_register_command(hass, websocket_refresh_figure)
    async_register_command(hass, websocket_set_favourites)


def _loaded_entries(hass: HomeAssistant) -> list[StoryboxConfigEntry]:
    entries: list[StoryboxConfigEntry] = hass.config_entries.async_entries(DOMAIN)
    return [e for e in entries if e.state is ConfigEntryState.LOADED]


def _entry_for_tonie(hass: HomeAssistant, tonie_id: str) -> StoryboxConfigEntry | None:
    """Return the account that owns the figure."""
    return next(
        (e for e in _loaded_entries(hass) if tonie_id in e.runtime_data.coordinator.data.tonies),
        None,
    )


def _on_box(data: CloudState, tonie_id: str) -> str | None:
    return next((b.box.id for b in data.boxes.values() if b.tonie_id == tonie_id), None)


def _tonie_dict(
    tonie: Tonie, on_box: str | None, favourites: Favourites | None = None
) -> dict[str, Any]:
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
        "transcoding_errors": list(tonie.transcoding_errors),
        "on_box": on_box,
        "favourites": favourites.as_dict() if favourites else None,
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
@async_response
async def websocket_library(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the households and figures of all accounts, and whether links can be fetched."""
    households: list[dict[str, Any]] = []
    tonies: list[dict[str, Any]] = []
    for entry in _loaded_entries(hass):
        data = entry.runtime_data.coordinator.data
        households.extend(
            {"id": h.id, "name": h.name, "entry_id": entry.entry_id}
            for h in data.households.values()
        )
        favourites = entry.runtime_data.favourites
        tonies.extend(
            _tonie_dict(t, _on_box(data, t.id), favourites.get(t.id)) for t in data.tonies.values()
        )
    tonies.sort(key=lambda t: str(t["name"]).lower())
    connection.send_result(
        msg["id"],
        {
            "households": households,
            "tonies": tonies,
            # The page offers links only while the Media Fetcher app is there
            "fetcher": await fetcher.async_find(hass) is not None,
        },
    )


# ---------------------------------------------------------------- chapters


def _chapter_message(err: ChapterError) -> str:
    return err.text or _CHAPTER_MESSAGES.get(err.code, err.code)


async def _answer_with_figure(
    connection: ActiveConnection,
    msg: dict[str, Any],
    coordinator: StoryboxCoordinator,
    change: Coroutine[Any, Any, Tonie],
) -> None:
    """Run a change to a creative figure and answer with the figure as the cloud left it."""
    try:
        tonie = await change
    except ChapterError as err:
        connection.send_error(msg["id"], err.code, _chapter_message(err))
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        connection.send_result(msg["id"], _tonie_dict(tonie, _on_box(coordinator.data, tonie.id)))


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/chapters/arrange",
        probatio.Required("tonie_id"): str,
        probatio.Required("chapters"): [str],
    }
)
@async_response
async def websocket_arrange_chapters(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Keep only the named chapters of a creative figure, in the given order."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection,
        msg,
        coordinator,
        coordinator.async_arrange_chapters(msg["tonie_id"], msg["chapters"]),
    )


def _content_type(filename: str) -> str:
    """Name the audio type of a file by its ending; unknown endings count as MP3."""
    suffix = Path(filename).suffix.lower()
    if suffix in _AUDIO_TYPES:
        return _AUDIO_TYPES[suffix]
    guessed = mimetypes.guess_type(filename)[0]
    return guessed if guessed and guessed.startswith("audio/") else "audio/mpeg"


def _read_upload(hass: HomeAssistant, file_id: str) -> tuple[bytes, str]:
    """Take the file the page uploaded to Home Assistant; it is deleted afterwards."""
    with process_uploaded_file(hass, file_id) as path:
        return path.read_bytes(), path.name


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/chapters/add",
        probatio.Required("tonie_id"): str,
        probatio.Required("file_id"): str,
        probatio.Optional("title"): str,
    }
)
@async_response
async def websocket_add_chapter(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Append a file the page uploaded (through /api/file_upload) as a chapter."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    try:
        data, filename = await hass.async_add_executor_job(_read_upload, hass, msg["file_id"])
    except ValueError:
        connection.send_error(msg["id"], "unknown_file", _CHAPTER_MESSAGES["unknown_file"])
        return
    if not data:
        connection.send_error(msg["id"], "empty_file", _CHAPTER_MESSAGES["empty_file"])
        return
    title = (msg.get("title") or "").strip() or Path(filename).stem or filename
    content_type = _content_type(filename)
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection,
        msg,
        coordinator,
        coordinator.async_add_chapter(msg["tonie_id"], title, data, filename, content_type),
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/chapters/add_link",
        probatio.Required("tonie_id"): str,
        probatio.Required("url"): probatio.All(str, probatio.Length(min=1, max=2048)),
    }
)
@async_response
async def websocket_add_link(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Fetch the audio of a video as a chapter; the page hears the progress as events.

    The command subscribes: the result confirms the subscription, the events
    name the stage ("probe", "download" with the bytes, "convert", "upload")
    and end with "done" and the figure, or "error" with a code and a
    message. The page unsubscribes then; unsubscribing earlier, or losing
    the connection, gives up a running download.
    """
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    msg_id: int = msg["id"]
    cancelled = asyncio.Event()

    @callback
    def tell(event: dict[str, Any]) -> None:
        if msg_id in connection.subscriptions:
            connection.send_event(msg_id, event)

    async def run() -> None:
        try:
            tonie = await coordinator.async_add_chapter_from_link(
                msg["tonie_id"], msg["url"], tell, cancelled
            )
        except ChapterError as err:
            tell({"stage": "error", "code": err.code, "message": _chapter_message(err)})
        except CloudError as err:
            tell({"stage": "error", "code": "cloud_error", "message": str(err)})
        except FetchCancelled:
            _LOGGER.debug("A fetch of a link was given up")
        except asyncio.CancelledError:
            # The entry unloads: the page hears the end before the task goes
            tell({"stage": "error", "code": "unloaded", "message": "Storybox Plus was reloaded"})
            raise
        except FetcherUnavailable as err:
            tell({"stage": "error", "code": "fetcher_unavailable", "message": err.message})
        except FetcherError as err:
            tell({"stage": "error", "code": err.code, "message": err.message})
        except Exception as err:  # The page must hear the end either way
            _LOGGER.exception("Adding a chapter from a link failed")
            tell({"stage": "error", "code": "unknown_error", "message": str(err)})
        else:
            tell(
                {"stage": "done", "figure": _tonie_dict(tonie, _on_box(coordinator.data, tonie.id))}
            )

    @callback
    def stop() -> None:
        cancelled.set()

    connection.subscriptions[msg_id] = stop
    connection.send_result(msg_id)
    # Bound to the entry, so a reload or a removal ends it with the coordinator it uses
    entry.async_create_background_task(hass, run(), f"{DOMAIN} chapter from link")


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/favourites/set",
        probatio.Required("tonie_id"): str,
        probatio.Required("chapters"): [probatio.All(int, probatio.Range(min=0))],
        probatio.Required("active"): bool,
    }
)
@async_response
async def websocket_set_favourites(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Keep the favourite chapters of a bought figure (0-based) and whether they steer the box."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    tonie = entry.runtime_data.coordinator.data.tonies[msg["tonie_id"]]
    if tonie.kind is TonieKind.CREATIVE:
        connection.send_error(msg["id"], "not_bought", _CHAPTER_MESSAGES["not_bought"])
        return
    if tonie.chapters and any(c >= len(tonie.chapters) for c in msg["chapters"]):
        connection.send_error(msg["id"], "unknown_chapter", _CHAPTER_MESSAGES["unknown_chapter"])
        return
    favourites = await entry.runtime_data.favourites.async_set(
        msg["tonie_id"], msg["chapters"], msg["active"]
    )
    connection.send_result(msg["id"], {"favourites": favourites.as_dict() if favourites else None})


@require_admin
@websocket_command(
    {probatio.Required("type"): f"{DOMAIN}/figure/refresh", probatio.Required("tonie_id"): str}
)
@async_response
async def websocket_refresh_figure(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Read one creative figure from the cloud again, while it converts the chapters."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection, msg, coordinator, coordinator.async_refresh_creative(msg["tonie_id"])
    )


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
