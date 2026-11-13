"""The settings tab: locking new figures, notifications marked as read; box names, pictures
and the cloud's version."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store

from custom_components.storybox_plus.cloud import Tonie, TonieKind
from custom_components.storybox_plus.const import CLOUD_INFO_INTERVAL, DOMAIN
from custom_components.storybox_plus.preferences import Preferences

from .conftest import (
    BACKEND_VERSION,
    BOX_ID,
    CREATIVE_ID,
    DISC_ID,
    TONIE_ID,
    FakeCloud,
    PushChannels,
    content_tonie,
    device,
)


def _tonie(tonie_id: str, kind: TonieKind = TonieKind.CONTENT, locked: bool = False) -> Tonie:
    return Tonie(id=tonie_id, household_id="hh", kind=kind, name=tonie_id, locked=locked)


async def test_to_lock(hass: HomeAssistant) -> None:
    """The first run's figures are known; later only new unlocked ones are locked, once."""
    store: Store[dict[str, Any]] = Store(hass, 1, "storybox_plus.test.settings")
    prefs = Preferences(store)
    await prefs.async_load()
    assert prefs.as_dict() == {"analytics": True, "auto_lock": True, "mark_read": False}
    assert prefs.to_lock([_tonie("old"), _tonie("c", TonieKind.CREATIVE)]) == []
    new, locked_already, disc = (
        _tonie("new"),
        _tonie("lk", locked=True),
        _tonie("d", TonieKind.DISC),
    )
    assert prefs.to_lock([_tonie("old"), new, locked_already, disc]) == [new, disc]
    # Not locked yet (refused): asked again; once locked, never again
    assert prefs.to_lock([new]) == [new]
    prefs.locked("new")
    assert prefs.to_lock([new]) == []
    # Switched off: new ones are only noted, also for later
    await prefs.async_set(False, True)
    assert prefs.to_lock([_tonie("later")]) == []
    await prefs.async_set(True, None)
    assert prefs.to_lock([_tonie("later")]) == []
    await prefs.async_save()
    again = Preferences(Store(hass, 1, "storybox_plus.test.settings"))
    await again.async_load()
    assert again.as_dict() == {"analytics": True, "auto_lock": True, "mark_read": True}
    assert again.to_lock([_tonie("old"), _tonie("later"), _tonie("newest")]) == [_tonie("newest")]


