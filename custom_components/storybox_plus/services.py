"""Actions for automations: chapters of creative figures and the settings of a Toniebox 2.

The page is the way to change figures and boxes by hand; these actions are
for what should happen on its own, such as a greeting spoken onto a figure
every evening or a lower maximum volume while guests sleep over. They are
for administrators (automations and scripts run with that right).

Figures have no entities, so the chapter actions name a creative figure by
its name as the page shows it, or by its ID. The settings action targets the
media player of a Toniebox 2; a Toniebox 1 has no entities.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import probatio as vol

from homeassistant.components import media_source
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service import async_extract_entity_ids, async_register_admin_service

from . import speech
from .cloud import CloudError, Tonie, TonieKind
from .cloud.models import SETTING_FIELDS
from .const import DOMAIN
from .coordinator import BoxError, ChapterError, StoryboxCoordinator, setting_supported
from .shuffle import MIN_CHAPTERS, new_order
from .websocket import content_type

SERVICE_ADD_CHAPTER = "add_chapter"
SERVICE_REMOVE_CHAPTERS = "remove_chapters"
SERVICE_SHUFFLE_CHAPTERS = "shuffle_chapters"
SERVICE_SET_BOX_SETTINGS = "set_box_settings"

CHAPTER_TITLE_MAX = 128
# A file from a media source is read up to this size; the cloud takes 90 minutes at most
MEDIA_MAX_BYTES = 200 * 1024 * 1024
# The settings a Toniebox 2 has; the others belong to the Toniebox 1, which has no entity
BOX_SETTINGS = (
    "max_volume",
    "max_headphone_volume",
    "lightring_brightness",
    "bedtime_lightring_brightness",
    "bedtime_max_volume",
    "bedtime_max_headphone_volume",
    "skipping_enabled",
    "skipping_direction",
    "scrubbing_enabled",
)
_SOURCES = ("media", "text", "url")


def _setting_check(name: str) -> Any:
    allowed = SETTING_FIELDS[name][1]
    if allowed is bool:
        return cv.boolean
    if isinstance(allowed[0], str):
        return vol.In(allowed)
    return vol.All(vol.Coerce(int), vol.Range(min=allowed[0], max=allowed[1]))


ADD_CHAPTER_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required("figure"): vol.All(cv.string, vol.Strip, vol.Length(min=1)),
            vol.Exclusive("media", "source"): vol.Schema(
                {vol.Required("media_content_id"): cv.string}, extra=vol.ALLOW_EXTRA
            ),
            vol.Exclusive("text", "source"): vol.All(
                cv.string, vol.Strip, vol.Length(min=1, max=speech.TEXT_MAX)
            ),
            vol.Exclusive("url", "source"): vol.All(cv.string, vol.Length(min=1, max=2048)),
            vol.Optional("title"): vol.All(
                cv.string, vol.Strip, vol.Length(min=1, max=CHAPTER_TITLE_MAX)
            ),
            vol.Optional("replace", default=False): cv.boolean,
        },
        cv.has_at_least_one_key(*_SOURCES),
    )
)
REMOVE_CHAPTERS_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required("figure"): vol.All(cv.string, vol.Strip, vol.Length(min=1)),
            vol.Exclusive("title", "which"): vol.All(cv.string, vol.Strip, vol.Length(min=1)),
            vol.Exclusive("keep_last", "which"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        },
        cv.has_at_least_one_key("title", "keep_last"),
    )
)
SHUFFLE_CHAPTERS_SCHEMA = vol.Schema(
    {vol.Required("figure"): vol.All(cv.string, vol.Strip, vol.Length(min=1))}
)
_BOX_SETTING_FIELDS: dict[Any, Any] = {
    **cv.ENTITY_SERVICE_FIELDS,
    **{vol.Optional(name): _setting_check(name) for name in BOX_SETTINGS},
}
SET_BOX_SETTINGS_SCHEMA = vol.Schema(
    vol.All(_BOX_SETTING_FIELDS, cv.has_at_least_one_key(*BOX_SETTINGS))
)


def _coordinators(hass: HomeAssistant) -> list[StoryboxCoordinator]:
    return [
        entry.runtime_data.coordinator
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def find_figure(hass: HomeAssistant, ref: str) -> tuple[StoryboxCoordinator, Tonie]:
    """Return the creative figure an action names, by ID or by its name (any case).

    A figure several accounts share counts once. A name two creative figures
    carry is refused: the action cannot know which one is meant.
    """
    found: dict[str, tuple[StoryboxCoordinator, Tonie]] = {}
    wanted = ref.casefold()
    for coordinator in _coordinators(hass):
        for tonie in coordinator.data.tonies.values():
            if tonie.id in found:
                continue
            if tonie.id == ref or (
                tonie.kind is TonieKind.CREATIVE and tonie.name.casefold() == wanted
            ):
                found[tonie.id] = (coordinator, tonie)
    if not found:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="figure_unknown",
            translation_placeholders={"figure": ref},
        )
    if len(found) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="figure_ambiguous",
            translation_placeholders={"figure": ref, "count": str(len(found))},
        )
    coordinator, tonie = next(iter(found.values()))
    if tonie.kind is not TonieKind.CREATIVE:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_creative",
            translation_placeholders={"figure": tonie.name},
        )
    return coordinator, tonie


def _figure_response(tonie: Tonie) -> dict[str, Any]:
    free = tonie.seconds_remaining
    return {
        "figure": tonie.name,
        "id": tonie.id,
        "chapters": [chapter.title for chapter in tonie.chapters],
        "minutes_free": round(free / 60, 1) if free is not None else None,
    }


def _refused(err: ChapterError | CloudError) -> HomeAssistantError:
    """Say why a change of chapters failed, in the words the page uses too."""
    if isinstance(err, ChapterError):
        return ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="chapter_refused",
            translation_placeholders={"error": str(err)},
        )
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="cloud_failed",
        translation_placeholders={"error": str(err)},
    )


async def _read_media(hass: HomeAssistant, media_id: str) -> tuple[bytes, str]:
    """Read the audio a media selector picked: a file, a spoken text or a web address.

    Returns the bytes and a file name whose ending tells the audio type.
    """
    try:
        if media_id.startswith("media-source://tts/"):
            from homeassistant.components import tts  # Loaded only when a text was spoken

            extension, data = await tts.async_get_media_source_audio(hass, media_id)
            return data, f"speech.{extension}"
        url = media_id
        if media_source.is_media_source_id(media_id):
            play = await media_source.async_resolve_media(hass, media_id, None)
            if play.path is not None:
                path: Path = play.path
                data = await hass.async_add_executor_job(path.read_bytes)
                return data, path.name
            url = play.url
        if not url.startswith(("http://", "https://")):
            raise ValueError("not a web address")
        session = async_get_clientsession(hass)
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.content.read(MEDIA_MAX_BYTES + 1)
        if len(data) > MEDIA_MAX_BYTES:
            raise ValueError("larger than 200 MB")
        name = Path(url.split("?", 1)[0]).name or "media.mp3"
    except Exception as err:  # The media source, the speech engine or the web: none may pass
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="media_unreadable",
            translation_placeholders={"error": str(err) or type(err).__name__},
        ) from err
    return data, name


async def _async_add_chapter(call: ServiceCall) -> ServiceResponse:
    """Add a chapter from a media source, a text or a video link."""
    hass = call.hass
    coordinator, tonie = find_figure(hass, call.data["figure"])
    title: str | None = call.data.get("title")
    try:
        if "text" in call.data:
            text: str = call.data["text"]
            figure = await coordinator.async_add_chapter_from_text(
                tonie.id, text, title or " ".join(text.split()[:6])
            )
        elif "url" in call.data:
            figure = await coordinator.async_add_chapter_from_link(
                tonie.id, call.data["url"], lambda _event: None, asyncio.Event()
            )
            if title:
                new = figure.chapters[-1]
                figure = await coordinator.async_arrange_chapters(
                    tonie.id, [c.id for c in figure.chapters], {new.id: title}
                )
        else:
            data, filename = await _read_media(hass, call.data["media"]["media_content_id"])
            if not data:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="media_unreadable",
                    translation_placeholders={"error": "empty"},
                )
            figure = await coordinator.async_add_chapter(
                tonie.id,
                title or Path(filename).stem or filename,
                data,
                filename,
                content_type(filename),
            )
        if call.data["replace"]:
            new = figure.chapters[-1]
            keep = [c.id for c in figure.chapters if c.id == new.id or c.title != new.title]
            if len(keep) < len(figure.chapters):
                figure = await coordinator.async_arrange_chapters(tonie.id, keep)
    except (ChapterError, CloudError) as err:
        raise _refused(err) from err
    return _figure_response(figure)


async def _async_remove_chapters(call: ServiceCall) -> ServiceResponse:
    """Remove the chapters of a title, or all but the last ones."""
    coordinator, tonie = find_figure(call.hass, call.data["figure"])
    chapters = list(tonie.chapters)
    if "title" in call.data:
        wanted = call.data["title"].casefold()
        keep = [c.id for c in chapters if c.title.casefold() != wanted]
    else:
        last: int = call.data["keep_last"]
        keep = [c.id for c in chapters[len(chapters) - last :]] if last else []
    if len(keep) == len(chapters):
        return _figure_response(tonie)
    try:
        figure = await coordinator.async_arrange_chapters(tonie.id, keep)
    except (ChapterError, CloudError) as err:
        raise _refused(err) from err
    return _figure_response(figure)


async def _async_shuffle_chapters(call: ServiceCall) -> ServiceResponse:
    """Put the chapters of a creative figure into a new random order."""
    coordinator, tonie = find_figure(call.hass, call.data["figure"])
    if len(tonie.chapters) < MIN_CHAPTERS:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="too_few_chapters",
            translation_placeholders={"figure": tonie.name},
        )
    try:
        await coordinator.async_refuse_tune(tonie.id)
        figure = await coordinator.async_arrange_chapters(
            tonie.id, new_order([c.id for c in tonie.chapters])
        )
    except (ChapterError, CloudError) as err:
        raise _refused(err) from err
    return _figure_response(figure)


async def _async_set_box_settings(call: ServiceCall) -> None:
    """Change settings of the targeted Tonieboxes 2, as the page's save button does."""
    hass = call.hass
    changes = {name: call.data[name] for name in BOX_SETTINGS if name in call.data}
    registry = er.async_get(hass)
    targets: list[tuple[StoryboxCoordinator, str]] = []
    by_entry = {c.config_entry.entry_id: c for c in _coordinators(hass)}
    for entity_id in await async_extract_entity_ids(call):
        entity = registry.async_get(entity_id)
        coordinator = by_entry.get(entity.config_entry_id or "") if entity else None
        if entity is None or coordinator is None or entity.domain != Platform.MEDIA_PLAYER:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_a_box",
                translation_placeholders={"entity": entity_id},
            )
        box_id = entity.unique_id.removeprefix(f"{coordinator.config_entry.entry_id}_")
        box_state = coordinator.data.boxes.get(box_id)
        if box_state is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="box_unknown")
        missing = [name for name in changes if not setting_supported(box_state.box, name)]
        if missing:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="setting_unsupported",
                translation_placeholders={"box": box_state.box.name, "setting": missing[0]},
            )
        targets.append((coordinator, box_id))
    if not targets:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_box")
    for coordinator, box_id in targets:
        try:
            await coordinator.async_change_settings(box_id, changes)
        except BoxError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="setting_refused",
                translation_placeholders={"error": err.code},
            ) from err
        except CloudError as err:
            raise _refused(err) from err


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions, once, for administrators and automations."""
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_ADD_CHAPTER,
        _async_add_chapter,
        ADD_CHAPTER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_REMOVE_CHAPTERS,
        _async_remove_chapters,
        REMOVE_CHAPTERS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SHUFFLE_CHAPTERS,
        _async_shuffle_chapters,
        SHUFFLE_CHAPTERS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_BOX_SETTINGS,
        _async_set_box_settings,
        SET_BOX_SETTINGS_SCHEMA,
    )
