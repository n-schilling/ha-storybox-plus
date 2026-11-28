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
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from . import bedtime, fetcher, speech
from .cloud import (
    ALARM_TONES,
    SLEEP_TIMER_MAX_MINUTES,
    VOLUME_LEVELS,
    WEEKDAYS,
    Alarm,
    BedtimeSchedule,
    CloudError,
    Member,
    Tonie,
    TonieKind,
    Tune,
)
from .cloud.models import SETTING_FIELDS
from .const import BUILD_FILE, DOMAIN, TESTED_BACKEND_RELEASE
from .coordinator import (
    BoxError,
    BoxState,
    ChapterError,
    CloudState,
    StoryboxConfigEntry,
    StoryboxCoordinator,
    box_owner,
    setting_supported,
    tonie_owner,
)
from .favourites import MODES as FAVOURITE_MODES
from .fetcher import FetchCancelled, FetcherError, FetcherUnavailable
from .ids import box_unique_id
from .log import LEVELS, MAX_DAYS, async_get_log
from .night import NightMode
from .preferences import ANALYTICS_DAYS, FETCH_MAX_MB, PRESENCE_DOMAINS, PRESENCE_LAG
from .repeat import MODES

_LOGGER = logging.getLogger(__name__)

DATA_WEBSOCKET: HassKey[bool] = HassKey(f"{DOMAIN}_websocket")
DATA_ABOUT: HassKey[dict[str, str | None]] = HassKey(f"{DOMAIN}_about")

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
    "not_creative": "Only creative figures can be changed here",
    "unknown_chapter": "The chapter list names chapters the figure does not have",
    "unknown_file": "The uploaded file is not there any more",
    "empty_file": "The uploaded file is empty",
    "fetcher_missing": "The Media Fetcher app is not installed or not running",
    "speech_missing": "No voice for texts is set up in Home Assistant",
    "invalid_url": "Only web links (http or https) can be fetched",
    "not_lockable": "Only bought figures and discs are locked to a household",
    "unknown_tune": "The account has no such Tune",
    "unsuitable_tune": "The Tune does not fit this figure",
    "no_tune": "No Tune lies on this figure",
    "tune_on": "A Tune lies on the figure; take it off first",
    "tune_not_changed": "The cloud took the Tune change but does not show it yet",
    "chapter_missing": "The cloud answered, but the chapter is not on the figure",
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
    async_register_command(hass, websocket_add_text)
    async_register_command(hass, websocket_refresh_figure)
    async_register_command(hass, websocket_set_favourites)
    async_register_command(hass, websocket_star)
    async_register_command(hass, websocket_box_favourites)
    async_register_command(hass, websocket_cloud_check)
    async_register_command(hass, websocket_update_figure)
    async_register_command(hass, websocket_figure_volume)
    async_register_command(hass, websocket_figure_lock)
    async_register_command(hass, websocket_figure_tune)
    async_register_command(hass, websocket_shuffle_on_swap)
    async_register_command(hass, websocket_preferences)
    async_register_command(hass, websocket_box_repeat)
    async_register_command(hass, websocket_log)
    async_register_command(hass, websocket_log_set)
    async_register_command(hass, websocket_rename_household)
    async_register_command(hass, websocket_box_command)
    async_register_command(hass, websocket_redeem_voucher)
    async_register_command(hass, websocket_redeem_token)
    async_register_command(hass, websocket_save_schedule)
    async_register_command(hass, websocket_delete_schedule)
    async_register_command(hass, websocket_set_wake_up_light)
    async_register_command(hass, websocket_clear_wake_up_light)
    async_register_command(hass, websocket_box_settings)
    async_register_command(hass, websocket_night_mode)


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
    tonie: Tonie,
    on_box: str | None,
    favourites: dict[str, Any] | None = None,
    volume: int | None = None,
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
        "live": tonie.live,
        "on_box": on_box,
        "favourites": favourites,
        "volume": volume,
    }


def _tune_dict(tune: Tune, coordinator: StoryboxCoordinator) -> dict[str, Any]:
    return {
        "id": tune.id,
        "title": tune.title,
        "image_url": tune.image_url,
        "series": tune.series,
        "seconds": tune.seconds,
        "remaining": tune.remaining,
        "assigned": list(tune.assigned),
        "suitable": coordinator.tune_fits(tune),
    }


def _figure_answer(coordinator: StoryboxCoordinator, tonie: Tonie) -> dict[str, Any]:
    """A changed creative figure as the page shows it, with its volume and shuffling."""
    return {
        **_tonie_dict(
            tonie,
            _on_box(coordinator.data, tonie.id),
            coordinator.stars(tonie.id).describe(tonie),
            coordinator.volumes.get(tonie.id),
        ),
        "shuffle_on_swap": coordinator.shuffles.enabled(tonie.id),
    }


def _chapter_list(
    tonie: Tonie | None, favourites: tuple[int, ...] | None = ()
) -> list[dict[str, Any]]:
    """The chapters by name and length; favourites None: which have a star is not known."""
    return (
        [
            {
                "title": c.title or None,
                "seconds": c.seconds,
                "favourite": None if favourites is None else i in favourites,
            }
            for i, c in enumerate(tonie.chapters)
        ]
        if tonie
        else []
    )


