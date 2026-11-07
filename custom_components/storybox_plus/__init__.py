"""Storybox Plus: the Toniebox in Home Assistant, through its cloud.

A config entry is one cloud account. Its boxes become devices with a few
entities; the figures and the listening statistics live on the page.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import client_context

from .analytics import Analytics, AnalyticsData
from .battery import BatteryStats
from .cloud import Auth, CloudAuthError, CloudClient, CloudError, PushClient, PushEvent, TokenSet
from .const import (
    CONF_ANALYTICS,
    CONF_REFRESH_TOKEN,
    CONF_USER_ID,
    DEFAULT_ANALYTICS,
    DOMAIN,
    STORAGE_VERSION,
)
from .coordinator import RuntimeData, StoryboxConfigEntry, StoryboxCoordinator
from .favourites import FavouriteChapters
from .frontend import async_register_frontend, async_unregister_panel
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
]


def analytics_store(hass: HomeAssistant, entry_id: str) -> Store[AnalyticsData]:
    """Return the store of the listening sums of an entry."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.analytics")


def details_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Return the store of the chapters learned from the boxes."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.chapters")


def battery_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Return the store of the battery cycles."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.battery")


def favourites_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Return the store of the favourite chapters."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.favourites")


async def async_setup_entry(hass: HomeAssistant, entry: StoryboxConfigEntry) -> bool:
    """Set up one cloud account."""
    session = async_get_clientsession(hass)

    @callback
    def _tokens_changed(tokens: TokenSet) -> None:
        """Keep the newest refresh token; the cloud rotates it with every refresh."""
        if entry.data.get(CONF_REFRESH_TOKEN) != tokens.refresh_token:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_REFRESH_TOKEN: tokens.refresh_token}
            )

    auth = Auth(session, entry.data[CONF_REFRESH_TOKEN], on_tokens=_tokens_changed)
    try:
        await auth.async_refresh()
    except CloudAuthError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="invalid_auth"
        ) from err
    except CloudError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"error": str(err)},
        ) from err
    client = CloudClient(session, auth)

    analytics: Analytics | None = None
    if entry.options.get(CONF_ANALYTICS, DEFAULT_ANALYTICS):
        analytics = Analytics(analytics_store(hass, entry.entry_id), dt_util.now)
        await analytics.async_load()
    else:
        await analytics_store(hass, entry.entry_id).async_remove()

    coordinator: StoryboxCoordinator

    @callback
    def _push_event(event: PushEvent) -> None:
        coordinator.handle_push(event)

    @callback
    def _push_connected(connected: bool) -> None:
        coordinator.set_push_connected(connected)

    push = PushClient(
        auth,
        entry.data[CONF_USER_ID],
        ssl_context=client_context(),
        on_event=_push_event,
        on_connected=_push_connected,
    )
    battery_stats = BatteryStats(battery_store(hass, entry.entry_id), dt_util.now)
    await battery_stats.async_load()
    favourites = FavouriteChapters(favourites_store(hass, entry.entry_id))
    await favourites.async_load()
    coordinator = StoryboxCoordinator(
        hass,
        entry,
        client,
        push,
        analytics,
        details_store(hass, entry.entry_id),
        battery_stats,
        favourites,
    )
    await coordinator.async_load_details()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = RuntimeData(
        auth=auth,
        client=client,
        push=push,
        coordinator=coordinator,
        analytics=analytics,
        battery_stats=battery_stats,
        favourites=favourites,
    )

    await async_register_frontend(hass)
    async_register_websocket(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        coordinator.async_add_listener(lambda: _remove_stale_devices(hass, entry))
    )
    _remove_stale_devices(hass, entry)

    async def _run_push() -> None:
        """Keep the push channel open; a refused login asks for a new one."""
        try:
            await push.async_run()
        except CloudAuthError:
            _LOGGER.debug("Push channel: the account needs a new login")
            entry.async_start_reauth(hass)

    entry.async_create_background_task(hass, _run_push(), f"{DOMAIN} push channel")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: StoryboxConfigEntry) -> bool:
    """Unload one cloud account."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    if entry.runtime_data.analytics is not None:
        await entry.runtime_data.analytics.async_save()
    await entry.runtime_data.battery_stats.async_save()
    if not any(e for e in hass.config_entries.async_loaded_entries(DOMAIN) if e is not entry):
        async_unregister_panel(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: StoryboxConfigEntry) -> None:
    """Forget the listening sums, the learned chapters and the favourites of a removed account."""
    await analytics_store(hass, entry.entry_id).async_remove()
    await details_store(hass, entry.entry_id).async_remove()
    await battery_store(hass, entry.entry_id).async_remove()
    await favourites_store(hass, entry.entry_id).async_remove()


@callback
def _remove_stale_devices(hass: HomeAssistant, entry: StoryboxConfigEntry) -> None:
    """Remove devices of boxes that left the account."""
    data = entry.runtime_data.coordinator.data
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        box_ids = {identifier[1] for identifier in device.identifiers if identifier[0] == DOMAIN}
        if box_ids and not box_ids & set(data.boxes):
            registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
