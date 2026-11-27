"""The actions for automations: chapters of creative figures and the settings of a box."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry, MockUser
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from homeassistant.components.media_source import PlayMedia
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.setup import async_setup_component

from custom_components.storybox_plus import services, speech
from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.coordinator import StoryboxCoordinator

from .conftest import (
    BOX_ID,
    CREATIVE_ID,
    CREATIVE_NAME,
    HOUSEHOLD_ID,
    TONIE_ID,
    FakeCloud,
    PushChannels,
    creative_tonie,
    entity_id,
)


def _speech_engine(audio: Any) -> Any:
    """Stand in for the speech integration, whose module needs more than the tests have."""
    fake = type("tts", (), {"async_get_media_source_audio": staticmethod(audio)})
    return patch.dict("sys.modules", {"homeassistant.components.tts": fake})


def _two_chapters(cloud: FakeCloud) -> None:
    figure = cloud.main.creative_tonies[HOUSEHOLD_ID][0]
    figure["chapters"].append(
        {"id": "ch2", "title": "Gruß", "file": "f2", "seconds": 30.0, "transcoding": False}
    )


async def _setup(hass: HomeAssistant, config_entry: MockConfigEntry) -> MockConfigEntry:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def _call(hass: HomeAssistant, service: str, data: dict[str, Any], **kwargs: Any) -> Any:
    return await hass.services.async_call(
        DOMAIN, service, data, blocking=True, return_response=True, **kwargs
    )


async def test_actions_are_registered(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The four actions exist next to those of the media player."""
    for service in ("add_chapter", "remove_chapters", "shuffle_chapters", "set_box_settings"):
        assert hass.services.has_service(DOMAIN, service)