def _box_favourites(
    coordinator: StoryboxCoordinator, box_state: BoxState, tonie: Tonie | None
) -> dict[str, Any] | None:
    """The favourites of the figure on a Toniebox 2 and how they play on it now."""
    chapters = coordinator.playing_stars(tonie)
    if tonie is None or chapters is None or not box_state.box.live:
        return None
    suspended = coordinator.runs(box_state.box.id).suspended(box_state.box.id, tonie.id)
    plan = coordinator.favourite_plan(box_state, tonie.id)
    return {
        "chapters": list(chapters),
        # The mode at work ("first", "random", "only"); None while nothing is steered
        "mode": plan.mode if plan and not suspended else None,
        # The mode that would be at work if the figure did not play everything
        "paused_mode": plan.mode if plan and suspended else None,
        "suspended": suspended,
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
            # For the page's chapter list: every chapter by name and length, and its star
            "chapter_list": _chapter_list(tonie, coordinator.playing_stars(tonie)),
            "favourites": _box_favourites(coordinator, box_state, tonie),
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
            "chapter_list": _chapter_list(tonie, coordinator.playing_stars(tonie)),
            "favourites": _box_favourites(coordinator, box_state, tonie),
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
        "image_url": coordinator.box_picture(box),
        "firmware": box.firmware,
        "online": box_state.online,
        # A Toniebox 1 only: the entity its online state and active time come from
        "presence_entity": coordinator.presence_entity(box),
        # The minutes taken off each stretch of its active time
        "presence_lag": None if box.live else entry.runtime_data.preferences.presence_lag(box.id),
        "last_seen": box.last_seen.isoformat() if box.last_seen else None,
        "battery": box_state.battery.percent if box_state.battery else None,
        "charging": box_state.battery.charging if box_state.battery else None,
        "volume": box_state.volume.level if box_state.volume else None,
        "volume_max": VOLUME_LEVELS,
        "volume_percent": box_state.volume.percent if box_state.volume else None,
        "headphones": (
            {
                "connected": box_state.headphones.connected,
                "kind": box_state.headphones.kind,
                "battery": box_state.headphones.battery,
            }
            if box_state.headphones and box_state.online is not False
            else None
        ),
        "sleep_timer": (
            {
                "state": box_state.sleep_timer.state,
                "alarm": box_state.sleep_timer.alarm,
                "until": (
                    box_state.sleep_timer.until.isoformat() if box_state.sleep_timer.until else None
                ),
            }
            if box_state.sleep_timer
            else None
        ),
        "playback": playback,
        # A Toniebox 2 only: the figure on it repeats ("all") or one chapter of it ("one")
        "repeat": coordinator.repeat_mode(box.id),
        "battery_stats": coordinator.battery_stats.summary(box.id) if box.live else None,
        # How long the battery lasts from now, by the past charges; not while charging
        "battery_remaining_hours": (
            coordinator.battery_stats.remaining_hours(box.id, box_state.battery.percent)
            if box.live
            and box_state.battery is not None
            and not box_state.battery.charging
            and box_state.online is not False
            else None
        ),
        "bedtime": _bedtime_dict(coordinator, box_state),
        "settings": _settings_dict(box_state),
        "night": _night_dict(coordinator, box_state),
        "entities": _box_entities(entry, coordinator, box_state),
    }


def _box_entities(
    entry: StoryboxConfigEntry, coordinator: StoryboxCoordinator, box_state: BoxState
) -> dict[str, str | None]:
    """The entity IDs automations need of a box: its media player, figure event and battery."""
    registry = er.async_get(coordinator.hass)
    box_id = box_state.box.id
    return {
        "player": registry.async_get_entity_id(
            "media_player", DOMAIN, box_unique_id(entry, box_id)
        ),
        "figure": registry.async_get_entity_id(
            "event", DOMAIN, box_unique_id(entry, box_id, "figure")
        ),
        "battery": registry.async_get_entity_id(
            "sensor", DOMAIN, box_unique_id(entry, box_id, "battery")
        ),
    }


def _night_dict(coordinator: StoryboxCoordinator, box_state: BoxState) -> dict[str, Any] | None:
    """The night mode of a Toniebox 2's light ring and the phase it is in now."""
    if not box_state.box.live:
        return None
    mode = coordinator.night_modes.get(box_state.box.id)
    return {
        "mode": mode.as_dict() if mode else None,
        "phase": coordinator.night_phase(box_state),
    }


def _settings_dict(box_state: BoxState) -> dict[str, Any]:
    """The settings the box has and the cloud named, with the read-only state beside them."""
    box = box_state.box
    values = {
        name: getattr(box.settings, name)
        for name in SETTING_FIELDS
        if setting_supported(box, name) and getattr(box.settings, name) is not None
    }
    return {
        "values": values,
        "offline_mode": box.settings.offline_mode,
        "applied": box.settings.settings_applied,
    }


def _schedule_dict(schedule: BedtimeSchedule) -> dict[str, Any]:
    alarm = schedule.alarm
    return {
        "id": schedule.id,
        "name": schedule.name,
        "sleep_time": schedule.sleep_time,
        "wakeup_time": schedule.wakeup_time,
        "days": list(schedule.days),
        "enabled": schedule.enabled,
        "alarm_enabled": schedule.alarm_enabled,
        "alarm_tone": alarm.tone,
        "alarm_volume": alarm.volume,
        "alarm_morning_light": alarm.morning_light,
    }


def _bedtime_dict(coordinator: StoryboxCoordinator, box_state: BoxState) -> dict[str, Any] | None:
    """The schedules of a box that rings alarms, the next wake-up and whether it is armed."""
    if not box_state.box.alarm_capable:
        return None
    schedules = box_state.schedules
    upcoming = coordinator.next_alarm(box_state)
    light = coordinator.wake_up_light(box_state.box.id)
    return {
        # None: the schedules could not be read yet
        "schedules": None if schedules is None else [_schedule_dict(s) for s in schedules],
        "wake_up_light": (
            {
                # The box's own time, as the page shows and takes it
                "at": light.at.astimezone(coordinator.now_at(box_state.box).tzinfo).isoformat(),
                "tone": light.alarm.tone,
                "volume": light.alarm.volume,
                "morning_light": light.alarm.morning_light,
            }
            if light
            else None
        ),
        "next_alarm": (
            {
                "at": upcoming.at.isoformat(),
                # None: the wake-up light
                "schedule_id": upcoming.schedule.id if upcoming.schedule else None,
                "armed": bedtime.armed_for(box_state.sleep_timer, upcoming.at),
                "due": coordinator.due_alarm(box_state.box.id) is not None,
            }
            if upcoming
            else None
        ),
    }


