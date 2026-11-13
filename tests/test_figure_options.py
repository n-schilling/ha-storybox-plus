"""Live mode of creative figures, shuffling on swap, and renaming a household."""

from __future__ import annotations

import random
from typing import Any

from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store

from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.shuffle import ShuffleOnSwap, new_order

from .conftest import CREATIVE_ID, DISC_ID, HOUSEHOLD_ID, TONIE_ID, FakeCloud, PushChannels, tune

THREE_CHAPTERS = [
    {"id": f"ch{i}", "title": f"Song {i}", "file": f"f{i}", "seconds": 60, "transcoding": False}
    for i in (1, 2, 3)
]


async def _setup(hass: HomeAssistant, cloud: FakeCloud, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    result: dict[str, Any] = await client.receive_json()
    return result


async def test_live_and_private(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Only the given fields go to the cloud; nothing to change is refused."""
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    result = await _call(
        client,
        {
            "type": f"{DOMAIN}/figure/update",
            "tonie_id": CREATIVE_ID,
            "live": True,
        },
    )
    assert result["success"], result
    assert cloud.renames == [(CREATIVE_ID, {"live": True})]
    assert result["result"]["live"] is True
    assert result["result"]["shuffle_on_swap"] is False
    result = await _call(client, {"type": f"{DOMAIN}/figure/update", "tonie_id": CREATIVE_ID})
    assert result["error"]["code"] == "invalid_format"


def test_new_order() -> None:
    """A shuffle always gives another order; one chapter cannot be shuffled."""
    ids = ["a", "b"]
    assert new_order(ids, random.Random(1)) == ["b", "a"]
    assert new_order(["a"]) == ["a"]
    assert sorted(new_order(["a", "b", "c"])) == ["a", "b", "c"]


async def test_shuffle_store(hass: HomeAssistant) -> None:
    """Only a replacement counts, across an empty box; the last figure survives a restart."""
    store: Store[dict[str, Any]] = Store(hass, 1, "storybox_plus.test.shuffle")
    await store.async_save({"tonies": ["c", 5], "last": {"box": "c", "bad": 3}})
    shuffles = ShuffleOnSwap(store)
    await shuffles.async_load()
    assert shuffles.enabled("c")
    assert shuffles.placed("box", None) is None
    assert shuffles.placed("box", "c") is None
    assert shuffles.placed("box", "t") == "c"
    assert shuffles.placed("box", "c") is None
    await shuffles.async_set("c", False)
    assert shuffles.placed("box", "t") is None
    await ShuffleOnSwap(Store(hass, 1, "storybox_plus.test.none")).async_load()


async def test_shuffled_when_replaced(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Taken off and put back: nothing; replaced by another figure: a new order."""
    cloud.main.creative_tonies[HOUSEHOLD_ID][0]["chapters"] = [dict(c) for c in THREE_CHAPTERS]
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    result = await _call(
        client,
        {"type": f"{DOMAIN}/figure/shuffle_on_swap", "tonie_id": CREATIVE_ID, "enabled": True},
    )
    assert result["result"] == {"shuffle_on_swap": True}
    channel = push.last
    channel.connect()
    channel.playback(CREATIVE_ID, chapter=0)
    channel.removed()
    channel.playback(CREATIVE_ID, chapter=0)
    channel.removed()
    await hass.async_block_till_done()
    assert cloud.chapter_patches == []
    channel.playback(TONIE_ID, chapter=0)
    await hass.async_block_till_done()
    assert len(cloud.chapter_patches) == 1
    order = [c["id"] for c in cloud.chapter_patches[0][2]["chapters"]]
    assert sorted(order) == ["ch1", "ch2", "ch3"]
    assert order != ["ch1", "ch2", "ch3"]
    library = await _call(client, {"type": f"{DOMAIN}/library"})
    creative = next(t for t in library["result"]["tonies"] if t["id"] == CREATIVE_ID)
    assert creative["shuffle_on_swap"] is True


async def test_not_shuffled_with_a_tune_or_on_another_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A figure a Tune lies on keeps its order; bought figures cannot be switched on."""
    cloud.main.creative_tonies[HOUSEHOLD_ID][0]["chapters"] = [dict(c) for c in THREE_CHAPTERS]
    cloud.main.tunes = [tune(assigned=(CREATIVE_ID,))]
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    await _call(
        client,
        {"type": f"{DOMAIN}/figure/shuffle_on_swap", "tonie_id": CREATIVE_ID, "enabled": True},
    )
    channel = push.last
    channel.connect()
    channel.playback(CREATIVE_ID, chapter=0)
    channel.playback(TONIE_ID, chapter=0)
    await hass.async_block_till_done()
    assert cloud.chapter_patches == []
    result = await _call(
        client,
        {"type": f"{DOMAIN}/figure/shuffle_on_swap", "tonie_id": DISC_ID, "enabled": True},
    )
    assert result["error"]["code"] == "not_creative"
    result = await _call(
        client, {"type": f"{DOMAIN}/figure/shuffle_on_swap", "tonie_id": "nope", "enabled": True}
    )
    assert result["error"]["code"] == "unknown_figure"


async def test_rename_household(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The household gets a new name; the entry and the account's device follow it."""
    await _setup(hass, cloud, config_entry)
    client = await hass_ws_client(hass)
    result = await _call(
        client,
        {"type": f"{DOMAIN}/household/rename", "household_id": HOUSEHOLD_ID, "name": " Home "},
    )
    assert result["result"] == {"entry_title": "Home"}
    assert cloud.household_patches == [(HOUSEHOLD_ID, {"name": "Home"})]
    assert config_entry.title == "Home"
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), config_entry.entry_id)
    account = next(d for d in devices if (DOMAIN, config_entry.entry_id) in d.identifiers)
    assert account.name == "Home"
    # A title given by hand stays
    hass.config_entries.async_update_entry(config_entry, title="Mine")
    await _call(
        client,
        {"type": f"{DOMAIN}/household/rename", "household_id": HOUSEHOLD_ID, "name": "Again"},
    )
    assert config_entry.title == "Mine"
    result = await _call(
        client, {"type": f"{DOMAIN}/household/rename", "household_id": "nope", "name": "X"}
    )
    assert result["error"]["code"] == "unknown_household"
    cloud.main.rest_status = 500
    result = await _call(
        client, {"type": f"{DOMAIN}/household/rename", "household_id": HOUSEHOLD_ID, "name": "X"}
    )
    assert result["error"]["code"] == "cloud_error"
