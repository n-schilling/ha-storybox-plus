"""The entities of a box: connectivity, battery, the media player and the figure event."""

from __future__ import annotations

from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.media_player import (
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MP_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_SEEK,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError

from custom_components.storybox_plus.cloud import CloudConnectionError

from .conftest import (
    BOX_ID,
    CLASSIC_BOX_ID,
    CREATIVE_ID,
    CREATIVE_NAME,
    MAC,
    TONIE_ID,
    TONIE_NAME,
    TONIE_SERIES,
    FakeCloud,
    PushChannels,
    entity_id,
)


def _state(hass: HomeAssistant, domain: str, unique_id: str) -> State:
    state = hass.states.get(entity_id(hass, domain, unique_id))
    assert state is not None
    return state


def _player(hass: HomeAssistant) -> State:
    return _state(hass, MP_DOMAIN, BOX_ID)


async def _call(hass: HomeAssistant, service: str, **data: Any) -> None:
    await hass.services.async_call(
        MP_DOMAIN,
        service,
        {ATTR_ENTITY_ID: entity_id(hass, MP_DOMAIN, BOX_ID), **data},
        blocking=True,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


# -- connectivity --


async def test_connectivity_follows_push(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A Toniebox 2 starts with the cloud's state and follows the push channel from then on."""
    connectivity = entity_id(hass, "binary_sensor", f"{BOX_ID}_connectivity")
    assert hass.states.get(connectivity).state == STATE_ON
    push.last.online(False)
    assert hass.states.get(connectivity).state == STATE_OFF
    push.last.online(True)
    assert hass.states.get(connectivity).state == STATE_ON
    push.last.online(None)
    assert hass.states.get(connectivity).state == STATE_UNKNOWN
    # A poll does not overwrite what the push channel said
    push.last.online(False)
    await setup_entry.runtime_data.coordinator.async_refresh()
    assert hass.states.get(connectivity).state == STATE_OFF


async def test_connectivity_unknown_without_online_state(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Without any information the state stays unknown; a playing box is online."""
    box = cloud.main.box(BOX_ID)
    del box["onlineState"]
    del box["lastSeen"]
    await _setup(hass, config_entry)
    assert _state(hass, "binary_sensor", f"{BOX_ID}_connectivity").state == STATE_UNKNOWN
    assert _player(hass).state == STATE_UNKNOWN
    push.last.playback()
    assert _state(hass, "binary_sensor", f"{BOX_ID}_connectivity").state == STATE_ON


async def test_classic_connectivity_follows_last_seen(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A classic box counts as online for 30 minutes after the cloud last saw it."""
    freezer.move_to("2026-11-04T10:10:00+00:00")
    classic = cloud.main.box(CLASSIC_BOX_ID)
    classic["lastSeen"] = "2026-11-04T10:00:00Z"
    await _setup(hass, config_entry)
    connectivity = entity_id(hass, "binary_sensor", f"{CLASSIC_BOX_ID}_connectivity")
    assert hass.states.get(connectivity).state == STATE_ON

    freezer.move_to("2026-11-04T10:31:00+00:00")
    await config_entry.runtime_data.coordinator.async_refresh()
    assert hass.states.get(connectivity).state == STATE_OFF

    del classic["lastSeen"]
    await config_entry.runtime_data.coordinator.async_refresh()
    assert hass.states.get(connectivity).state == STATE_UNKNOWN


async def test_push_for_unknown_box_is_ignored(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A message of a box the account does not have changes nothing."""
    push.last.online(False, mac="FFFFFFFFFFFF")
    push.last.playback(mac="FFFFFFFFFFFF")
    assert _state(hass, "binary_sensor", f"{BOX_ID}_connectivity").state == STATE_ON
    assert _player(hass).state == "idle"


# -- battery --


async def test_battery_and_charging(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Battery and charging exist once reported and vanish while the box is off."""
    battery = entity_id(hass, "sensor", f"{BOX_ID}_battery")
    charging = entity_id(hass, "binary_sensor", f"{BOX_ID}_charging")
    assert hass.states.get(battery).state == STATE_UNAVAILABLE
    assert hass.states.get(charging).state == STATE_UNAVAILABLE

    push.last.battery(80, "charging")
    assert hass.states.get(battery).state == "80"
    assert hass.states.get(battery).attributes["unit_of_measurement"] == "%"
    assert hass.states.get(charging).state == STATE_ON

    push.last.battery(79, "discharging")
    assert hass.states.get(battery).state == "79"
    assert hass.states.get(charging).state == STATE_OFF

    # A box that shuts down sends only nulls, then goes offline
    push.last.battery(None, None)
    assert hass.states.get(battery).state == STATE_UNKNOWN
    assert hass.states.get(charging).state == STATE_UNKNOWN
    push.last.online(False)
    assert hass.states.get(battery).state == STATE_UNAVAILABLE
    assert hass.states.get(charging).state == STATE_UNAVAILABLE

    push.last.online(True)
    push.last.battery(50, "full")
    assert hass.states.get(battery).state == "50"
    assert hass.states.get(charging).state == STATE_OFF


# -- media player --


async def test_player_states(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Off while offline, idle without a figure, playing or paused with one."""
    assert _player(hass).state == "idle"
    push.last.online(False)
    assert _player(hass).state == "off"
    push.last.playback(paused=False)
    assert _player(hass).state == "playing"
    assert _state(hass, "binary_sensor", f"{BOX_ID}_connectivity").state == STATE_ON
    push.last.playback(paused=True)
    assert _player(hass).state == "paused"
    push.last.playback(paused=False, ended=True)
    assert _player(hass).state == "idle"
    push.last.playback(paused=False, downloading=True)
    assert _player(hass).state == "idle"
    push.last.playback(paused=None)
    assert _player(hass).state == "idle"
    push.last.removed()
    assert _player(hass).state == "idle"
    push.last.online(None)
    assert _player(hass).state == STATE_UNKNOWN
    # Going offline while playing turns the player off; what plays counts as paused
    push.last.playback(paused=False)
    push.last.online(False)
    assert _player(hass).state == "off"
    assert setup_entry.runtime_data.coordinator.data.boxes[BOX_ID].playback.paused is True


async def test_player_attributes(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The chapter, the figure, its series and picture, and the position are shown."""
    push.last.playback(chapter=1, duration=200.0, position=50.0)
    attributes = _player(hass).attributes
    assert attributes["media_title"] == "Kapitel 2"
    assert attributes["media_album_name"] == TONIE_NAME
    assert attributes["media_artist"] == TONIE_SERIES
    assert attributes["media_track"] == 2
    assert attributes["media_duration"] == 200
    assert attributes["media_position"] == 50
    assert attributes["media_position_updated_at"] is not None
    assert attributes["media_content_type"] == "music"
    assert attributes["entity_picture"].startswith("/api/media_player_proxy/")
    assert "volume_level" not in attributes
    assert attributes["device_class"] == "speaker"

    push.last.volume(7)
    assert _player(hass).attributes["volume_level"] == pytest.approx(7 / 13)

    push.last.playback(chapter=1, duration=None, position=None)
    attributes = _player(hass).attributes
    assert "media_duration" not in attributes
    assert "media_position" not in attributes
    assert "media_position_updated_at" not in attributes
    assert "media_track" in attributes


async def test_player_title_fallbacks(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Without a usable chapter title the figure's name is shown; an unknown figure shows nothing."""
    push.last.playback(chapter=7)
    attributes = _player(hass).attributes
    assert attributes["media_title"] == TONIE_NAME
    assert attributes["media_track"] == 8

    push.last.playback(chapter=None)
    assert _player(hass).attributes["media_title"] == TONIE_NAME
    assert "media_track" not in _player(hass).attributes

    cloud.main.content_tonies[0]["chapters"][1]["title"] = ""
    await setup_entry.runtime_data.coordinator.async_refresh()
    push.last.playback(chapter=1)
    assert _player(hass).attributes["media_title"] == TONIE_NAME

    push.last.playback(tonie_id="unknown-figure")
    attributes = _player(hass).attributes
    assert "media_title" not in attributes
    assert "media_album_name" not in attributes
    assert "media_artist" not in attributes
    assert "entity_picture" not in attributes
    assert attributes["media_track"] == 2


async def test_player_commands(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Play, pause, volume and seeking become commands to the box."""
    channel = push.last
    channel.connect()
    channel.playback(chapter=1)
    channel.volume(7)
    await _call(hass, SERVICE_MEDIA_PLAY)
    await _call(hass, SERVICE_MEDIA_PAUSE)
    await _call(hass, SERVICE_VOLUME_SET, **{ATTR_MEDIA_VOLUME_LEVEL: 1.0})
    await _call(hass, SERVICE_VOLUME_SET, **{ATTR_MEDIA_VOLUME_LEVEL: 0.0})
    await _call(hass, SERVICE_VOLUME_SET, **{ATTR_MEDIA_VOLUME_LEVEL: 0.3})
    await _call(hass, SERVICE_VOLUME_UP)
    await _call(hass, SERVICE_VOLUME_DOWN)
    await _call(hass, SERVICE_MEDIA_SEEK, **{ATTR_MEDIA_SEEK_POSITION: 42.7})
    assert channel.commands == [
        (MAC, "playback", {"action": "start"}),
        (MAC, "playback", {"action": "pause"}),
        (MAC, "volume", {"level": 13}),
        (MAC, "volume", {"level": 0}),
        (MAC, "volume", {"level": 4}),
        (MAC, "volume", {"level": 8}),
        (MAC, "volume", {"level": 6}),
        (MAC, "playback", {"action": "setPosition", "chapter": 1, "ms": 42700}),
    ]


async def test_player_volume_steps_are_clamped(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Louder than the loudest and quieter than silent stay within the 13 levels."""
    channel = push.last
    channel.connect()
    channel.volume(13)
    await _call(hass, SERVICE_VOLUME_UP)
    channel.volume(0)
    await _call(hass, SERVICE_VOLUME_DOWN)
    assert channel.commands == [(MAC, "volume", {"level": 13}), (MAC, "volume", {"level": 0})]


async def test_player_volume_step_needs_a_known_volume(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Without a reported volume a step cannot be computed."""
    push.last.connect()
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, SERVICE_VOLUME_UP)
    assert err.value.translation_key == "volume_unknown"
    push.last.volume(None)
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, SERVICE_VOLUME_DOWN)
    assert err.value.translation_key == "volume_unknown"
    assert push.last.commands == []


@pytest.mark.parametrize(
    ("service", "data"),
    [
        (SERVICE_MEDIA_SEEK, {ATTR_MEDIA_SEEK_POSITION: 10}),
        (SERVICE_MEDIA_NEXT_TRACK, {}),
        (SERVICE_MEDIA_PREVIOUS_TRACK, {}),
    ],
)
async def test_player_seeking_needs_a_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    service: str,
    data: dict[str, Any],
) -> None:
    """Seeking and chapter jumps need a figure on the box."""
    push.last.connect()
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, service, **data)
    assert err.value.translation_key == "nothing_plays"
    push.last.removed()
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, service, **data)
    assert err.value.translation_key == "nothing_plays"
    assert push.last.commands == []


async def test_player_chapter_jumps(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Chapter jumps stay within the figure's chapters when they are known."""
    channel = push.last
    channel.connect()

    def jump(chapter: int) -> tuple[str, str, dict[str, Any]]:
        return (MAC, "playback", {"action": "setPosition", "chapter": chapter, "ms": 0})

    channel.playback(chapter=0)
    await _call(hass, SERVICE_MEDIA_NEXT_TRACK)
    await _call(hass, SERVICE_MEDIA_PREVIOUS_TRACK)
    channel.playback(chapter=1)
    await _call(hass, SERVICE_MEDIA_NEXT_TRACK)
    await _call(hass, SERVICE_MEDIA_PREVIOUS_TRACK)
    channel.playback(chapter=None)
    await _call(hass, SERVICE_MEDIA_NEXT_TRACK)
    # A figure the library does not know has no limit
    channel.playback(tonie_id="unknown-figure", chapter=1)
    await _call(hass, SERVICE_MEDIA_NEXT_TRACK)
    assert channel.commands == [jump(1), jump(0), jump(1), jump(0), jump(1), jump(2)]


async def test_player_command_errors(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A command the channel cannot deliver is an error that names the cause."""
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, SERVICE_MEDIA_PLAY)
    assert err.value.translation_key == "command_failed"

    push.last.connect()
    push.last.command_error = CloudConnectionError("Command playback not sent: broker gone")
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, SERVICE_MEDIA_PAUSE)
    assert err.value.translation_key == "command_failed"
    assert err.value.translation_placeholders == {"error": "Command playback not sent: broker gone"}
    assert push.last.commands == []


async def test_player_without_mac(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A box the cloud lists without a MAC cannot be addressed."""
    push.last.connect()
    del cloud.main.box(BOX_ID)["macAddress"]
    await setup_entry.runtime_data.coordinator.async_refresh()
    assert push.last.macs == set()
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, SERVICE_MEDIA_PLAY)
    assert err.value.translation_key == "box_unknown"


async def test_push_channel_loss_pauses_the_player(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Without the channel nothing is known about playing, so the player shows paused."""
    push.last.connect()
    push.last.playback(paused=False)
    assert _player(hass).state == "playing"
    assert setup_entry.runtime_data.coordinator.data.push_connected
    push.last.connect(False)
    assert _player(hass).state == "paused"
    assert not setup_entry.runtime_data.coordinator.data.push_connected
    assert _state(hass, "binary_sensor", f"{BOX_ID}_connectivity").state == STATE_ON


# -- figure event --


async def test_figure_events(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Placing and removing a figure fire named events; nothing fires when nothing changed."""
    event = entity_id(hass, "event", f"{BOX_ID}_figure")
    assert hass.states.get(event).state == STATE_UNKNOWN

    # The cloud already said this figure stands on the box
    push.last.playback(tonie_id=TONIE_ID)
    assert hass.states.get(event).state == STATE_UNKNOWN

    push.last.removed()
    removed = hass.states.get(event)
    assert removed.state != STATE_UNKNOWN
    assert removed.attributes["event_type"] == "removed"
    assert removed.attributes["tonie_id"] == TONIE_ID
    assert removed.attributes["tonie"] == TONIE_NAME

    push.last.playback(tonie_id=CREATIVE_ID)
    placed = hass.states.get(event)
    assert placed.attributes["event_type"] == "placed"
    assert placed.attributes["tonie_id"] == CREATIVE_ID
    assert placed.attributes["tonie"] == CREATIVE_NAME

    push.last.playback(tonie_id="unknown-figure")
    unknown = hass.states.get(event)
    assert unknown.attributes["event_type"] == "placed"
    assert unknown.attributes["tonie_id"] == "unknown-figure"
    assert unknown.attributes["tonie"] is None

    push.last.battery(50, "full")
    push.last.playback(tonie_id="unknown-figure", paused=True)
    unchanged = hass.states.get(event)
    assert unchanged.state == unknown.state
    assert unchanged.attributes == unknown.attributes