async def _about(hass: HomeAssistant) -> dict[str, str | None]:
    """The version the page shows at its bottom, and the commit of a test deployment.

    The version is the manifest's; only scripts/deploy.sh writes a commit,
    so a release shows none.
    """
    if (about := hass.data.get(DATA_ABOUT)) is None:
        integration = await async_get_integration(hass, DOMAIN)
        commit = await hass.async_add_executor_job(_read_commit)
        about = hass.data[DATA_ABOUT] = {"version": str(integration.version), "commit": commit}
    return about


def _read_commit() -> str | None:
    try:
        return (Path(__file__).parent / BUILD_FILE).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _member_dict(member: Member) -> dict[str, Any]:
    return {
        "id": member.id,
        "name": member.display_name,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "email": member.email,
        "role": member.role,
        "self": member.is_self,
    }


def _entry_extras(entry: StoryboxConfigEntry) -> dict[str, Any]:
    """The page's settings of an account and the version its cloud runs."""
    coordinator = entry.runtime_data.coordinator
    return {
        "households": [
            {
                "id": h.id,
                "name": h.name,
                "members": (
                    None
                    if h.id not in coordinator.members
                    else [_member_dict(m) for m in coordinator.members[h.id]]
                ),
            }
            for h in coordinator.data.households.values()
        ],
        "preferences": entry.runtime_data.preferences.as_dict(),
        # The voice that speaks texts while none is chosen: Piper, if it is set up
        "speech_auto": speech.find_piper(coordinator.hass),
        "cloud": {
            "version": coordinator.backend_version,
            "release": coordinator.backend_release,
            "tested": TESTED_BACKEND_RELEASE,
            "matches": coordinator.backend_tested,
            # What the last check of the interface found, and against which release
            "check": entry.runtime_data.preferences.cloud_check,
        },
    }


