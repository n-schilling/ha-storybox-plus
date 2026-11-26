"""The dashboard card: served, loaded on every page and kept as a dashboard resource.

The tests of the resource need nothing of the integration but frontend.py; the
ones of the script read it as text, together with the module it loads.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE, MODE_YAML
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.storybox_plus import frontend
from custom_components.storybox_plus.frontend import CARD_FILENAME, CARD_PATH, DATA_CARD

CARD = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "storybox_plus"
    / "frontend"
    / CARD_FILENAME
)


def _lovelace(mode: str, resources: Any) -> MagicMock:
    data = MagicMock()
    data.resource_mode = mode
    data.resources = resources
    return data


def _collection(items: list[dict[str, Any]]) -> MagicMock:
    collection = MagicMock(spec=ResourceStorageCollection)
    collection.async_get_info = AsyncMock()
    collection.async_items = MagicMock(return_value=items)
    collection.async_create_item = AsyncMock()
    collection.async_update_item = AsyncMock()
    collection.async_delete_item = AsyncMock()
    return collection


async def test_card_loaded_and_resource_created(hass: HomeAssistant) -> None:
    """With the frontend there the card is loaded on every page and added to the resources."""
    assert await async_setup_component(hass, "http", {})
    collection = _collection([{"id": "1", "url": "/local/other.js", "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, collection)
    hass.data[DATA_EXTRA_MODULE_URL] = MagicMock()
    with patch(f"{frontend.__name__}.add_extra_js_url") as add_url:
        await frontend.async_register_card(hass)
    url = hass.data[DATA_CARD]
    assert url.startswith(f"{CARD_PATH}?v=")
    add_url.assert_called_once_with(hass, url)
    collection.async_create_item.assert_awaited_once_with({"res_type": "module", "url": url})
    collection.async_update_item.assert_not_awaited()

    # Loaded once per run: a second setup adds nothing to the pages
    with patch(f"{frontend.__name__}.add_extra_js_url") as add_url:
        await frontend.async_register_card(hass)
    add_url.assert_not_called()


async def test_card_resource_updated_and_removed(hass: HomeAssistant) -> None:
    """An entry of an earlier version is pointed to this one; removing takes it away."""
    assert await async_setup_component(hass, "http", {})
    await frontend.async_register_card(hass)
    url = hass.data[DATA_CARD]
    collection = _collection([{"id": "7", "url": f"{CARD_PATH}?v=old", "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, collection)
    await frontend.async_register_card(hass)
    collection.async_update_item.assert_awaited_once_with("7", {"url": url})
    collection.async_create_item.assert_not_awaited()

    await frontend.async_remove_card_resource(hass)
    collection.async_delete_item.assert_awaited_once_with("7")


async def test_card_resource_left_alone(hass: HomeAssistant) -> None:
    """Resources in YAML are the user's; a collection of another kind is left alone."""
    assert await async_setup_component(hass, "http", {})
    await frontend.async_register_card(hass)
    collection = _collection([{"id": "3", "url": hass.data[DATA_CARD], "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_YAML, collection)
    await frontend.async_register_card(hass)
    await frontend.async_remove_card_resource(hass)
    collection.async_create_item.assert_not_awaited()
    collection.async_delete_item.assert_not_awaited()

    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, MagicMock())
    await frontend.async_register_card(hass)
    await frontend.async_remove_card_resource(hass)


# The actions the card's buttons may call: only what every user may operate on a
# box's media player anyway (media control and its sleep timer)
ACTIONS = {
    "media_player.media_play",
    "media_player.media_pause",
    "media_player.media_next_track",
    "media_player.media_previous_track",
    "media_player.volume_up",
    "media_player.volume_down",
    "storybox_plus.set_sleep_timer",
    "storybox_plus.clear_sleep_timer",
}


# The subscriptions a view of the card may open: none, the card has no view with live data
SUBSCRIPTIONS: set[str] = set()


def test_card_reads_and_calls_only_what_is_listed() -> None:
    """The card and the module it loads call no command, and no action outside the controls."""
    card = CARD.read_text(encoding="utf-8")
    loaded = re.findall(r"`\./([\w-]+\.js)\$\{", card)
    assert loaded == ["storybox-plus-common.js"]
    code = card + "".join((CARD.parent / name).read_text(encoding="utf-8") for name in loaded)
    for call in ("callWS", "callApi", "fetch(", "sendMessage"):
        assert call not in code, call
    # Every subscription is one of the list; a card without a live view opens none
    subscribed = re.findall(r'subscribeMessage\([^;]*?\{ type: "([^"]+)" \}', code, re.DOTALL)
    assert code.count("subscribeMessage(") == len(subscribed)
    assert set(subscribed) == SUBSCRIPTIONS
    listed = re.search(r"const ACTIONS = \[(.*?)\];", code, re.DOTALL)
    assert listed is not None
    assert set(re.findall(r'"([a-z_]+\.[a-z_]+)"', listed.group(1))) == ACTIONS
    # One place calls, with an entry of the list
    assert code.count("callService") == 1


def test_card_has_a_field_and_a_text_for_every_option() -> None:
    """Every option the card reads is in its editor, with a label in both languages."""
    card = CARD.read_text(encoding="utf-8")
    shared = (CARD.parent / "storybox-plus-common.js").read_text(encoding="utf-8")
    listed = re.search(r"const PARTS = \[(.*?)\];", card)
    assert listed is not None
    parts = re.findall(r'"(\w+)"', listed.group(1))
    assert len(parts) == 9
    # The parts come from the one list: their options, their defaults, their fields
    assert "PARTS.map((part) => [`show_${part}`, !OFF.includes(part)])" in card
    # What only whoever set the box up reads is off until switched on
    assert 'const OFF = ["night_mode"];' in card
    assert "name: `show_${part}`" in card
    options = set(re.findall(r"\bc\.(\w+)", card))
    assert options >= {"entity", "title", "size"}
    for option in options:
        if option.startswith("show_"):
            assert option.removeprefix("show_") in parts, option
        else:
            assert f'name: "{option}"' in card, option
    for key in [f"show_{part}" for part in parts] + [
        "cardEntity",
        "cardTitle",
        "cardSize",
        "cardShow",
        "sizeAuto",
        "sizeSmall",
        "sizeMedium",
        "sizeLarge",
        "cardMissing",
        "cardUnknown",
    ]:
        assert shared.count(f'{key}: "') == 2, key
    # Works without any configuration, and is offered once
    assert re.search(r"static getStubConfig\(\) \{\s*return \{\};", card)
    assert card.count("window.customCards.push(") == 1
