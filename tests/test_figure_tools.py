"""Chapters picked from the media browser, renamed creative figures, a volume per figure,
and the cloud's notifications passed on as events."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus import async_remove_config_entry_device
from custom_components.storybox_plus.const import DOMAIN, UPDATE_INTERVAL
from custom_components.storybox_plus.volumes import FigureVolumes

from .conftest import (
    BOX_ID,
    CREATIVE_ID,
    DISC_ID,
    MAC,
    TONIE_ID,
    TONIE_NAME,
    FakeCloud,
    PushChannels,
    entity_id,
)

# ---------------------------------------------------------------- the media browser


async def test_browse_and_play_a_chapter(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The chapters of the figure on the box are listed; playing one jumps to its start."""
    channel = push.last
    channel.connect()
    channel.playback(TONIE_ID, chapter=0)
    player = entity_id(hass, "media_player", BOX_ID)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "media_player/browse_media", "entity_id": player})
    result = await client.receive_json()
    assert result["success"], result
    browse = result["result"]
    assert browse["title"] == TONIE_NAME
    assert [c["media_content_id"] for c in browse["children"]][:2] == [
        f"chapter:{TONIE_ID}:0",
        f"chapter:{TONIE_ID}:1",
    ]
    assert browse["children"][0]["title"].startswith("1. ")
    await hass.services.async_call(
        "media_player",
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": player,
            ATTR_MEDIA_CONTENT_ID: f"chapter:{TONIE_ID}:1",
            ATTR_MEDIA_CONTENT_TYPE: "track",
        },
        blocking=True,
    )
    assert channel.commands[-1] == (
        MAC,
        "playback",
        {"action": "setPosition", "chapter": 1, "ms": 0},
    )


@pytest.mark.parametrize(
    ("media_id", "key"),
    [
        (f"chapter:{TONIE_ID}:99", "unknown_chapter"),
        (f"chapter:{TONIE_ID}:x", "unknown_chapter"),
        ("something:else", "unknown_chapter"),
        (f"chapter:{CREATIVE_ID}:0", "other_figure"),
    ],
)
async def test_play_refusals(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    media_id: str,
    key: str,
) -> None:
    """A chapter the figure lacks, or one of another figure, is refused."""
    push.last.connect()
    push.last.playback(TONIE_ID, chapter=0)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            "media_player",
            SERVICE_PLAY_MEDIA,
            {
                "entity_id": entity_id(hass, "media_player", BOX_ID),
                ATTR_MEDIA_CONTENT_ID: media_id,
                ATTR_MEDIA_CONTENT_TYPE: "track",
            },
            blocking=True,
        )
    assert err.value.translation_key == key