@require_admin
@websocket_command({probatio.Required("type"): f"{DOMAIN}/overview"})
@async_response
async def websocket_overview(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the accounts and their boxes with the live state, and the version for the page."""
    all_entries: list[StoryboxConfigEntry] = hass.config_entries.async_entries(DOMAIN)
    boxes: list[dict[str, Any]] = []
    push_connected = False
    for entry in _loaded_entries(hass):
        coordinator = entry.runtime_data.coordinator
        push_connected = push_connected or coordinator.data.push_connected
        # A box shared by two accounts of one household shows once
        boxes.extend(
            _box_dict(entry, coordinator, b)
            for b in coordinator.data.boxes.values()
            if box_owner(hass, b.box.id) is entry
        )
    connection.send_result(
        msg["id"],
        {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "title": e.title,
                    "loaded": e.state is ConfigEntryState.LOADED,
                    **(_entry_extras(e) if e.state is ConfigEntryState.LOADED else {}),
                }
                for e in all_entries
            ],
            "push_connected": push_connected,
            "boxes": boxes,
            "about": await _about(hass),
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
    tunes: list[dict[str, Any]] = []
    for entry in _loaded_entries(hass):
        data = entry.runtime_data.coordinator.data
        households.extend(
            {"id": h.id, "name": h.name, "entry_id": entry.entry_id}
            for h in data.households.values()
            if h.id not in {known["id"] for known in households}
        )
        favourites = entry.runtime_data.favourites
        volumes = entry.runtime_data.volumes
        shuffles = entry.runtime_data.shuffles
        tonies.extend(
            {
                **_tonie_dict(t, _on_box(data, t.id), favourites.describe(t), volumes.get(t.id)),
                "shuffle_on_swap": shuffles.enabled(t.id),
            }
            for t in data.tonies.values()
            # A figure of a household shared by two accounts shows once
            if tonie_owner(hass, t.id) is entry
        )
        coordinator = entry.runtime_data.coordinator
        tunes.extend(_tune_dict(t, coordinator) for t in coordinator.tunes or ())
    tonies.sort(key=lambda t: str(t["name"]).lower())
    connection.send_result(
        msg["id"],
        {
            "households": households,
            "tonies": tonies,
            "tunes": tunes,
            # The page offers links only while the Media Fetcher app is there,
            # chapters from text only while the voice of an account can speak
            "fetcher": await fetcher.async_find(hass) is not None,
            "speech": any(
                speech.find_engine(hass, e.runtime_data.preferences.speech_engine) is not None
                for e in _loaded_entries(hass)
            ),
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
        connection.send_result(msg["id"], _figure_answer(coordinator, tonie))


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/chapters/arrange",
        probatio.Required("tonie_id"): str,
        probatio.Required("chapters"): [str],
        probatio.Optional("titles"): {
            str: probatio.All(str, probatio.Strip, probatio.Length(min=1, max=128))
        },
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
        coordinator.async_arrange_chapters(msg["tonie_id"], msg["chapters"], msg.get("titles")),
    )


def content_type(filename: str) -> str:
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
    audio_type = content_type(filename)
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection,
        msg,
        coordinator,
        coordinator.async_add_chapter(msg["tonie_id"], title, data, filename, audio_type),
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/chapters/add_text",
        probatio.Required("tonie_id"): str,
        probatio.Required("text"): probatio.All(
            str, probatio.Strip, probatio.Length(min=1, max=speech.TEXT_MAX)
        ),
        probatio.Optional("title"): probatio.All(str, probatio.Strip, probatio.Length(max=128)),
    }
)
@async_response
async def websocket_add_text(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Let Piper speak a text and append it as a chapter; named after its title or first words."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    text: str = msg["text"]
    title = msg.get("title") or " ".join(text.split()[:6])
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection,
        msg,
        coordinator,
        coordinator.async_add_chapter_from_text(msg["tonie_id"], text, title),
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
        if event.get("stage") == "error":
            _LOGGER.warning(
                "Adding a chapter from a link failed: %s (%s)",
                event.get("message"),
                event.get("code"),
            )
        elif event.get("stage") == "done":
            _LOGGER.info("Adding a chapter from a link is done")
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
            tell({"stage": "done", "figure": _figure_answer(coordinator, tonie)})

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
        # Without them the stars stay as they are and only the mode changes
        probatio.Optional("chapters"): [probatio.All(int, probatio.Range(min=0))],
        # None: the figure follows the mode of the account
        probatio.Required("mode"): probatio.Any(None, probatio.In(list(FAVOURITE_MODES))),
    }
)
@async_response
async def websocket_set_favourites(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Keep the favourite chapters of a figure (from 0) and the mode they play by."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    tonie = coordinator.data.tonies[msg["tonie_id"]]
    known = tonie.chapters or tonie.kind is TonieKind.CREATIVE
    chapters: list[int] | None = msg.get("chapters")
    if known and any(c >= len(tonie.chapters) for c in chapters or ()):
        connection.send_error(msg["id"], "unknown_chapter", _CHAPTER_MESSAGES["unknown_chapter"])
        return
    stars = coordinator.stars(tonie.id)
    if chapters is None:
        await stars.async_set_mode(tonie, msg["mode"])
    else:
        await stars.async_set(tonie, chapters, msg["mode"])
    coordinator.async_update_listeners()
    connection.send_result(msg["id"], {"favourites": stars.describe(tonie)})


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/favourites/star",
        probatio.Required("tonie_id"): str,
        probatio.Required("chapter"): probatio.All(int, probatio.Range(min=0)),
        # Without it the star changes sides
        probatio.Optional("favourite"): bool,
    }
)
@async_response
async def websocket_star(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Mark one chapter of a figure (from 0) as a favourite, or take its star off."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    try:
        await coordinator.async_star(msg["tonie_id"], msg["chapter"], msg.get("favourite"))
    except ChapterError as err:
        connection.send_error(msg["id"], err.code, _chapter_message(err))
        return
    tonie = coordinator.data.tonies[msg["tonie_id"]]
    connection.send_result(msg["id"], {"favourites": coordinator.stars(tonie.id).describe(tonie)})


_BOX_MESSAGES = {
    "unknown_box": "The box is not in any account",
    "no_alarm": "This box has no bedtime schedules",
    "unknown_schedule": "The box has no such bedtime schedule",
    "not_supported": "This box does not have that setting",
    "invalid_value": "A classic box takes 25, 50, 75 or 100 percent",
    "unknown_household": "The account has no such household",
    "alarm_due": "The alarm of a bedtime is due; the sleep timer would cancel it",
    "alarm_too_soon": "That time is less than 5 minutes away",
    "nothing_plays": "No figure is on the box",
    "unknown_chapter": "The figure has no such chapter",
    "invalid_command": "The command needs a value",
    "other_figure": "Another figure is on the box now",
    "tune_plays": "A Tune lies on the figure; the box plays the Tune",
}


def _setting_schema() -> dict[Any, Any]:
    """The values each setting takes, from the cloud layer's table."""
    schema: dict[Any, Any] = {}
    for name, (_api, allowed) in SETTING_FIELDS.items():
        if allowed is bool:
            check: Any = bool
        elif isinstance(allowed[0], str):
            check = probatio.In(allowed)
        else:
            check = probatio.All(int, probatio.Range(min=allowed[0], max=allowed[1]))
        schema[probatio.Optional(name)] = check
    return schema


_PRESENCE_ENTITY = probatio.All(
    str,
    probatio.Length(max=255),
    probatio.Match(rf"^({'|'.join(PRESENCE_DOMAINS)})\.[a-z0-9_]+$"),
)
_CLOCK = probatio.Match(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
# The page's names and the cloud's
_SCHEDULE_FIELDS = {
    "name": "name",
    "sleep_time": "sleepTime",
    "wakeup_time": "wakeupTime",
    "days": "days",
    "enabled": "enabled",
    "alarm_enabled": "alarmEnabled",
    "alarm_tone": "alarmTone",
    "alarm_volume": "alarmVolume",
    "alarm_morning_light": "alarmMorningLight",
}


def _entry_for_box(hass: HomeAssistant, box_id: str) -> StoryboxConfigEntry | None:
    return next(
        (e for e in _loaded_entries(hass) if box_id in e.runtime_data.coordinator.data.boxes),
        None,
    )


async def _answer_with_box(
    connection: ActiveConnection,
    msg: dict[str, Any],
    entry: StoryboxConfigEntry,
    change: Coroutine[Any, Any, BoxState],
) -> None:
    """Run a change to the schedules of a box and answer with the box as it is then."""
    try:
        box_state = await change
    except BoxError as err:
        connection.send_error(msg["id"], err.code, _BOX_MESSAGES[err.code])
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        connection.send_result(
            msg["id"], _box_dict(entry, entry.runtime_data.coordinator, box_state)
        )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/bedtime/save",
        probatio.Required("box_id"): str,
        probatio.Optional("schedule_id"): str,
        probatio.Optional("name"): probatio.All(str, probatio.Length(max=100)),
        probatio.Optional("sleep_time"): _CLOCK,
        probatio.Optional("wakeup_time"): _CLOCK,
        probatio.Optional("days"): [probatio.In(WEEKDAYS)],
        probatio.Optional("enabled"): bool,
        probatio.Optional("alarm_enabled"): bool,
        probatio.Optional("alarm_tone"): probatio.In(ALARM_TONES),
        probatio.Optional("alarm_volume"): probatio.All(int, probatio.Range(min=0, max=100)),
        probatio.Optional("alarm_morning_light"): bool,
    }
)
@async_response
async def websocket_save_schedule(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Create a bedtime schedule of a box, or change the given fields of one.

    A new schedule needs its times and days; the alarm is armed by the
    integration as soon as the schedule asks for one.
    """
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    fields = {cloud: msg[page] for page, cloud in _SCHEDULE_FIELDS.items() if page in msg}
    if "days" in fields:
        # In the order of the week, each day once
        fields["days"] = [d for d in WEEKDAYS if d in fields["days"]]
    schedule_id: str | None = msg.get("schedule_id")
    if schedule_id is None:
        missing = [f for f in ("sleep_time", "wakeup_time", "days") if not msg.get(f)]
        if missing:
            connection.send_error(
                msg["id"], "invalid_format", f"A new schedule needs {', '.join(missing)}"
            )
            return
        fields.setdefault("name", "")
        fields.setdefault("enabled", True)
        fields.setdefault("alarmEnabled", False)
    coordinator = entry.runtime_data.coordinator
    await _answer_with_box(
        connection,
        msg,
        entry,
        coordinator.async_save_schedule(msg["box_id"], schedule_id, fields),
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/box/settings",
        probatio.Required("box_id"): str,
        probatio.Optional("name"): probatio.All(
            str, probatio.Strip, probatio.Length(min=1, max=100)
        ),
        probatio.Optional("presence_entity"): probatio.Any(None, _PRESENCE_ENTITY),
        probatio.Optional("presence_lag"): probatio.All(
            int, probatio.Range(min=PRESENCE_LAG[0], max=PRESENCE_LAG[1])
        ),
        **_setting_schema(),
    }
)
@async_response
async def websocket_box_settings(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change the name or settings of a box; only the given ones are sent to the cloud."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    changes = {k: v for k, v in msg.items() if k == "name" or k in SETTING_FIELDS}
    presence = "presence_entity" in msg
    lag = "presence_lag" in msg
    if not changes and not presence and not lag:
        connection.send_error(msg["id"], "invalid_format", "Nothing to change")
        return
    coordinator = entry.runtime_data.coordinator

    async def _change() -> BoxState:
        # The entity is kept in Home Assistant only; the cloud hears of the rest
        box_state = coordinator.data.boxes[msg["box_id"]]
        if presence:
            box_state = await coordinator.async_set_presence(msg["box_id"], msg["presence_entity"])
        if lag:
            box_state = await coordinator.async_set_presence_lag(msg["box_id"], msg["presence_lag"])
        if changes:
            box_state = await coordinator.async_change_settings(msg["box_id"], changes)
        return box_state

    await _answer_with_box(connection, msg, entry, _change())


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/night/set",
        probatio.Required("box_id"): str,
        probatio.Required("enabled"): bool,
        probatio.Required("start"): _CLOCK,
        probatio.Required("end"): _CLOCK,
        probatio.Required("night"): probatio.All(int, probatio.Range(min=0, max=100)),
        probatio.Required("day"): probatio.All(int, probatio.Range(min=0, max=100)),
    }
)
@async_response
async def websocket_night_mode(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Keep the night mode of a box's light ring; the ring is set as the mode asks now."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    if msg["start"] == msg["end"]:
        connection.send_error(msg["id"], "invalid_format", "Start and end are the same time")
        return
    mode = NightMode(
        enabled=msg["enabled"],
        start=msg["start"],
        end=msg["end"],
        night=msg["night"],
        day=msg["day"],
    )
    coordinator = entry.runtime_data.coordinator
    await _answer_with_box(
        connection, msg, entry, coordinator.async_set_night_mode(msg["box_id"], mode)
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/alarm/set",
        probatio.Required("box_id"): str,
        # The box's own time: "YYYY-MM-DDTHH:MM", as the schedules are local to the box
        probatio.Required("at"): probatio.Match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?$"),
        probatio.Required("tone"): probatio.In(ALARM_TONES),
        probatio.Required("volume"): probatio.All(int, probatio.Range(min=0, max=100)),
        probatio.Required("morning_light"): bool,
    }
)
@async_response
async def websocket_set_wake_up_light(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Set the wake-up light of a box: one alarm at a time of its own."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    coordinator = entry.runtime_data.coordinator
    box = coordinator.data.boxes[msg["box_id"]].box
    local = dt_util.parse_datetime(msg["at"])
    if local is None:
        connection.send_error(msg["id"], "invalid_format", "No valid time")
        return
    at = local.replace(tzinfo=coordinator.now_at(box).tzinfo)
    alarm = Alarm(msg["tone"], msg["volume"], msg["morning_light"])
    await _answer_with_box(
        connection, msg, entry, coordinator.async_set_wake_up_light(box.id, at, alarm)
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/alarm/clear",
        probatio.Required("box_id"): str,
    }
)
@async_response
async def websocket_clear_wake_up_light(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Drop the wake-up light of a box."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    coordinator = entry.runtime_data.coordinator
    await _answer_with_box(
        connection, msg, entry, coordinator.async_clear_wake_up_light(msg["box_id"])
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/bedtime/delete",
        probatio.Required("box_id"): str,
        probatio.Required("schedule_id"): str,
    }
)
@async_response
async def websocket_delete_schedule(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a bedtime schedule of a box."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    coordinator = entry.runtime_data.coordinator
    await _answer_with_box(
        connection,
        msg,
        entry,
        coordinator.async_delete_schedule(msg["box_id"], msg["schedule_id"]),
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/figure/volume",
        probatio.Required("tonie_id"): str,
        probatio.Required("level"): probatio.Any(
            None, probatio.All(int, probatio.Range(min=1, max=VOLUME_LEVELS))
        ),
    }
)
@async_response
async def websocket_figure_volume(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Keep the volume level of a figure (None: the box's own volume)."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    await entry.runtime_data.coordinator.async_set_figure_volume(msg["tonie_id"], msg["level"])
    connection.send_result(msg["id"], {"volume": entry.runtime_data.volumes.get(msg["tonie_id"])})


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/figure/lock",
        probatio.Required("tonie_id"): str,
        probatio.Required("locked"): bool,
    }
)
@async_response
async def websocket_figure_lock(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Lock a bought figure or disc to the household, or unlock it for good."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    try:
        tonie = await entry.runtime_data.coordinator.async_set_lock(msg["tonie_id"], msg["locked"])
    except ChapterError as err:
        connection.send_error(msg["id"], err.code, _chapter_message(err))
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        connection.send_result(msg["id"], {"locked": tonie.locked})


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/figure/shuffle_on_swap",
        probatio.Required("tonie_id"): str,
        probatio.Required("enabled"): bool,
    }
)
@async_response
async def websocket_shuffle_on_swap(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Shuffle a creative figure whenever another figure replaces it on a Toniebox 2."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    tonie = entry.runtime_data.coordinator.data.tonies[msg["tonie_id"]]
    if tonie.kind is not TonieKind.CREATIVE:
        connection.send_error(msg["id"], "not_creative", _CHAPTER_MESSAGES["not_creative"])
        return
    shuffles = entry.runtime_data.shuffles
    await shuffles.async_set(msg["tonie_id"], msg["enabled"])
    connection.send_result(msg["id"], {"shuffle_on_swap": shuffles.enabled(msg["tonie_id"])})


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/figure/tune",
        probatio.Required("tonie_id"): str,
        probatio.Required("tune_id"): probatio.Any(None, str),
    }
)
@async_response
async def websocket_figure_tune(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Lay a bought Tune on a figure, or take it off (tune_id null); answers with the Tunes."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    try:
        await coordinator.async_set_tune(msg["tonie_id"], msg["tune_id"])
    except ChapterError as err:
        connection.send_error(msg["id"], err.code, _chapter_message(err))
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        tonie = coordinator.data.tonies.get(msg["tonie_id"])
        connection.send_result(
            msg["id"],
            {
                "tunes": [_tune_dict(t, coordinator) for t in coordinator.tunes or ()],
                "figure": _figure_answer(coordinator, tonie) if tonie else None,
            },
        )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/voucher/redeem",
        probatio.Required("entry_id"): str,
        probatio.Required("code"): probatio.All(
            str, probatio.Strip, probatio.Length(min=1, max=100)
        ),
    }
)
@async_response
async def websocket_redeem_voucher(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Redeem a Tunes voucher for an account; answers with how many Tunes it brought."""
    entry = next((e for e in _loaded_entries(hass) if e.entry_id == msg["entry_id"]), None)
    if entry is None:
        connection.send_error(msg["id"], "unknown_entry", "The account is not loaded")
        return
    coordinator = entry.runtime_data.coordinator
    try:
        count = await coordinator.async_redeem_voucher(msg["code"])
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        connection.send_result(
            msg["id"],
            {
                "count": count,
                "tunes": [_tune_dict(t, coordinator) for t in coordinator.tunes or ()],
            },
        )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/figure/redeem_token",
        probatio.Required("tonie_id"): str,
        probatio.Required("token"): probatio.All(
            str, probatio.Strip, probatio.Length(min=1, max=100)
        ),
    }
)
@async_response
async def websocket_redeem_token(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Put the content of a content token on a creative figure; answers with the figure."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection, msg, coordinator, coordinator.async_redeem_token(msg["tonie_id"], msg["token"])
    )


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/box/repeat",
        probatio.Required("box_id"): str,
        probatio.Required("mode"): probatio.Any(None, probatio.In(list(MODES))),
    }
)
@callback
def websocket_box_repeat(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Let the figure on a Toniebox 2 repeat, or one chapter of it, or end the repeat."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    coordinator = entry.runtime_data.coordinator
    try:
        box_state = coordinator.set_repeat(msg["box_id"], msg["mode"])
    except BoxError as err:
        connection.send_error(msg["id"], err.code, _BOX_MESSAGES[err.code])
        return
    connection.send_result(msg["id"], _box_dict(entry, coordinator, box_state))


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/box/favourites",
        probatio.Required("box_id"): str,
        probatio.Required("suspended"): bool,
    }
)
@callback
def websocket_box_favourites(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Let the figure on a Toniebox 2 play everything until it is taken off, or steer it again."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    coordinator = entry.runtime_data.coordinator
    try:
        box_state = coordinator.suspend_favourites(msg["box_id"], msg["suspended"])
    except BoxError as err:
        connection.send_error(msg["id"], err.code, _BOX_MESSAGES[err.code])
        return
    connection.send_result(msg["id"], _box_dict(entry, coordinator, box_state))


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/box/command",
        probatio.Required("box_id"): str,
        probatio.Required("command"): probatio.In(
            ["play", "pause", "next", "previous", "chapter", "volume", "sleep", "sleep_clear"]
        ),
        probatio.Optional("value"): probatio.All(
            int, probatio.Range(min=0, max=SLEEP_TIMER_MAX_MINUTES)
        ),
        # With "chapter": the figure the chapter is meant for; another one on the box refuses it
        probatio.Optional("tonie_id"): str,
    }
)
@async_response
async def websocket_box_command(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Play, pause, skip, change the volume or the sleep timer of a Toniebox 2 from the page."""
    entry = _entry_for_box(hass, msg["box_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_box", _BOX_MESSAGES["unknown_box"])
        return
    value = msg.get("value")
    if msg["command"] == "volume" and value is not None and value > VOLUME_LEVELS:
        connection.send_error(msg["id"], "invalid_format", "The box knows 13 volume levels")
        return
    if msg["command"] == "sleep" and not value:
        connection.send_error(msg["id"], "invalid_command", _BOX_MESSAGES["invalid_command"])
        return
    try:
        await entry.runtime_data.coordinator.async_box_command(
            msg["box_id"], msg["command"], value, msg.get("tonie_id")
        )
    except BoxError as err:
        connection.send_error(msg["id"], err.code, _BOX_MESSAGES[err.code])
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        connection.send_result(msg["id"])


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/household/rename",
        probatio.Required("household_id"): str,
        probatio.Required("name"): probatio.All(
            str, probatio.Strip, probatio.Length(min=1, max=100)
        ),
    }
)
@async_response
async def websocket_rename_household(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Rename a household of an account."""
    entry = next(
        (
            e
            for e in _loaded_entries(hass)
            if msg["household_id"] in e.runtime_data.coordinator.data.households
        ),
        None,
    )
    if entry is None:
        connection.send_error(msg["id"], "unknown_household", _BOX_MESSAGES["unknown_household"])
        return
    try:
        await entry.runtime_data.coordinator.async_rename_household(
            msg["household_id"], msg["name"]
        )
    except BoxError as err:
        connection.send_error(msg["id"], err.code, _BOX_MESSAGES[err.code])
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
    else:
        connection.send_result(msg["id"], {"entry_title": entry.title})


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/preferences/set",
        probatio.Required("entry_id"): str,
        probatio.Optional("auto_lock"): bool,
        probatio.Optional("mark_read"): bool,
        probatio.Optional("analytics"): bool,
        probatio.Optional("analytics_days"): probatio.In(list(ANALYTICS_DAYS)),
        probatio.Optional("speech_engine"): probatio.Any(
            None, probatio.All(str, probatio.Match(r"^tts\.[a-z0-9_]{1,200}$"))
        ),
        probatio.Optional("voice"): probatio.Any(None, probatio.All(str, probatio.Length(max=200))),
        probatio.Optional("voice_language"): probatio.Any(
            None, probatio.All(str, probatio.Length(max=20))
        ),
        probatio.Optional("fetch_max_mb"): probatio.All(
            int, probatio.Range(min=FETCH_MAX_MB[0], max=FETCH_MAX_MB[1])
        ),
        probatio.Optional("favourites_mode"): probatio.In(list(FAVOURITE_MODES)),
    }
)
@async_response
async def websocket_preferences(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change the settings of an account from the page's settings tab."""
    entry = next((e for e in _loaded_entries(hass) if e.entry_id == msg["entry_id"]), None)
    if entry is None:
        connection.send_error(msg["id"], "unknown_entry", "The account is not loaded")
        return
    preferences = entry.runtime_data.preferences
    counting = preferences.analytics
    changes = {k: v for k, v in msg.items() if k not in ("id", "type", "entry_id")}
    try:
        await preferences.async_set(**changes)
    except ValueError:
        connection.send_error(msg["id"], "invalid_format", "A voice needs its language")
        return
    if "favourites_mode" in changes:
        # The boxes show the mode at work
        entry.runtime_data.coordinator.async_update_listeners()
    if "analytics_days" in changes and entry.runtime_data.analytics is not None:
        entry.runtime_data.analytics.set_keep_days(preferences.analytics_days)
    _LOGGER.info("Preferences of %s changed: %s", entry.title, ", ".join(sorted(changes)))
    connection.send_result(msg["id"], preferences.as_dict())
    if preferences.analytics != counting:
        # Counting starts or ends with the entry: it is set up anew
        hass.config_entries.async_schedule_reload(entry.entry_id)


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/cloud/check",
        probatio.Required("entry_id"): str,
    }
)
@async_response
async def websocket_cloud_check(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Compare what the cloud answers with what the integration relies on; reads only."""
    entry = next((e for e in _loaded_entries(hass) if e.entry_id == msg["entry_id"]), None)
    if entry is None:
        connection.send_error(msg["id"], "unknown_entry", "The account is not loaded")
        return
    try:
        report = await entry.runtime_data.coordinator.async_check_cloud()
    except CloudError as err:
        connection.send_error(msg["id"], "cloud_error", str(err))
        return
    connection.send_result(msg["id"], report)


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/log",
        # Without a limit, every line kept on disk (for the download)
        probatio.Optional("limit"): probatio.All(int, probatio.Range(min=1)),
    }
)
@async_response
async def websocket_log(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """The integration's log settings and its latest lines, newest first."""
    log = await async_get_log(hass)
    connection.send_result(msg["id"], await log.async_as_dict(msg.get("limit")))


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/log/set",
        probatio.Optional("level"): probatio.In(list(LEVELS)),
        probatio.Optional("days"): probatio.All(int, probatio.Range(min=0, max=MAX_DAYS)),
    }
)
@async_response
async def websocket_log_set(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change the log level or how many days the lines are kept, now and for the next start."""
    log = await async_get_log(hass)
    await log.async_set(msg.get("level"), msg.get("days"))
    _LOGGER.info("Log level %s, lines kept for %s days", log.level, log.days)
    connection.send_result(msg["id"], await log.async_as_dict(0))


@require_admin
@websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/figure/update",
        probatio.Required("tonie_id"): str,
        probatio.Optional("name"): probatio.All(
            str, probatio.Strip, probatio.Length(min=1, max=100)
        ),
        probatio.Optional("live"): bool,
    }
)
@async_response
async def websocket_update_figure(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change name or live mode of a creative figure; only the given ones are sent."""
    entry = _entry_for_tonie(hass, msg["tonie_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_figure", _CHAPTER_MESSAGES["unknown_figure"])
        return
    fields: dict[str, Any] = {k: msg[k] for k in ("name", "live") if k in msg}
    if not fields:
        connection.send_error(msg["id"], "invalid_format", "Nothing to change")
        return
    coordinator = entry.runtime_data.coordinator
    await _answer_with_figure(
        connection, msg, coordinator, coordinator.async_update_figure(msg["tonie_id"], fields)
    )


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


# A favourite heard for less than this many seconds over the days counts as hardly heard
UNHEARD_SECONDS = 60


def _chapter_title(tonie: Tonie | None, index: int) -> str | None:
    if tonie is None or not 0 <= index < len(tonie.chapters):
        return None
    return tonie.chapters[index].title or None


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
    active_per_box: dict[str, int] = {}
    per_day: dict[str, int] = {}
    placements: dict[str, int] = {}
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
        for box_id, seconds in runtime.analytics.active_per_box(days).items():
            active_per_box[box_id] = active_per_box.get(box_id, 0) + seconds
        for day, seconds in runtime.analytics.per_day(days).items():
            per_day[day] = per_day.get(day, 0) + seconds
        for tonie_id, times in runtime.analytics.placements_per_tonie(days).items():
            placements[tonie_id] = placements.get(tonie_id, 0) + times
    top = sorted(per_tonie.items(), key=lambda item: (-item[1], item[0]))[:limit]
    top_placed = sorted(placements.items(), key=lambda item: (-item[1], item[0]))[:limit]
    per_chapter: dict[tuple[str, int], int] = {}
    heatmap = [[0] * 24 for _ in range(7)]
    heatmap_boxes: list[dict[str, Any]] = []
    previous: int | None = 0 if days else None
    for entry in _loaded_entries(hass):
        analytics = entry.runtime_data.analytics
        if analytics is None:
            continue
        for key, seconds in analytics.per_chapter(days).items():
            per_chapter[key] = per_chapter.get(key, 0) + seconds
        for weekday, hours in enumerate(analytics.per_weekday_hour(days)):
            for hour, seconds in enumerate(hours):
                heatmap[weekday][hour] += seconds
        heatmap_boxes.extend(
            {
                "box_id": box_id,
                "name": box_names.get(box_id),
                "grid": analytics.per_weekday_hour(days, box_id),
            }
            for box_id in sorted(analytics.hour_boxes(days))
        )
        if days and previous is not None:
            before = analytics.total_before(days)
            previous = None if before is None else previous + before
    ranked = sorted(per_chapter.items(), key=lambda item: (-item[1], item[0]))
    top_chapters = ranked[:limit]
    # The favourites over the same days: by the stars as they are now
    starred: set[tuple[str, int]] = set()
    for entry in _loaded_entries(hass):
        coordinator = entry.runtime_data.coordinator
        for tonie in coordinator.data.tonies.values():
            # The stars of a figure are kept by one account, also where several have it
            stars = coordinator.stars(tonie.id).indexes(tonie)
            starred.update((tonie.id, index) for index in stars)

    def chapter_row(tonie_id: str, index: int, seconds: int) -> dict[str, Any]:
        tonie = names.get(tonie_id)
        length = tonie.chapters[index].seconds if tonie and index < len(tonie.chapters) else None
        return {
            "tonie_id": tonie_id,
            "name": tonie.name if tonie else None,
            "image_url": tonie.image_url if tonie else None,
            "chapter": index,
            "title": _chapter_title(tonie, index),
            "seconds": seconds,
            # How often the chapter ran through, where its length is known
            "plays": round(seconds / length, 1) if length else None,
        }

    def exists(tonie_id: str, index: int) -> bool:
        tonie = names.get(tonie_id)
        return tonie is not None and (not tonie.chapters or index < len(tonie.chapters))

    counted = sum(per_chapter.values())
    on_favourites = sum(s for key, s in per_chapter.items() if key in starred)
    with_stars = {tonie_id for tonie_id, _ in starred}
    share_per_tonie: dict[str, list[int]] = {}
    for (tonie_id, index), seconds in per_chapter.items():
        if tonie_id in with_stars:
            sums = share_per_tonie.setdefault(tonie_id, [0, 0])
            sums[0] += seconds
            sums[1] += seconds if (tonie_id, index) in starred else 0
    unheard = sorted(
        (
            (per_chapter.get(key, 0), key)
            for key in starred
            # A figure nobody listened to in these days says nothing about its stars
            if key[0] in share_per_tonie and per_chapter.get(key, 0) < UNHEARD_SECONDS
        ),
        key=lambda item: (item[0], item[1]),
    )
    favourite_stats = {
        "count": len(starred),
        "seconds": on_favourites,
        # Of the listening time whose chapter is known
        "counted_seconds": counted,
        "share": round(on_favourites / counted, 3) if counted and starred else None,
        "per_tonie": [
            {
                "tonie_id": tonie_id,
                "name": names[tonie_id].name if tonie_id in names else None,
                "image_url": names[tonie_id].image_url if tonie_id in names else None,
                "seconds": sums[0],
                "favourite_seconds": sums[1],
                "share": round(sums[1] / sums[0], 3) if sums[0] else None,
            }
            for tonie_id, sums in sorted(
                share_per_tonie.items(), key=lambda item: (-item[1][0], item[0])
            )[:limit]
        ],
        # The chapters heard most that have no star: favourites nobody marked yet
        "hidden": [
            chapter_row(tonie_id, index, seconds)
            for (tonie_id, index), seconds in [
                item for item in ranked if item[0] not in starred and exists(*item[0])
            ][:limit]
        ],
        # Stars on chapters that were hardly heard, of figures that were listened to in these days
        "unheard": [
            chapter_row(tonie_id, index, seconds) for seconds, (tonie_id, index) in unheard[:limit]
        ],
    }
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
            "top_placed": [
                {
                    "tonie_id": tonie_id,
                    "name": names[tonie_id].name if tonie_id in names else None,
                    "image_url": names[tonie_id].image_url if tonie_id in names else None,
                    "kind": names[tonie_id].kind.value if tonie_id in names else None,
                    "times": times,
                }
                for tonie_id, times in top_placed
            ],
            "top_chapters": [
                {
                    "tonie_id": tonie_id,
                    "name": names[tonie_id].name if tonie_id in names else None,
                    "image_url": names[tonie_id].image_url if tonie_id in names else None,
                    "chapter": index,
                    "title": _chapter_title(names.get(tonie_id), index),
                    "seconds": seconds,
                }
                for (tonie_id, index), seconds in top_chapters
            ],
            "favourites": favourite_stats if enabled else None,
            # Monday first, 24 hours each; all boxes, and each box on its own
            "heatmap": heatmap,
            "heatmap_boxes": heatmap_boxes,
            # The window of the same length right before, while it was counted in full
            "previous_total_seconds": previous if enabled else None,
            "per_day": [{"day": d, "seconds": s} for d, s in sorted(per_day.items())],
            "per_box": [
                {"box_id": b, "name": box_names.get(b), "seconds": s}
                for b, s in sorted(per_box.items(), key=lambda item: -item[1])
            ],
            # How long each Toniebox 1 was in the network: an indication, no listening time
            "active_per_box": [
                {"box_id": b, "name": box_names.get(b), "seconds": s}
                for b, s in sorted(active_per_box.items(), key=lambda item: -item[1])
            ],
        },
    )