async def _setup(
    hass: HomeAssistant, config_entry: MockConfigEntry, settings: dict[str, Any] | None = None
) -> None:
    if settings is not None:
        await Store(hass, 1, f"storybox_plus.{config_entry.entry_id}.settings").async_save(settings)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_new_figures_locked_by_the_poll(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """The figures of the first run stay as they are; a new bought figure gets locked."""
    await _setup(hass, config_entry)
    assert cloud.lock_patches == []
    cloud.main.content_tonies.append(content_tonie("t-new", "New figure"))
    coordinator = config_entry.runtime_data.coordinator
    cloud.main.lock_status = 500
    await coordinator.async_refresh()
    assert cloud.lock_patches == []
    assert coordinator.data.tonies["t-new"].locked is False
    cloud.main.lock_status = None
    await coordinator.async_refresh()
    assert cloud.lock_patches == [("contenttonies", "t-new", {"lock": True})]
    assert coordinator.data.tonies["t-new"].locked is True
    await coordinator.async_refresh()
    assert len(cloud.lock_patches) == 1


async def test_no_lock_when_switched_off(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Switched off in the settings, a new figure is not locked."""
    await _setup(hass, config_entry, {"auto_lock": False, "mark_read": False, "known": [TONIE_ID]})
    assert cloud.lock_patches == []


async def test_lock_and_unlock_by_hand(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A figure unlocked by hand stays unlocked; creative figures have no lock."""
    await _setup(hass, config_entry)
    client = await hass_ws_client(hass)

    async def call(message: dict[str, Any]) -> dict[str, Any]:
        await client.send_json_auto_id(message)
        result: dict[str, Any] = await client.receive_json()
        return result

    result = await call({"type": f"{DOMAIN}/figure/lock", "tonie_id": DISC_ID, "locked": False})
    assert result["result"] == {"locked": False}
    assert cloud.lock_patches == [("discs", DISC_ID, {"lock": False})]
    await config_entry.runtime_data.coordinator.async_refresh()
    assert len(cloud.lock_patches) == 1
    result = await call({"type": f"{DOMAIN}/figure/lock", "tonie_id": CREATIVE_ID, "locked": True})
    assert result["error"]["code"] == "not_lockable"
    result = await call({"type": f"{DOMAIN}/figure/lock", "tonie_id": "nope", "locked": True})
    assert result["error"]["code"] == "unknown_figure"
    cloud.main.lock_status = 400
    result = await call({"type": f"{DOMAIN}/figure/lock", "tonie_id": TONIE_ID, "locked": True})
    assert result["error"]["code"] == "cloud_error"


async def test_preferences_set(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The settings tab changes the preferences of a loaded account."""
    await _setup(hass, config_entry)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/preferences/set", "entry_id": config_entry.entry_id, "mark_read": True}
    )
    result = await client.receive_json()
    assert result["result"] == {"analytics": True, "auto_lock": True, "mark_read": True}
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/preferences/set", "entry_id": "nope", "auto_lock": False}
    )
    result = await client.receive_json()
    assert result["error"]["code"] == "unknown_entry"


async def test_notices_marked_read(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """With the preference on, a passed-on notification is marked read, a broadcast dismissed."""
    cloud.main.notices = [{"id": "n1", "text": "Hello", "read": False, "ntype": "news"}]
    cloud.main.system_notices = [{"id": "s1", "translatedText": "Maintenance"}]
    await _setup(hass, config_entry, {"auto_lock": True, "mark_read": True, "known": []})
    assert cloud.notice_changes == [
        ("PATCH", "/notifications/n1", {"read": True}),
        ("DELETE", "/system-notifications/s1", None),
    ]


async def test_notices_not_marked_by_default(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """By default nothing changes in the cloud."""
    cloud.main.notices = [{"id": "n1", "text": "Hello", "read": False, "ntype": "news"}]
    await _setup(hass, config_entry)
    assert cloud.notice_changes == []


async def test_box_name_follows_the_cloud(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Renamed on the page or in the app, the box's device takes the name; a user's name wins."""
    await _setup(hass, config_entry)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/box/settings", "box_id": BOX_ID, "name": "Nursery"}
    )
    assert (await client.receive_json())["success"]
    assert device(hass, config_entry, BOX_ID).name == "Nursery"
    cloud.main.box(BOX_ID)["name"] = "Play room"
    await config_entry.runtime_data.coordinator.async_refresh()
    box_device = device(hass, config_entry, BOX_ID)
    assert box_device.name == "Play room"
    dr.async_get(hass).async_update_device(box_device.id, name_by_user="Mine")
    cloud.main.box(BOX_ID)["name"] = "Other"
    await config_entry.runtime_data.coordinator.async_refresh()
    assert device(hass, config_entry, BOX_ID).name_by_user == "Mine"


async def test_cloud_version_and_pictures_hourly(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The version and the pictures are read at the start and then once an hour."""
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.backend_version == BACKEND_VERSION
    assert coordinator.backend_tested
    assert coordinator.box_pictures == {"red": "https://img.example.com/box-red.png"}
    await coordinator.async_refresh()
    assert cloud.version_calls == 1
    cloud.version = "v2027.01.01/abc"
    freezer.tick(CLOUD_INFO_INTERVAL + timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    await coordinator.async_refresh()
    assert coordinator.backend_version == "v2027.01.01/abc"
    assert coordinator.backend_release == "v2027.01.01"
    assert not coordinator.backend_tested


@pytest.mark.parametrize("version", [None, ""])
async def test_cloud_version_unreadable(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    version: str | None,
) -> None:
    """A version that cannot be read stays unknown and costs the poll nothing."""
    cloud.version = version
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.backend_version is None
    assert coordinator.last_update_success