async def test_browse_without_figure(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Nothing on the box: nothing to browse."""
    push.last.connect()
    push.last.removed()
    player = hass.data["entity_components"]["media_player"].get_entity(
        entity_id(hass, "media_player", BOX_ID)
    )
    with pytest.raises(HomeAssistantError):
        await player.async_browse_media()


# ---------------------------------------------------------------- renaming


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


async def test_rename_creative_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A creative figure gets a new name; the cloud converts nothing for it."""
    client = await hass_ws_client(hass)
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/update", "tonie_id": CREATIVE_ID, "name": " Lullabies "}
    )
    assert result["success"], result
    assert result["result"]["name"] == "Lullabies"
    assert cloud.renames == [(CREATIVE_ID, {"name": "Lullabies"})]
    assert cloud.chapter_patches == []
    assert setup_entry.runtime_data.coordinator.data.tonies[CREATIVE_ID].name == "Lullabies"


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ({"tonie_id": TONIE_ID, "name": "x"}, "not_creative"),
        ({"tonie_id": "nope", "name": "x"}, "unknown_figure"),
        ({"tonie_id": CREATIVE_ID, "name": "  "}, "invalid_format"),
    ],
)
async def test_rename_refusals(
    hass: HomeAssistant,
    cloud: FakeCloud,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Bought figures keep their names; unknown figures and empty names are refused."""
    client = await hass_ws_client(hass)
    result = await _call(client, {"type": f"{DOMAIN}/figure/update", **message})
    assert result["error"]["code"] == code
    assert cloud.renames == []


# ---------------------------------------------------------------- volume per figure


def _volumes(push: PushChannels) -> list[int]:
    return [p["level"] for _m, c, p in push.last.commands if c == "volume"]


async def _set_volume(client: Any, tonie_id: str, level: int | None) -> dict[str, Any]:
    return await _call(
        client, {"type": f"{DOMAIN}/figure/volume", "tonie_id": tonie_id, "level": level}
    )


async def test_figure_volume_set_and_restored(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Placed: the figure's level; taken off: the level from before, whatever was turned."""
    client = await hass_ws_client(hass)
    result = await _set_volume(client, DISC_ID, 4)
    assert result["result"] == {"volume": 4}
    channel = push.last
    channel.connect()
    channel.removed()
    channel.volume(9)
    channel.playback(DISC_ID, chapter=0)
    await hass.async_block_till_done()
    assert _volumes(push) == [4]
    # Turned at the box meanwhile; taking the figure off still brings 9 back
    channel.volume(6)
    channel.removed()
    await hass.async_block_till_done()
    assert _volumes(push) == [4, 9]
    library = await _call(client, {"type": f"{DOMAIN}/library"})
    disc = next(t for t in library["result"]["tonies"] if t["id"] == DISC_ID)
    assert disc["volume"] == 4


async def test_figure_volume_chain_and_level_change(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Figure after figure starts from the level before the first; a new level applies at once."""
    client = await hass_ws_client(hass)
    await _set_volume(client, DISC_ID, 4)
    await _set_volume(client, CREATIVE_ID, 11)
    channel = push.last
    channel.connect()
    channel.removed()
    channel.volume(8)
    channel.playback(DISC_ID, chapter=0)
    channel.volume(4)
    channel.playback(CREATIVE_ID, chapter=0)
    channel.volume(11)
    channel.playback(TONIE_ID, chapter=0)
    await hass.async_block_till_done()
    assert _volumes(push) == [4, 11, 8]
    # A level set while the figure stands on the box applies now; removed, 8 comes back
    channel.volume(8)
    channel.playback(DISC_ID, chapter=0)
    channel.volume(4)
    await _set_volume(client, DISC_ID, 2)
    await hass.async_block_till_done()
    assert _volumes(push)[-1] == 2
    await _set_volume(client, DISC_ID, None)
    await hass.async_block_till_done()
    assert _volumes(push)[-1] == 8


async def test_figure_volume_unknown_box_level(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Without the box's level the figure's is not set: it could not be undone."""
    client = await hass_ws_client(hass)
    await _set_volume(client, DISC_ID, 4)
    channel = push.last
    channel.connect()
    channel.removed()
    channel.playback(DISC_ID, chapter=0)
    channel.removed()
    await hass.async_block_till_done()
    assert _volumes(push) == []


async def test_figure_volume_refusals(
    hass: HomeAssistant, setup_entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Unknown figures and levels beyond the box's 13 steps are refused."""
    client = await hass_ws_client(hass)
    assert (await _set_volume(client, "nope", 3))["error"]["code"] == "unknown_figure"
    assert (await _set_volume(client, DISC_ID, 14))["error"]["code"] == "invalid_format"
    assert (await _set_volume(client, DISC_ID, 0))["error"]["code"] == "invalid_format"


async def test_figure_volume_store(hass: HomeAssistant) -> None:
    """Levels and the levels to restore survive a restart; what does not fit is left out."""
    store: Store[dict[str, Any]] = Store(hass, 1, "storybox_plus.test.volumes")
    await store.async_save(
        {
            "tonies": {"a": 5, "b": 20, "c": "x"},
            "boxes": {"box": {"tonie": "a", "previous": 9}, "bad": 1},
        }
    )
    volumes = FigureVolumes(store)
    await volumes.async_load()
    assert volumes.get("a") == 5
    assert volumes.get("b") is None
    assert volumes.raised("box") == "a"
    assert volumes.raised("bad") is None
    # The figure leaves after the restart: its level from before comes back
    assert volumes.placed("box", None, 5) == 9
    assert volumes.raised("box") is None
    await FigureVolumes(Store(hass, 1, "storybox_plus.test.none")).async_load()


# ---------------------------------------------------------------- notifications


def _notice(notice_id: str, text: str, read: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "id": notice_id,
        "text": text,
        "read": read,
        "timestamp": "2026-11-12T08:00:00Z",
        "ntype": "tonie_transcoding_failed",
        **extra,
    }


async def test_notices_passed_on_once(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
) -> None:
    """Unread notifications and broadcasts fire once each, oldest first; read ones never."""
    cloud.main.notices = [
        _notice(
            "n2",
            "Second",
            timestamp="2026-11-12T09:00:00Z",
            tonieId=CREATIVE_ID,
            tonieReason="tooLong",
        ),
        _notice("n1", "First"),
        _notice("n0", "Already read", read=True),
    ]
    cloud.main.system_notices = [{"id": "s1", "translatedText": "Maintenance tonight"}]
    config_entry.add_to_hass(hass)
    seen: list[dict[str, Any]] = []
    stamps: set[str] = set()

    # A callback runs in the event loop, in the order of the events; a plain function
    # would run in the executor, where the order is left to the threads
    @callback
    def note(event: Any) -> None:
        # One entry per event fired; the state an entity gets back after a reload is none
        state = event.data["new_state"]
        if not event.data["entity_id"].endswith("_notification") or state is None:
            return
        if state.attributes.get("event_type") != "notification" or state.state in stamps:
            return
        stamps.add(state.state)
        seen.append(dict(state.attributes))

    hass.bus.async_listen("state_changed", note)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    fired = [a for a in seen if a.get("event_type") == "notification"]
    assert [a["text"] for a in fired] == ["First", "Second", "Maintenance tonight"]
    assert fired[1]["tonie_id"] == CREATIVE_ID
    assert fired[1]["tonie"] == "Kreativ"
    assert fired[1]["reason"] == "tooLong"
    assert fired[1]["kind"] == "tonie_transcoding_failed"
    assert fired[1]["time"] == "2026-11-12T09:00:00+00:00"
    assert fired[2]["kind"] == "system"
    # The next poll passes nothing on again; a new one goes, the gone ones are forgotten
    cloud.main.notices = [_notice("n1", "First"), _notice("n3", "Third")]
    cloud.main.system_notices = []
    async_fire_time_changed(hass, dt_util.utcnow() + UPDATE_INTERVAL + timedelta(seconds=1))
    await hass.async_block_till_done()
    fired = [a for a in seen if a.get("event_type") == "notification"]
    assert [a["text"] for a in fired][3:] == ["Third"]
    # After a restart the store keeps them from coming again
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    fired = [a for a in seen if a.get("event_type") == "notification"]
    assert len(fired) == 4


async def test_notices_read_failure_costs_nothing(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
) -> None:
    """When the notifications cannot be read, the poll still succeeds."""
    cloud.main.notices_status = 500
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.runtime_data.coordinator.last_update_success


async def test_account_device_stays(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """The account's device is no box: polls keep it, and it cannot be removed by hand."""
    registry = dr.async_get(hass)

    def account_device() -> dr.DeviceEntry | None:
        return next(
            (
                d
                for d in dr.async_entries_for_config_entry(registry, setup_entry.entry_id)
                if (DOMAIN, setup_entry.entry_id) in d.identifiers
            ),
            None,
        )

    account = account_device()
    assert account is not None
    assert account.entry_type is dr.DeviceEntryType.SERVICE
    coordinator = setup_entry.runtime_data.coordinator
    for _ in range(14):
        await coordinator.async_refresh()
    assert account_device() is not None
    assert not await async_remove_config_entry_device(hass, setup_entry, account)
