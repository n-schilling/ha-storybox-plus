"""Serves the page, puts it into the sidebar of administrators, and offers the dashboard card."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import (
    add_extra_js_url,
    async_panel_exists,
    async_remove_panel,
    remove_extra_js_url,
)
from homeassistant.components.http.server import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import (
    DOMAIN,
    FRONTEND_URL_BASE,
    PANEL_ELEMENT,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
)

DATA_STATIC: HassKey[bool] = HassKey(f"{DOMAIN}_static")
# The address of the dashboard card while it is offered, to take it back
DATA_CARD: HassKey[str] = HassKey(f"{DOMAIN}_card")
PANEL_PATH = f"{FRONTEND_URL_BASE}/{PANEL_FILENAME}"
CARD_FILENAME = "storybox-plus-card.js"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the page once per run of Home Assistant and add it to the sidebar.

    The page stays as long as any account is loaded; unloading the last one
    takes it off the sidebar.
    """
    if DATA_STATIC not in hass.data:
        hass.data[DATA_STATIC] = True
        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL_BASE, str(Path(__file__).parent / "frontend"), False)]
        )
    if async_panel_exists(hass, PANEL_URL_PATH):
        return
    script = Path(__file__).parent / "frontend" / PANEL_FILENAME
    digest = await hass.async_add_executor_job(_digest, script)
    # The card loads with every dashboard, for every user; nothing has to be added by hand
    if "frontend" in hass.config.components:
        card = f"{FRONTEND_URL_BASE}/{CARD_FILENAME}?v={digest}"
        add_extra_js_url(hass, card)
        hass.data[DATA_CARD] = card
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        # The content hash makes browsers fetch every changed page, also within a version
        module_url=f"{PANEL_PATH}?v={digest}",
        require_admin=True,
    )


def _digest(path: Path) -> str:
    """A short hash of the scripts in the page's folder: the page and what it imports."""
    digest = hashlib.sha256()
    for script in sorted(path.parent.glob("*.js")):
        digest.update(script.read_bytes())
    return digest.hexdigest()[:12]


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Take the page off the sidebar and the card out of the dashboards."""
    async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    if (card := hass.data.pop(DATA_CARD, None)) is not None:
        remove_extra_js_url(hass, card)
