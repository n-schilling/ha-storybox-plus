"""The page in the sidebar: served once, shared by the accounts, removed with the last."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any
from unittest.mock import patch

from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.components import panel_custom
from homeassistant.components.frontend import DATA_PANELS, async_panel_exists
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component

from custom_components.storybox_plus import frontend, websocket
from custom_components.storybox_plus.const import (
    DOMAIN,
    FRONTEND_URL_BASE,
    PANEL_ELEMENT,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
)
from custom_components.storybox_plus.frontend import DATA_STATIC, PANEL_PATH, async_unregister_panel

from .conftest import FakeCloud, PushChannels, entry_for


async def test_panel_is_registered_for_admins(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The panel loads our module, with a hash of the scripts it uses, and is for administrators only."""
    folder = Path(frontend.__file__).parent / "frontend"
    combined = hashlib.sha256()
    for script in sorted(folder.glob("*.js")):
        combined.update(script.read_bytes())
    digest = combined.hexdigest()[:12]
    assert (folder / PANEL_FILENAME).exists()
    assert async_panel_exists(hass, PANEL_URL_PATH)
    panel = hass.data[DATA_PANELS][PANEL_URL_PATH]
    assert panel.component_name == "custom"
    assert panel.sidebar_title == PANEL_TITLE
    assert panel.sidebar_icon == PANEL_ICON
    assert panel.require_admin is True
    assert panel.config["_panel_custom"]["name"] == PANEL_ELEMENT
    assert panel.config["_panel_custom"]["module_url"] == f"{PANEL_PATH}?v={digest}"
    assert panel.config["_panel_custom"]["embed_iframe"] is False
    assert hass.data[DATA_STATIC] is True


async def test_static_path_once_and_panel_after_reload(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """The files are served from the integration's folder, registered once per run."""
    assert await async_setup_component(hass, "http", {})
    config_entry.add_to_hass(hass)
    with patch.object(
        hass.http, "async_register_static_paths", wraps=hass.http.async_register_static_paths
    ) as register:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert async_panel_exists(hass, PANEL_URL_PATH)
        await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done()
    assert register.await_count == 1
    (config,) = register.await_args.args[0]
    assert config.url_path == FRONTEND_URL_BASE
    assert config.path.endswith("/custom_components/storybox_plus/frontend")
    assert config.cache_headers is False
    assert async_panel_exists(hass, PANEL_URL_PATH)
    assert hass.data[DATA_PANELS][PANEL_URL_PATH].config["_panel_custom"]["name"] == PANEL_ELEMENT


async def test_panel_shared_by_accounts(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A second account does not register the panel again; the last one removes it."""
    second = entry_for(cloud.add_account("second", households=[{"id": "hh2", "name": "Zwei"}]))
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.storybox_plus.frontend.panel_custom.async_register_panel",
        wraps=panel_custom.async_register_panel,
    ) as register:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        second.add_to_hass(hass)
        assert await hass.config_entries.async_setup(second.entry_id)
        await hass.async_block_till_done()
    assert register.await_count == 1
    assert async_panel_exists(hass, PANEL_URL_PATH)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert async_panel_exists(hass, PANEL_URL_PATH)
    assert await hass.config_entries.async_unload(second.entry_id)
    assert not async_panel_exists(hass, PANEL_URL_PATH)


async def test_unregister_without_panel(hass: HomeAssistant) -> None:
    """Removing a panel that is not there is harmless."""
    async_unregister_panel(hass)
    assert not async_panel_exists(hass, PANEL_URL_PATH)


async def test_page_gets_the_version_of_the_manifest(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """The overview carries the manifest's version, and a commit only for a test deployment."""
    integration = await async_get_integration(hass, DOMAIN)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
    about = (await client.receive_json())["result"]["about"]
    assert about == {"version": str(integration.version), "commit": None}
    # A test deployment wrote the commit next to the files
    (tmp_path / "BUILD").write_text("abc1234\n", encoding="utf-8")
    monkeypatch.setattr(websocket, "__file__", str(tmp_path / "websocket.py"))
    hass.data.pop(websocket.DATA_ABOUT)
    await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
    about = (await client.receive_json())["result"]["about"]
    assert about == {"version": str(integration.version), "commit": "abc1234"}


def test_page_keeps_no_version_of_its_own() -> None:
    """The page shows the version it is told; the script names none, so nothing drifts."""
    script = (Path(frontend.__file__).parent / "frontend" / PANEL_FILENAME).read_text()
    assert not re.search(r"\b\d+\.\d+\.\d+\b", script)


def _language_keys(shared: str, language: str) -> list[str]:
    """The keys of one language of the texts, in order, each as often as it is written."""
    start = shared.index(f"\n  {language}: {{\n")
    end = shared.index("\n  },", start)
    body = shared[start:end]
    return re.findall(r'(?:^|", |\{ )\s*([A-Za-z_][A-Za-z0-9_]*): "', body, re.MULTILINE)


def test_texts_have_each_key_once_in_both_languages() -> None:
    """A key written twice silently takes the later text; both languages have the same keys."""
    shared = (Path(frontend.__file__).parent / "frontend" / "storybox-plus-common.js").read_text(
        encoding="utf-8"
    )
    english = _language_keys(shared, "en")
    german = _language_keys(shared, "de")
    assert len(english) > 300
    for keys in (english, german):
        twice = sorted({k for k in keys if keys.count(k) > 1})
        assert not twice, twice
    assert set(english) == set(german)


def test_page_is_built_from_home_assistants_elements() -> None:
    """The page uses Home Assistant's frame and elements, none of the look-alikes of before."""
    folder = Path(frontend.__file__).parent / "frontend"
    panel = (folder / PANEL_FILENAME).read_text(encoding="utf-8")
    shared = (folder / "storybox-plus-common.js").read_text(encoding="utf-8")
    for element in (
        "hass-tabs-subpage",
        "ha-tab-group",
        "ha-settings-row",
        "ha-tooltip",
        "ha-filter-chip",
        "ha-control-select",
        'slot="fab"',
    ):
        assert element in panel, element
    for gone in (
        "ha-top-app-bar-fixed",
        "ha-menu-button",
        "bottom-tabs",
        'class="ov',
        "<button",
        "<select",
    ):
        assert gone not in panel + shared, gone
    assert "height: 100dvh" in shared
    assert 'class="about"' in panel
