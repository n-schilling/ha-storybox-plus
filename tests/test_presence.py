"""A Toniebox 1 with a presence entity: its online state and its active time."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.analytics import Analytics
from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.preferences import Preferences

from .conftest import BOX_ID, CLASSIC_BOX_ID, FakeCloud, PushChannels, counting_off
from .test_analytics import TODAY, Clock

TRACKER = "device_tracker.toniebox"


def _about(seconds: int) -> Any:
    """Sums are whole seconds per hour: a span across an hour's end may lose one."""
    return pytest.approx(seconds, abs=2)


async def _ask(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    answer: dict[str, Any] = await client.receive_json()
    return answer


async def _box(client: Any, box_id: str = CLASSIC_BOX_ID) -> dict[str, Any]:
    answer = await _ask(client, {"type": f"{DOMAIN}/overview"})
    box: dict[str, Any] = next(b for b in answer["result"]["boxes"] if b["id"] == box_id)
    return box


async def _set(
    client: Any, entity_id: str | None, box_id: str = CLASSIC_BOX_ID, lag: int = 0
) -> dict[str, Any]:
    """Set the entity; the lag is switched off unless the test is about it."""
    return await _ask(
        client,
        {
            "type": f"{DOMAIN}/box/settings",
            "box_id": box_id,
            "presence_entity": entity_id,
            "presence_lag": lag,
        },
    )


async def _active(client: Any) -> list[dict[str, Any]]:
    answer = await _ask(client, {"type": f"{DOMAIN}/analytics"})
    active: list[dict[str, Any]] = answer["result"]["active_per_box"]
    return active


def _store(data: Any = None) -> Mock:
    store = Mock()
    store.async_load = AsyncMock(return_value=data)
    store.async_save = AsyncMock()
    return store


def test_awake_time_is_counted_apart() -> None:
    """The time in the network is summed per box and enters no listening sum."""
    clock = Clock()
    counter = Analytics(_store(), clock.now)
    counter.awake("classic", True)
    clock.advance(600)
    counter.tick()
    clock.advance(300)
    counter.awake("classic", False)
    clock.advance(1000)
    counter.awake("classic", False)
    assert counter.active_per_box() == {"classic": 900}
    assert counter.active_per_box(1) == {"classic": 900}
    assert counter.total() == 0
    assert counter.per_box() == {}
    assert counter._data_to_save()["active"] == {TODAY: {"classic": {"10": 900}}}


async def test_awake_time_is_loaded_and_pruned() -> None:
    """Sums of earlier runs are read; days too old or of another shape are left out."""
    clock = Clock()
    store = _store(
        {
            "active": {
                "2020-01-01": {"classic": {"9": 50}},
                TODAY: {"classic": {"9": "120"}, "odd": 3},
                "2026-11-03": 7,
            }
        }
    )
    counter = Analytics(store, clock.now)
    await counter.async_load()
    assert counter.active_per_box() == {"classic": 120}
    assert counter.active_per_box(1) == {"classic": 120}
    clock.advance(86400 * 2)
    assert counter.active_per_box(1) == {}


async def test_preferences_keep_the_entity() -> None:
    """Only entities of the two kinds are kept, from the page and from the store."""
    store = _store({"presence": {"a": TRACKER, "b": "light.kitchen", "c": 5}})
    preferences = Preferences(store)
    await preferences.async_load()
    assert preferences.presence == {"a": TRACKER}
    await preferences.async_set_presence("b", "binary_sensor.ping")
    await preferences.async_set_presence("a", None)
    await preferences.async_set_presence("gone", None)
    assert preferences.presence == {"b": "binary_sensor.ping"}
    with pytest.raises(ValueError):
        await preferences.async_set_presence("b", "light.kitchen")
    assert store.async_save.call_args.args[0]["presence"] == {"b": "binary_sensor.ping"}


async def test_state_and_active_time_follow_the_entity(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """The box is online while the tracker is at home, and that time is its active time."""
    client = await hass_ws_client(hass)
    assert (await _box(client))["presence_entity"] is None
    assert await _active(client) == []

    hass.states.async_set(TRACKER, "not_home")
    answer = await _set(client, TRACKER)
    assert answer["success"], answer
    assert answer["result"]["presence_entity"] == TRACKER
    assert answer["result"]["online"] is False
    assert hass_storage[f"{DOMAIN}.{setup_entry.entry_id}.settings"]["data"]["presence"] == {
        CLASSIC_BOX_ID: TRACKER
    }

    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert (await _box(client))["online"] is True
    freezer.tick(timedelta(seconds=200))
    # An attribute alone changes nothing
    hass.states.async_set(TRACKER, "home", {"ip": "10.0.0.2"})
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=100))
    hass.states.async_set(TRACKER, "unavailable")
    await hass.async_block_till_done()
    assert (await _box(client))["online"] is None
    freezer.tick(timedelta(seconds=500))
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert (await _box(client))["online"] is False

    active = await _active(client)
    assert [b["box_id"] for b in active] == [CLASSIC_BOX_ID]
    assert active[0]["seconds"] == _about(300)
    answer = await _ask(client, {"type": f"{DOMAIN}/analytics"})
    assert answer["result"]["total_seconds"] == 0
    assert answer["result"]["per_box"] == []


