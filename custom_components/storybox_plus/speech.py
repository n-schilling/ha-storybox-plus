"""A chapter from text: a voice of Home Assistant speaks it.

Like links through the Media Fetcher app, this is optional: the page offers
it only while a voice can speak. Without a choice that is Piper, the local
voice of Home Assistant (the Wyoming integration with a Piper entity): the
text never leaves the house then, only the spoken audio goes to the cloud as
a chapter. Any other text-to-speech entity can be chosen in the preferences;
a voice of a cloud service gets the text to speak it.
"""

from __future__ import annotations

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

# The text of one chapter; Piper speaks it at about 15 characters a second
TEXT_MAX = 5000


class SpeechError(Exception):
    """The voice could not speak the text."""


def find_engine(hass: HomeAssistant, chosen: str | None) -> str | None:
    """Return the entity that speaks texts now: the chosen one, or Piper without a choice.

    A chosen voice that is gone or unavailable is not replaced by another:
    which service gets the text is the user's choice.
    """
    if chosen is None:
        return find_piper(hass)
    if "tts" not in hass.config.components:
        return None
    state = hass.states.get(chosen)
    return chosen if state is not None and state.state != STATE_UNAVAILABLE else None


def find_piper(hass: HomeAssistant) -> str | None:
    """Return the entity of a Piper voice that can speak now, if one is set up.

    Piper comes through the Wyoming integration; its text-to-speech entity
    names Piper in its ID or name. One that is unavailable does not count.
    """
    if "tts" not in hass.config.components:
        return None
    registry = er.async_get(hass)
    found = [
        e.entity_id
        for e in registry.entities.values()
        if e.domain == "tts"
        and e.platform == "wyoming"
        and not e.disabled
        and "piper" in f"{e.entity_id} {e.original_name or ''} {e.name or ''}".lower()
    ]
    for entity_id in sorted(found, key=lambda e: e != "tts.piper"):
        state = hass.states.get(entity_id)
        if state is not None and state.state != STATE_UNAVAILABLE:
            return entity_id
    return None


async def async_speak(
    hass: HomeAssistant,
    engine: str,
    text: str,
    voice: str | None = None,
    language: str | None = None,
) -> tuple[str, bytes]:
    """Let the engine speak the text; return the file ending and audio.

    Without a voice, the engine speaks in its own default voice and language.
    """
    # Imported here: the text-to-speech integration is only there when set up
    from homeassistant.components import tts

    try:
        media_id = tts.generate_media_source_id(
            hass,
            text,
            engine=engine,
            language=language if voice else None,
            options={"voice": voice} if voice else None,
        )
        extension, data = await tts.async_get_media_source_audio(hass, media_id)
    except Exception as err:  # The engine or the speech pipeline failed, whatever the reason
        raise SpeechError(str(err) or type(err).__name__) from err
    if not data:
        raise SpeechError("The voice returned no audio")
    return extension, data