async def test_figure_is_found_by_name_or_id(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A creative figure is named in any case or by ID; others are refused with a reason."""
    cloud.main.creative_tonies[HOUSEHOLD_ID].append(creative_tonie("c2", "Doppelt"))
    cloud.main.creative_tonies[HOUSEHOLD_ID].append(creative_tonie("c3", "doppelt"))
    await _setup(hass, config_entry)
    _, by_name = services.find_figure(hass, CREATIVE_NAME.upper())
    assert by_name.id == CREATIVE_ID
    _, by_id = services.find_figure(hass, "c2")
    assert by_id.name == "Doppelt"
    for ref, key in (
        ("niemand", "figure_unknown"),
        ("Doppelt", "figure_ambiguous"),
        (TONIE_ID, "not_creative"),
    ):
        with pytest.raises(ServiceValidationError) as err:
            services.find_figure(hass, ref)
        assert err.value.translation_key == key


async def test_add_chapter_from_text_replaces_the_old_one(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A spoken greeting with replace leaves exactly one chapter of its title."""
    _two_chapters(cloud)
    await _setup(hass, config_entry)
    with (
        patch.object(speech, "find_engine", return_value="tts.piper"),
        patch.object(speech, "async_speak", return_value=("mp3", b"ID3audio")),
    ):
        answer = await _call(
            hass,
            "add_chapter",
            {"figure": CREATIVE_NAME, "text": "Gute Nacht", "title": "Gruß", "replace": True},
        )
    assert cloud.chapter_adds[-1][2]["title"] == "Gruß"
    kept = [c["title"] for c in cloud.chapter_patches[-1][2]["chapters"]]
    assert kept == ["Song", "Gruß"]
    assert answer["chapters"] == ["Song", "Gruß"]
    assert answer["id"] == CREATIVE_ID
    assert answer["figure"] == CREATIVE_NAME


async def test_add_chapter_without_replace_changes_nothing_else(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Without replace, a chapter of the same title stays; the title defaults to the first words."""
    await _setup(hass, config_entry)
    with (
        patch.object(speech, "find_engine", return_value="tts.piper"),
        patch.object(speech, "async_speak", return_value=("mp3", b"ID3audio")),
    ):
        answer = await _call(hass, "add_chapter", {"figure": CREATIVE_ID, "text": "Hallo du"})
    assert cloud.chapter_patches == []
    assert answer["chapters"] == ["Song", "Hallo du"]


async def test_add_chapter_from_spoken_media(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A text the media browser had spoken is read from the speech engine."""
    await _setup(hass, config_entry)

    async def audio(hass: HomeAssistant, media_id: str) -> tuple[str, bytes]:
        assert media_id == "media-source://tts/tts.piper?message=Hallo"
        return "mp3", b"ID3"

    with _speech_engine(audio):
        answer = await _call(
            hass,
            "add_chapter",
            {
                "figure": CREATIVE_ID,
                "media": {
                    "media_content_id": "media-source://tts/tts.piper?message=Hallo",
                    "media_content_type": "provider",
                },
            },
        )
    assert answer["chapters"] == ["Song", "speech"]
    assert ("file", "speech.mp3", "audio/mpeg", 3) in cloud.s3_uploads[-1]["fields"]


async def test_add_chapter_from_a_local_file(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    tmp_path: Path,
) -> None:
    """A file of the local media folder is read from the disk."""
    await _setup(hass, config_entry)
    song = tmp_path / "Schlaflied.ogg"
    song.write_bytes(b"OggS")
    play = PlayMedia("/media/local/Schlaflied.ogg", "audio/ogg", path=song)
    with patch.object(services.media_source, "async_resolve_media", return_value=play):
        answer = await _call(
            hass,
            "add_chapter",
            {
                "figure": CREATIVE_ID,
                "media": {"media_content_id": "media-source://media_source/local/Schlaflied.ogg"},
                "title": "Lied",
            },
        )
    assert answer["chapters"] == ["Song", "Lied"]
    assert ("file", "Schlaflied.ogg", "audio/ogg", 4) in cloud.s3_uploads[-1]["fields"]


async def test_add_chapter_from_a_web_address(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A media source that resolves to a web address is downloaded."""
    await _setup(hass, config_entry)
    aioclient_mock.get("https://media.example.com/gruss.mp3?token=1", content=b"ID3web")
    play = PlayMedia("https://media.example.com/gruss.mp3?token=1", "audio/mpeg")
    with patch.object(services.media_source, "async_resolve_media", return_value=play):
        answer = await _call(
            hass,
            "add_chapter",
            {"figure": CREATIVE_ID, "media": {"media_content_id": "media-source://other/x"}},
        )
    assert answer["chapters"] == ["Song", "gruss"]


@pytest.mark.parametrize(
    "play",
    [
        PlayMedia("/api/somewhere/x.mp3", "audio/mpeg"),
        PlayMedia("https://media.example.com/missing.mp3", "audio/mpeg"),
    ],
)
async def test_unreadable_media_is_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    play: PlayMedia,
) -> None:
    """A relative address or a failed download add nothing."""
    await _setup(hass, config_entry)
    aioclient_mock.get("https://media.example.com/missing.mp3", status=404)
    with (
        patch.object(services.media_source, "async_resolve_media", return_value=play),
        pytest.raises(ServiceValidationError) as err,
    ):
        await _call(
            hass,
            "add_chapter",
            {"figure": CREATIVE_ID, "media": {"media_content_id": "media-source://other/x"}},
        )
    assert err.value.translation_key == "media_unreadable"
    assert cloud.chapter_adds == []


async def test_empty_media_is_refused(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A source without bytes adds no chapter."""
    await _setup(hass, config_entry)

    async def empty(hass: HomeAssistant, media_id: str) -> tuple[str, bytes]:
        return "mp3", b""

    with (
        _speech_engine(empty),
        pytest.raises(ServiceValidationError) as err,
    ):
        await _call(
            hass,
            "add_chapter",
            {"figure": CREATIVE_ID, "media": {"media_content_id": "media-source://tts/x"}},
        )
    assert err.value.translation_key == "media_unreadable"


async def test_add_chapter_from_a_link(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A video link becomes a chapter; a title given renames it afterwards."""
    await _setup(hass, config_entry)
    coordinator: StoryboxCoordinator = config_entry.runtime_data.coordinator
    figure = coordinator.data.tonies[CREATIVE_ID]

    async def fetched(tonie_id: str, url: str, progress: Any, cancelled: Any) -> Any:
        progress({"stage": "probe"})
        assert not cancelled.is_set()
        assert url == "https://youtu.be/abc"
        return figure

    with patch.object(coordinator, "async_add_chapter_from_link", side_effect=fetched):
        answer = await _call(
            hass,
            "add_chapter",
            {"figure": CREATIVE_ID, "url": "https://youtu.be/abc", "title": "Neu"},
        )
    assert cloud.chapter_patches[-1][2]["chapters"][0]["title"] == "Neu"
    assert answer["chapters"] == ["Neu"]
    with patch.object(coordinator, "async_add_chapter_from_link", side_effect=fetched):
        answer = await _call(
            hass, "add_chapter", {"figure": CREATIVE_ID, "url": "https://youtu.be/abc"}
        )
    # Without a title the chapter keeps the video's, and nothing is renamed
    assert answer["chapters"] == ["Song"]


async def test_refusals_of_the_cloud_and_the_figure(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A refused change says why; a failing cloud is no validation error."""
    await _setup(hass, config_entry)
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "add_chapter", {"figure": CREATIVE_ID, "text": "Hallo"})
    assert err.value.translation_key == "chapter_refused"
    coordinator: StoryboxCoordinator = config_entry.runtime_data.coordinator
    from custom_components.storybox_plus.cloud import CloudConnectionError

    with (
        patch.object(
            coordinator, "async_arrange_chapters", side_effect=CloudConnectionError("down")
        ),
        pytest.raises(HomeAssistantError) as failed,
    ):
        await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "keep_last": 0})
    assert failed.value.translation_key == "cloud_failed"


async def test_add_chapter_needs_one_source(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Without a source, or with two, the call is refused before anything happens."""
    with pytest.raises(Exception, match="at least one"):
        await _call(hass, "add_chapter", {"figure": CREATIVE_ID})
    with pytest.raises(Exception, match="two or more"):
        await _call(hass, "add_chapter", {"figure": CREATIVE_ID, "text": "a", "url": "https://x"})
    assert cloud.chapter_adds == []


async def test_remove_chapters(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """By title in any case, or all but the last ones; nothing to remove asks the cloud nothing."""
    _two_chapters(cloud)
    await _setup(hass, config_entry)
    answer = await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "title": "nichts"})
    assert answer["chapters"] == ["Song", "Gruß"]
    assert cloud.chapter_patches == []
    answer = await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "keep_last": 5})
    assert cloud.chapter_patches == []
    answer = await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "title": "SONG"})
    assert answer["chapters"] == ["Gruß"]
    answer = await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "keep_last": 0})
    assert answer["chapters"] == []
    assert answer["minutes_free"] is not None


async def test_remove_keeps_the_last(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """keep_last keeps the end of the list."""
    _two_chapters(cloud)
    await _setup(hass, config_entry)
    answer = await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "keep_last": 1})
    assert answer["chapters"] == ["Gruß"]


async def test_shuffle_chapters(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Two chapters change places; a single chapter is refused."""
    _two_chapters(cloud)
    await _setup(hass, config_entry)
    answer = await _call(hass, "shuffle_chapters", {"figure": CREATIVE_ID})
    assert answer["chapters"] == ["Gruß", "Song"]
    await _call(hass, "remove_chapters", {"figure": CREATIVE_ID, "keep_last": 1})
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "shuffle_chapters", {"figure": CREATIVE_ID})
    assert err.value.translation_key == "too_few_chapters"


async def test_set_box_settings(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The media player of a Toniebox 2 takes its settings; only the given ones are sent."""
    player = entity_id(hass, "media_player", BOX_ID)
    await hass.services.async_call(
        DOMAIN,
        "set_box_settings",
        {"entity_id": player, "max_volume": 40, "skipping_enabled": False},
        blocking=True,
    )
    assert cloud.box_patches[-1] == (BOX_ID, {"maxVolume": 40, "skippingEnabled": False})


async def test_set_box_settings_refusals(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Not a box, no box, nothing to change, a box gone or a refused value: nothing is sent."""
    sensor = entity_id(hass, "sensor", f"{BOX_ID}_battery")
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "set_box_settings", {"entity_id": sensor, "max_volume": 40}, blocking=True
        )
    assert err.value.translation_key == "not_a_box"
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "set_box_settings",
            {"entity_id": "media_player.nothing", "max_volume": 40},
            blocking=True,
        )
    assert err.value.translation_key == "not_a_box"
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "set_box_settings", {"entity_id": [], "max_volume": 40}, blocking=True
        )
    assert err.value.translation_key == "no_box"
    player = entity_id(hass, "media_player", BOX_ID)
    with pytest.raises(Exception, match="at least one"):
        await hass.services.async_call(
            DOMAIN, "set_box_settings", {"entity_id": player}, blocking=True
        )
    with pytest.raises(Exception, match="value must be at most"):
        await hass.services.async_call(
            DOMAIN, "set_box_settings", {"entity_id": player, "max_volume": 101}, blocking=True
        )
    coordinator: StoryboxCoordinator = setup_entry.runtime_data.coordinator
    with (
        patch("custom_components.storybox_plus.services.setting_supported", return_value=False),
        pytest.raises(ServiceValidationError) as err,
    ):
        await hass.services.async_call(
            DOMAIN, "set_box_settings", {"entity_id": player, "max_volume": 40}, blocking=True
        )
    assert err.value.translation_key == "setting_unsupported"
    from custom_components.storybox_plus.cloud import CloudConnectionError
    from custom_components.storybox_plus.coordinator import BoxError

    for failure, key in (
        (BoxError("invalid_value"), "setting_refused"),
        (CloudConnectionError("x"), "cloud_failed"),
    ):
        with (
            patch.object(coordinator, "async_change_settings", side_effect=failure),
            pytest.raises(HomeAssistantError) as err,
        ):
            await hass.services.async_call(
                DOMAIN, "set_box_settings", {"entity_id": player, "max_volume": 40}, blocking=True
            )
        assert err.value.translation_key == key
    box = coordinator.data.boxes.pop(BOX_ID)
    try:
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "set_box_settings", {"entity_id": player, "max_volume": 40}, blocking=True
            )
        assert err.value.translation_key == "box_unknown"
    finally:
        coordinator.data.boxes[BOX_ID] = box
    assert cloud.box_patches == []


async def test_actions_need_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_read_only_user: MockUser,
) -> None:
    """A user without administrator rights may not call them."""
    with pytest.raises(Unauthorized):
        await _call(
            hass,
            "remove_chapters",
            {"figure": CREATIVE_ID, "keep_last": 0},
            context=Context(user_id=hass_read_only_user.id),
        )
    assert cloud.chapter_patches == []


async def test_actions_exist_without_an_account(hass: HomeAssistant) -> None:
    """The actions are there as soon as the integration is, and find no figure without one."""
    assert await async_setup_component(hass, DOMAIN, {})
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "shuffle_chapters", {"figure": "x"})
    assert err.value.translation_key == "figure_unknown"