async def test_a_poll_keeps_the_state_of_the_entity(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The cloud's guess from "last seen" does not overrule the entity; a poll books the time."""
    client = await hass_ws_client(hass)
    hass.states.async_set("binary_sensor.ping", "on")
    assert (await _set(client, "binary_sensor.ping"))["result"]["online"] is True
    freezer.tick(timedelta(seconds=120))
    hass.states.async_set("binary_sensor.ping", "off")
    await hass.async_block_till_done()
    await setup_entry.runtime_data.coordinator.async_refresh()
    assert (await _box(client))["online"] is False
    assert (await _active(client))[0]["seconds"] == _about(120)

    # Without the entity the state is the cloud's again, and nothing counts on
    hass.states.async_set("binary_sensor.ping", "on")
    await hass.async_block_till_done()
    answer = await _set(client, None)
    assert answer["result"]["presence_entity"] is None
    assert answer["result"]["online"] is True
    freezer.tick(timedelta(seconds=300))
    await setup_entry.runtime_data.coordinator.async_refresh()
    hass.states.async_set("binary_sensor.ping", "off")
    await hass.async_block_till_done()
    assert (await _box(client))["online"] is True
    assert (await _active(client))[0]["seconds"] == _about(120)


async def test_the_entity_is_watched_from_the_start(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """A saved entity counts from the setup on, also one that shows up only later."""
    key = f"{DOMAIN}.{config_entry.entry_id}.settings"
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {
            "presence": {CLASSIC_BOX_ID: TRACKER, BOX_ID: TRACKER},
            "presence_lag": {CLASSIC_BOX_ID: 0, "odd": 500, "flag": True},
        },
    }
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    assert (await _box(client))["online"] is None
    # A Toniebox 2 tells its state itself: an entity saved for it is not used
    assert (await _box(client, BOX_ID))["presence_entity"] is None

    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=60))
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass_storage[f"{DOMAIN}.{config_entry.entry_id}.analytics"]["data"]["active"]


async def test_state_without_counting(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """With counting switched off the box still shows its state."""
    counting_off(hass_storage, config_entry)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    hass.states.async_set(TRACKER, "home")
    assert (await _set(client, TRACKER))["result"]["online"] is True
    assert await _active(client) == []


@pytest.mark.parametrize(
    ("box_id", "entity_id", "code"),
    [
        (BOX_ID, TRACKER, "not_supported"),
        (CLASSIC_BOX_ID, "light.kitchen", "invalid_format"),
        (CLASSIC_BOX_ID, "device_tracker.Bad Name", "invalid_format"),
        ("nothing", TRACKER, "unknown_box"),
    ],
)
async def test_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    box_id: str,
    entity_id: str,
    code: str,
) -> None:
    """Only a Toniebox 1 takes an entity, and only one of the two kinds."""
    client = await hass_ws_client(hass)
    answer = await _set(client, entity_id, box_id)
    assert not answer["success"]
    assert answer["error"]["code"] == code


def test_the_lag_is_taken_off_every_stretch() -> None:
    """Time is booked once it is older than the lag; a short stretch counts nothing."""
    clock = Clock()
    counter = Analytics(_store(), clock.now)
    counter.awake("classic", True, 1200)
    clock.advance(600)
    counter.tick()
    assert counter.active_per_box() == {}
    clock.advance(900)
    counter.tick()
    assert counter.active_per_box() == {"classic": 300}
    # In the network already: the stretch goes on, only the lag follows
    counter.awake("classic", True, 600)
    clock.advance(900)
    counter.awake("classic", False)
    assert counter.active_per_box() == {"classic": 1800}
    # Twenty minutes switched on without a use
    counter.awake("classic", True, 1200)
    clock.advance(1200)
    counter.awake("classic", False)
    counter.awake("classic", True, 1200)
    clock.advance(300)
    counter.awake("classic", False)
    assert counter.active_per_box() == {"classic": 1800}


async def test_the_lag_of_a_box(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Twenty minutes go off each stretch by default; the page sets another lag."""
    client = await hass_ws_client(hass)
    assert (await _box(client))["presence_lag"] == 20
    assert (await _box(client, BOX_ID))["presence_lag"] is None
    hass.states.async_set(TRACKER, "home")
    answer = await _ask(
        client,
        {"type": f"{DOMAIN}/box/settings", "box_id": CLASSIC_BOX_ID, "presence_entity": TRACKER},
    )
    assert answer["result"]["presence_lag"] == 20
    freezer.tick(timedelta(minutes=50))
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert (await _active(client))[0]["seconds"] == _about(30 * 60)

    # A new lag counts for the stretch that runs
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    lag = {"type": f"{DOMAIN}/box/settings", "box_id": CLASSIC_BOX_ID, "presence_lag": 5}
    answer = await _ask(client, lag)
    assert answer["result"]["presence_lag"] == 5
    assert answer["result"]["presence_entity"] == TRACKER
    freezer.tick(timedelta(minutes=15))
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert (await _active(client))[0]["seconds"] == _about(40 * 60)
    stored = hass_storage[f"{DOMAIN}.{setup_entry.entry_id}.settings"]["data"]
    assert stored["presence_lag"] == {CLASSIC_BOX_ID: 5}

    for wrong, code in (
        ({**lag, "presence_lag": 121}, "invalid_format"),
        ({**lag, "box_id": BOX_ID}, "not_supported"),
        ({**lag, "box_id": "nothing"}, "unknown_box"),
    ):
        assert (await _ask(client, wrong))["error"]["code"] == code
    with pytest.raises(ValueError):
        await setup_entry.runtime_data.preferences.async_set_presence_lag(CLASSIC_BOX_ID, -1)
