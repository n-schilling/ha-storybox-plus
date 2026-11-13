"""The live channel's sensor, counting switched on the settings tab, renamed chapters and
chapters spoken by Piper."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.storybox_plus import speech
from custom_components.storybox_plus.const import DOMAIN

from .conftest import CREATIVE_ID, HOUSEHOLD_ID, TONIE_ID, FakeCloud, PushChannels, entity_id


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


# ---------------------------------------------------------------- the live channel


async def test_live_channel_sensor(
    hass: HomeAssistant, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The account's sensor follows the push channel."""
    sensor = entity_id(hass, "binary_sensor", "live_channel")
    assert hass.states.get(sensor).state == "off"
    push.last.connect()
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "on"
    push.last.connect(False)
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "off"


async def test_no_live_channel_without_a_toniebox_2(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """An account with classic boxes only has no live channel to watch."""
    cloud.main.boxes[HOUSEHOLD_ID] = [
        b for b in cloud.main.boxes[HOUSEHOLD_ID] if "tngSettings" not in b["features"]
    ]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    assert (
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{config_entry.entry_id}_live_channel"
        )
        is None
    )


# ---------------------------------------------------------------- counting on the settings tab


async def test_counting_switched_off_and_on(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """Switching counting off reloads the account and deletes the sums; on counts again."""
    assert setup_entry.runtime_data.analytics is not None
    client = await hass_ws_client(hass)
    result = await _call(
        client,
        {"type": f"{DOMAIN}/preferences/set", "entry_id": setup_entry.entry_id, "analytics": False},
    )
    assert result["result"]["analytics"] is False
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.LOADED
    assert setup_entry.runtime_data.analytics is None
    assert f"{DOMAIN}.{setup_entry.entry_id}.analytics" not in hass_storage
    result = await _call(
        client,
        {"type": f"{DOMAIN}/preferences/set", "entry_id": setup_entry.entry_id, "analytics": True},
    )
    await hass.async_block_till_done()
    assert setup_entry.runtime_data.analytics is not None
    # The same value again reloads nothing
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        await _call(
            client,
            {
                "type": f"{DOMAIN}/preferences/set",
                "entry_id": setup_entry.entry_id,
                "analytics": True,
            },
        )
    reload.assert_not_called()


# ---------------------------------------------------------------- renamed chapters


async def test_chapters_renamed(
    hass: HomeAssistant,
    cloud: FakeCloud,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """New names go with the order; a name of a chapter the figure lacks is refused."""
    client = await hass_ws_client(hass)
    result = await _call(
        client,
        {
            "type": f"{DOMAIN}/chapters/arrange",
            "tonie_id": CREATIVE_ID,
            "chapters": ["ch1"],
            "titles": {"ch1": " Lullaby "},
        },
    )
    assert result["success"], result
    assert cloud.chapter_patches[-1][2]["chapters"][0]["title"] == "Lullaby"
    result = await _call(
        client,
        {
            "type": f"{DOMAIN}/chapters/arrange",
            "tonie_id": CREATIVE_ID,
            "chapters": ["ch1"],
            "titles": {"nope": "X"},
        },
    )
    assert result["error"]["code"] == "unknown_chapter"


# ---------------------------------------------------------------- chapters spoken by Piper


def _piper(hass: HomeAssistant, state: str = "unknown") -> None:
    """Register a Piper voice as the Wyoming integration would."""
    hass.config.components.add("tts")
    er.async_get(hass).async_get_or_create(
        "tts", "wyoming", "piper-voice", suggested_object_id="piper", original_name="Piper"
    )
    hass.states.async_set("tts.piper", state)


async def test_find_piper(hass: HomeAssistant) -> None:
    """Only an available Piper voice of the Wyoming integration counts."""
    assert speech.find_piper(hass) is None
    _piper(hass, "unavailable")
    assert speech.find_piper(hass) is None
    hass.states.async_set("tts.piper", "unknown")
    assert speech.find_piper(hass) == "tts.piper"
    er.async_get(hass).async_get_or_create(
        "tts", "cloud", "other", suggested_object_id="cloud_voice"
    )
    assert speech.find_piper(hass) == "tts.piper"


async def test_speak_reports_failures(hass: HomeAssistant) -> None:
    """Whatever goes wrong in the speech pipeline comes back as a SpeechError."""
    fake_tts = type(
        "FakeTts",
        (),
        {
            "generate_media_source_id": staticmethod(lambda *a, **k: "media-source://tts/x"),
            "async_get_media_source_audio": staticmethod(_no_audio),
        },
    )
    with (
        patch.dict("sys.modules", {"homeassistant.components.tts": fake_tts}),
        patch("homeassistant.components.tts", fake_tts, create=True),
        pytest.raises(speech.SpeechError),
    ):
        await speech.async_speak(hass, "tts.piper", "Hallo")


async def _no_audio(hass: HomeAssistant, media_id: str) -> tuple[str, bytes]:
    return "mp3", b""


async def test_chapter_from_text(
    hass: HomeAssistant,
    cloud: FakeCloud,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Without Piper the page is told; with it the spoken text becomes a chapter."""
    client = await hass_ws_client(hass)
    library = await _call(client, {"type": f"{DOMAIN}/library"})
    assert library["result"]["speech"] is False
    message = {
        "type": f"{DOMAIN}/chapters/add_text",
        "tonie_id": CREATIVE_ID,
        "text": "  Gute Nacht, schlaf schön und träum etwas Schönes heute  ",
    }
    result = await _call(client, message)
    assert result["error"]["code"] == "speech_missing"

    _piper(hass)
    library = await _call(client, {"type": f"{DOMAIN}/library"})
    assert library["result"]["speech"] is True
    with patch.object(speech, "async_speak", return_value=("mp3", b"ID3audio")) as speak:
        result = await _call(client, message)
    assert result["success"], result
    speak.assert_awaited_once()
    assert speak.await_args.args[1:] == (
        "tts.piper",
        "Gute Nacht, schlaf schön und träum etwas Schönes heute",
    )
    added = cloud.chapter_adds[-1][2]
    assert added["title"] == "Gute Nacht, schlaf schön und träum"
    upload = cloud.s3_uploads[-1]
    assert ("file", "text.mp3", "audio/mpeg", len(b"ID3audio")) in upload["fields"]

    with patch.object(speech, "async_speak", side_effect=speech.SpeechError("no voice")):
        result = await _call(client, {**message, "title": "Gruß"})
    assert result["error"]["code"] == "speech_failed"
    result = await _call(client, {**message, "tonie_id": TONIE_ID})
    assert result["error"]["code"] == "not_creative"
    result = await _call(client, {**message, "tonie_id": "nope"})
    assert result["error"]["code"] == "unknown_figure"


async def _audio(hass: HomeAssistant, media_id: str) -> tuple[str, bytes]:
    return "mp3", b"ID3"


async def _broken(hass: HomeAssistant, media_id: str) -> tuple[str, bytes]:
    raise RuntimeError("voice gone")


@pytest.mark.parametrize(("audio", "expected"), [(_audio, ("mp3", b"ID3")), (_broken, None)])
async def test_speak(hass: HomeAssistant, audio: Any, expected: Any) -> None:
    """The audio comes back as it is; a failure of the pipeline as a SpeechError."""
    fake_tts = type(
        "FakeTts",
        (),
        {
            "generate_media_source_id": staticmethod(lambda *a, **k: "media-source://tts/x"),
            "async_get_media_source_audio": staticmethod(audio),
        },
    )
    with (
        patch.dict("sys.modules", {"homeassistant.components.tts": fake_tts}),
        patch("homeassistant.components.tts", fake_tts, create=True),
    ):
        if expected is None:
            with pytest.raises(speech.SpeechError, match="voice gone"):
                await speech.async_speak(hass, "tts.piper", "Hallo")
        else:
            assert await speech.async_speak(hass, "tts.piper", "Hallo") == expected
