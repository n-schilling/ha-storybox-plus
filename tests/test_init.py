"""Setup, polling, token handling, unload and removal of an account."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.storybox_plus.cloud import CloudAuthError
from custom_components.storybox_plus.const import (
    CONF_REFRESH_TOKEN,
    DOMAIN,
    RETRY_INTERVAL,
    STALE_AFTER_POLLS,
    UPDATE_INTERVAL,
)
from custom_components.storybox_plus.frontend import PANEL_URL_PATH
from custom_components.storybox_plus.ids import box_identifier

from .conftest import (
    BOX_ID,
    CLASSIC_BOX_ID,
    HOUSEHOLD_ID,
    MAC,
    FakeCloud,
    PushChannels,
    counting_off,
    device,
    entity_id,
    entry_for,
    tb2_box,
)


def _analytics_key(entry: MockConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}.analytics"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory, interval: timedelta) -> None:
    """Let the coordinator's next poll happen."""
    freezer.tick(interval + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_setup_creates_devices_and_entities(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A Toniebox 2 becomes a device; a Toniebox 1 reports nothing live and gets none."""
    assert setup_entry.state is ConfigEntryState.LOADED
    tb2 = device(hass, setup_entry, BOX_ID)
    assert tb2 is not None
    assert tb2.name == "Kinderzimmer"
    assert tb2.manufacturer == "tonies"
    assert tb2.model == "Toniebox 2"
    assert tb2.sw_version == "1.2.3"
    assert tb2.connections == {(dr.CONNECTION_NETWORK_MAC, "a1:b2:c3:d4:e5:f6")}
    assert device(hass, setup_entry, CLASSIC_BOX_ID) is None

    entities = er.async_entries_for_config_entry(er.async_get(hass), setup_entry.entry_id)
    assert {e.unique_id.removeprefix(f"{setup_entry.entry_id}_") for e in entities} == {
        BOX_ID,
        f"{BOX_ID}_connectivity",
        f"{BOX_ID}_charging",
        f"{BOX_ID}_battery",
        f"{BOX_ID}_figure",
        "notification",
        "live_channel",
    }
    assert all(e.unique_id.startswith(f"{setup_entry.entry_id}_") for e in entities)
    assert hass.states.get(entity_id(hass, "binary_sensor", f"{BOX_ID}_connectivity")).name == (
        "Kinderzimmer Connectivity"
    )
    # The push channel listens to the Toniebox 2 only
    assert push.last.macs == {MAC}
    assert push.last.runs == 1
    # The setup rotated the refresh token and kept the new one
    assert cloud.main.tokens_issued == 1
    assert setup_entry.data[CONF_REFRESH_TOKEN] == cloud.main.refresh_token
    assert setup_entry.data[CONF_REFRESH_TOKEN] != "refresh-main-0"


async def test_refused_refresh_token_asks_for_login(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A refresh token the login server refuses starts the reauth flow."""
    cloud.main.refresh_refused = True
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert flows[0]["context"]["entry_id"] == config_entry.entry_id
    assert not push.instances


async def test_unreachable_login_server_retries(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Without a connection the setup is retried later, no login is asked for."""
    cloud.unreachable = True
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)


async def test_rejected_api_token_asks_for_login(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """An API that rejects even a fresh token during the first poll starts the reauth flow."""
    cloud.main.rest_status = 401
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]
    # The token was refreshed once more before giving up
    assert cloud.main.tokens_issued == 2


async def test_unreachable_api_retries(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A login that works but an API that does not makes the setup retry."""
    cloud.main.rest_unreachable = True
    config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_token_rotation_during_poll_is_stored(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """An expired access token is renewed in a poll; the rotated refresh token lands in the entry."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert cloud.main.tokens_issued == 1
    stored = config_entry.data[CONF_REFRESH_TOKEN]

    await _poll(hass, freezer, UPDATE_INTERVAL)
    assert cloud.main.tokens_issued == 2
    assert config_entry.data[CONF_REFRESH_TOKEN] == cloud.main.refresh_token
    assert config_entry.data[CONF_REFRESH_TOKEN] != stored
    # The old refresh token is of no use any more
    assert "refresh-main-0" not in str(config_entry.data)


async def test_api_rejecting_token_once_is_retried(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """A 401 from the API makes the client refresh once and repeat the request."""
    cloud.expire_access_tokens()
    coordinator = setup_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert cloud.main.tokens_issued == 2


async def test_poll_failures_keep_values_then_make_unavailable(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Two failed polls keep the last values and retry every minute; the third makes entities unavailable."""
    connectivity = entity_id(hass, "binary_sensor", f"{BOX_ID}_connectivity")
    coordinator = setup_entry.runtime_data.coordinator
    cloud.main.rest_unreachable = True

    await _poll(hass, freezer, UPDATE_INTERVAL)
    assert hass.states.get(connectivity).state == "on"
    assert coordinator.update_interval == RETRY_INTERVAL
    await _poll(hass, freezer, RETRY_INTERVAL)
    assert hass.states.get(connectivity).state == "on"
    await _poll(hass, freezer, RETRY_INTERVAL)
    assert hass.states.get(connectivity).state == STATE_UNAVAILABLE

    cloud.main.rest_unreachable = False
    await _poll(hass, freezer, RETRY_INTERVAL)
    assert hass.states.get(connectivity).state == "on"
    assert coordinator.update_interval == UPDATE_INTERVAL


async def test_poll_turning_into_auth_error_asks_for_login(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """When the API rejects the tokens for good, a poll starts the reauth flow."""
    cloud.main.rest_status = 401
    await setup_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]


async def test_unload_saves_analytics_and_removes_panel(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Unloading the last account writes the listening sums and takes the page off the sidebar."""
    from homeassistant.components.frontend import async_panel_exists

    push.last.connect()
    push.last.playback()
    freezer.tick(timedelta(seconds=120))
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.NOT_LOADED
    days = hass_storage[_analytics_key(setup_entry)]["data"]["days"]
    assert len(days) == 1
    assert next(iter(days.values())) == {BOX_ID: {"t1": 120}}
    assert not async_panel_exists(hass, PANEL_URL_PATH)


async def test_unload_keeps_panel_for_other_account(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """The page and the dashboard card stay while another account is still loaded."""
    from homeassistant.components.frontend import (
        DATA_EXTRA_MODULE_URL,
        UrlManager,
        async_panel_exists,
    )

    # What the frontend holds for extra modules; the frontend itself does not start in tests
    hass.config.components.add("frontend")
    hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda *_: None, [])
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    setup_entry = config_entry

    def cards() -> list[str]:
        return [u for u in hass.data[DATA_EXTRA_MODULE_URL].urls if "storybox-plus-card.js?v=" in u]

    assert len(cards()) == 1

    second = entry_for(cloud.add_account("second", households=[{"id": "hh2", "name": "Zwei"}]))
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    assert len(push.instances) == 2

    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    assert async_panel_exists(hass, PANEL_URL_PATH)
    assert len(cards()) == 1
    assert await hass.config_entries.async_unload(second.entry_id)
    assert not async_panel_exists(hass, PANEL_URL_PATH)
    assert cards() == []


async def test_remove_entry_deletes_analytics(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Removing the account forgets its listening sums."""
    key = _analytics_key(setup_entry)
    await setup_entry.runtime_data.analytics.async_save()
    assert key in hass_storage
    await hass.config_entries.async_remove(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage


async def test_analytics_option_off_removes_store(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    hass_storage: dict[str, Any],
) -> None:
    """With the option off nothing is counted and old sums are deleted."""
    entry = entry_for(cloud.main)
    counting_off(hass_storage, entry)
    key = _analytics_key(entry)
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {"days": {"2026-11-01": {BOX_ID: {"t1": 60}}}},
    }
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.analytics is None
    assert key not in hass_storage
    # Listening is not counted either
    push.last.connect()
    push.last.playback()
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert key not in hass_storage


async def test_stored_analytics_are_loaded(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Sums of earlier runs are read at setup."""
    key = _analytics_key(config_entry)
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {"days": {"2026-11-01": {BOX_ID: {"t1": 60}}}},
    }
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.runtime_data.analytics.total() == 60


async def _polls(hass: HomeAssistant, entry: MockConfigEntry, count: int) -> None:
    for _ in range(count):
        await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_box_leaving_the_account_removes_its_device(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A box missing from an hour of polls loses its device and entities; one poll is a hiccup."""
    cloud.main.boxes[HOUSEHOLD_ID].append(
        tb2_box("box3", name="Bad", mac="0A1B2C3D4E5F", placed=None)
    )
    await _polls(hass, setup_entry, 1)
    connectivity = entity_id(hass, "binary_sensor", f"{'box3'}_connectivity")
    removed = cloud.main.box("box3")
    cloud.main.remove_box("box3")
    # Missing for a while, then back: nothing is lost, the count starts over
    await _polls(hass, setup_entry, STALE_AFTER_POLLS - 1)
    assert device(hass, setup_entry, "box3") is not None
    assert hass.states.get(connectivity).state == STATE_UNAVAILABLE
    cloud.main.boxes[HOUSEHOLD_ID].append(removed)
    await _polls(hass, setup_entry, 1)
    assert hass.states.get(connectivity).state != STATE_UNAVAILABLE
    cloud.main.remove_box("box3")
    await _polls(hass, setup_entry, STALE_AFTER_POLLS - 1)
    assert device(hass, setup_entry, "box3") is not None
    await _polls(hass, setup_entry, 1)
    assert device(hass, setup_entry, "box3") is None
    assert device(hass, setup_entry, BOX_ID) is not None
    assert er.async_get(hass).async_get(connectivity) is None
    assert hass.states.get(connectivity) is None
    # Back in the account after all: the box gets its entities anew
    cloud.main.boxes[HOUSEHOLD_ID].append(removed)
    await _polls(hass, setup_entry, 1)
    connectivity = entity_id(hass, "binary_sensor", f"{'box3'}_connectivity")
    assert hass.states.get(connectivity) is not None


async def test_stale_device_is_removed_after_an_hour(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A device left over from an earlier run goes once its box stayed away for an hour."""
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={box_identifier(config_entry, "box-sold")},
        name="Alt",
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert device(hass, config_entry, "box-sold") is not None
    await _polls(hass, config_entry, STALE_AFTER_POLLS - 1)
    assert device(hass, config_entry, "box-sold") is None
    assert device(hass, config_entry, BOX_ID) is not None


async def test_device_of_a_gone_box_can_be_removed_by_hand(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The user may remove the device of a box the account lacks, not of one it has."""
    cloud.main.boxes[HOUSEHOLD_ID].append(
        tb2_box("box3", name="Bad", mac="0A1B2C3D4E5F", placed=None)
    )
    await _polls(hass, setup_entry, 1)
    assert await async_setup_component(hass, "config", {})
    cloud.main.remove_box("box3")
    await _polls(hass, setup_entry, 1)
    client = await hass_ws_client(hass)
    for box_id, success in ((BOX_ID, False), ("box3", True)):
        await client.send_json_auto_id(
            {
                "type": "config/device_registry/remove_config_entry",
                "config_entry_id": setup_entry.entry_id,
                "device_id": device(hass, setup_entry, box_id).id,
            }
        )
        assert (await client.receive_json())["success"] is success
    assert device(hass, setup_entry, "box3") is None


async def test_new_box_gets_entities(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A box that joins the account later gets its entities without a reload."""
    new_mac = "0A1B2C3D4E5F"
    cloud.main.boxes["hh1"].append(tb2_box("box3", name="Bad", mac=new_mac, placed=None))
    await setup_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "media_player", "box3")).state == "idle"
    assert hass.states.get(entity_id(hass, "binary_sensor", "box3_connectivity")).state == "on"
    assert hass.states.get(entity_id(hass, "event", "box3_figure")) is not None
    assert push.last.macs == {MAC, new_mac}
    # Nothing is created twice on the next poll
    before = len(er.async_entries_for_config_entry(er.async_get(hass), setup_entry.entry_id))
    await setup_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert (
        len(er.async_entries_for_config_entry(er.async_get(hass), setup_entry.entry_id)) == before
    )


async def test_push_channel_refused_login_asks_for_login(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """When the push channel's token is refused for good, the reauth flow starts."""
    push.last.end(CloudAuthError("Login refused (invalid_grant)"))
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]
    assert setup_entry.state is ConfigEntryState.LOADED


async def test_unload_fails_when_a_platform_does_not(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """When a platform cannot be unloaded the entry is not unloaded either."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms", return_value=False
    ):
        assert not await hass.config_entries.async_unload(setup_entry.entry_id)
    assert setup_entry.state is ConfigEntryState.FAILED_UNLOAD


async def test_two_accounts_of_one_household(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Two members sign in with their own accounts: each gets its own device of the shared box."""
    second = entry_for(
        cloud.add_account(
            "second",
            households=[{"id": HOUSEHOLD_ID, "name": "Familie Muster"}],
            boxes={HOUSEHOLD_ID: [tb2_box()]},
        )
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    first_device = device(hass, setup_entry, BOX_ID)
    second_device = device(hass, second, BOX_ID)
    assert first_device is not None
    assert second_device is not None
    assert first_device.id != second_device.id
    registry = er.async_get(hass)
    players = [
        e.entity_id
        for entry in (setup_entry, second)
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        if e.domain == "media_player"
    ]
    assert len(players) == 2
    assert all(hass.states.get(p) is not None for p in players)
    # Each entry removes only devices of its own; the other's box is not gone
    await setup_entry.runtime_data.coordinator.async_refresh()
    assert device(hass, second, BOX_ID) is not None


async def test_device_of_a_toniebox_1_goes(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A device of a Toniebox 1 stands for nothing: removable by hand, gone after an hour."""
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={box_identifier(config_entry, CLASSIC_BOX_ID)},
        name="Alt",
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert await async_setup_component(hass, "config", {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "config/device_registry/remove_config_entry",
            "config_entry_id": config_entry.entry_id,
            "device_id": device(hass, config_entry, CLASSIC_BOX_ID).id,
        }
    )
    assert (await client.receive_json())["success"] is True
    assert device(hass, config_entry, CLASSIC_BOX_ID) is None
    registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={box_identifier(config_entry, CLASSIC_BOX_ID)},
        name="Alt",
    )
    await _polls(hass, config_entry, STALE_AFTER_POLLS)
    assert device(hass, config_entry, CLASSIC_BOX_ID) is None
    assert device(hass, config_entry, BOX_ID) is not None
