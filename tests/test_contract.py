"""The interface others build on, pinned: a change here is a breaking change.

Automations, dashboards and scripts use the entity IDs, unique IDs, translation
keys, event types, event data, attributes, actions and WebSocket commands; the
stores keep what the integration learned across updates. docs/automations.md,
section Interface, describes the same; change both together and note the change in
CHANGELOG.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from homeassistant.components.websocket_api import DOMAIN as WS_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus.cloud import TOPIC_HEADPHONES
from custom_components.storybox_plus.cloud.models import parse_headphones
from custom_components.storybox_plus.const import DOMAIN, STORAGE_VERSION

from .conftest import BOX_ID, TONIE_ID, TONIE_NAME, FakeCloud, PushChannels

PLAYER = "media_player.kinderzimmer"
FIGURE = "event.kinderzimmer_figure"
NOTIFICATION = "event.familie_muster_cloud_notification"
# What Home Assistant adds to every event entity; the rest is the event data
EVENT_BASE = {"event_type", "event_types", "friendly_name"}


def _event(hass: HomeAssistant, entity_id: str) -> tuple[str, dict[str, Any]]:
    """The last event of an event entity: its type and its data."""
    current = hass.states.get(entity_id)
    assert current is not None
    data = {key: value for key, value in current.attributes.items() if key not in EVENT_BASE}
    return str(current.attributes["event_type"]), data


async def test_entities(hass: HomeAssistant, setup_entry: MockConfigEntry) -> None:
    """Entity IDs, unique IDs and translation keys of a Toniebox 2 and of the account."""
    registry = er.async_get(hass)
    entry = setup_entry.entry_id
    entities = {
        item.entity_id: (
            item.unique_id.removeprefix(f"{entry}_"),
            item.translation_key,
            item.disabled_by is None,
        )
        for item in er.async_entries_for_config_entry(registry, entry)
    }
    assert all(
        item.unique_id.startswith(f"{entry}_")
        for item in er.async_entries_for_config_entry(registry, entry)
    )
    assert entities == {
        "media_player.kinderzimmer": (BOX_ID, None, True),
        "binary_sensor.kinderzimmer_connectivity": (f"{BOX_ID}_connectivity", "connectivity", True),
        "binary_sensor.kinderzimmer_charging": (f"{BOX_ID}_charging", "charging", True),
        "binary_sensor.kinderzimmer_headphones": (f"{BOX_ID}_headphones", "headphones", True),
        "binary_sensor.kinderzimmer_night_mode": (f"{BOX_ID}_night_mode", "night_mode", True),
        "sensor.kinderzimmer_battery": (f"{BOX_ID}_battery", "battery", True),
        "sensor.kinderzimmer_sleep_timer": (f"{BOX_ID}_sleep_timer", "sleep_timer", True),
        "sensor.kinderzimmer_next_alarm": (f"{BOX_ID}_next_alarm", "next_alarm", True),
        "event.kinderzimmer_figure": (f"{BOX_ID}_figure", "figure", True),
        "binary_sensor.familie_muster_live_channel": ("live_channel", "live_channel", True),
        "sensor.familie_muster_tonieboxes_2": ("boxes", "boxes", True),
        "event.familie_muster_cloud_notification": ("notification", "notification", True),
    }


async def test_attributes(
    hass: HomeAssistant, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The attributes a dashboard or an automation reads beside the states."""
    push.last.connect()
    push.last.online(True)
    push.last.playback(TONIE_ID, chapter=0)
    push.last.send(
        TOPIC_HEADPHONES, parse_headphones({"connected": [{"type": "bluetooth", "battery": 55}]})
    )
    await hass.async_block_till_done()

    player = hass.states.get(PLAYER)
    assert player is not None
    assert player.state == "playing"
    assert {
        "chapters",
        "chapter_list",
        "box_picture",
        "favourite",
        "tonie_id",
        "media_album_name",
        "media_title",
        "media_track",
    } <= set(player.attributes)
    assert player.attributes["media_album_name"] == TONIE_NAME

    headphones = hass.states.get("binary_sensor.kinderzimmer_headphones")
    assert headphones is not None
    assert (headphones.attributes["kind"], headphones.attributes["battery"]) == ("bluetooth", 55)

    alarm = hass.states.get("sensor.kinderzimmer_next_alarm")
    assert alarm is not None
    assert alarm.attributes["device_class"] == "timestamp"
    assert alarm.attributes["due"] in (True, False)
    timer = hass.states.get("sensor.kinderzimmer_sleep_timer")
    assert timer is not None
    assert timer.attributes["device_class"] == "timestamp"

    boxes = hass.states.get("sensor.familie_muster_tonieboxes_2")
    assert boxes is not None
    assert boxes.state == "1"
    (box,) = boxes.attributes["boxes"]
    assert set(box) == {"name", "entity_id", "picture"}
    assert (box["name"], box["entity_id"]) == ("Kinderzimmer", PLAYER)


async def test_events(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """The event types and the data of each event."""
    figure = hass.states.get(FIGURE)
    assert figure is not None
    assert figure.attributes["event_types"] == ["placed", "removed"]
    notification = hass.states.get(NOTIFICATION)
    assert notification is not None
    assert notification.attributes["event_types"] == ["notification"]

    push.last.playback(tonie_id=TONIE_ID)
    push.last.removed()
    assert _event(hass, FIGURE) == ("removed", {"tonie_id": TONIE_ID, "tonie": TONIE_NAME})
    push.last.playback(tonie_id=TONIE_ID)
    assert _event(hass, FIGURE) == ("placed", {"tonie_id": TONIE_ID, "tonie": TONIE_NAME})

    cloud.main.notices = [{"id": "n1", "text": "Hello", "read": False, "ntype": "news"}]
    await setup_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    kind, data = _event(hass, NOTIFICATION)
    assert kind == "notification"
    assert set(data) == {"kind", "text", "time", "tonie_id", "tonie", "reason"}
    assert (data["kind"], data["text"]) == ("news", "Hello")


async def test_actions_and_websocket_commands(
    hass: HomeAssistant, setup_entry: MockConfigEntry
) -> None:
    """The actions, and the commands of the page by name. The dashboard card uses none."""
    assert set(hass.services.async_services()[DOMAIN]) == {
        "set_sleep_timer",
        "clear_sleep_timer",
        "set_favourite",
        "play_favourite",
        "add_chapter",
        "remove_chapters",
        "shuffle_chapters",
        "set_box_settings",
    }
    commands = {name for name in hass.data[WS_DOMAIN] if name.startswith(f"{DOMAIN}/")}
    assert commands == {
        f"{DOMAIN}/overview",
        f"{DOMAIN}/library",
        f"{DOMAIN}/analytics",
        f"{DOMAIN}/chapters/arrange",
        f"{DOMAIN}/chapters/add",
        f"{DOMAIN}/chapters/add_text",
        f"{DOMAIN}/chapters/add_link",
        f"{DOMAIN}/favourites/set",
        f"{DOMAIN}/favourites/star",
        f"{DOMAIN}/box/favourites",
        f"{DOMAIN}/cloud/check",
        f"{DOMAIN}/figure/refresh",
        f"{DOMAIN}/figure/update",
        f"{DOMAIN}/figure/shuffle_on_swap",
        f"{DOMAIN}/figure/tune",
        f"{DOMAIN}/figure/redeem_token",
        f"{DOMAIN}/figure/lock",
        f"{DOMAIN}/figure/volume",
        f"{DOMAIN}/household/rename",
        f"{DOMAIN}/box/command",
        f"{DOMAIN}/box/repeat",
        f"{DOMAIN}/box/settings",
        f"{DOMAIN}/voucher/redeem",
        f"{DOMAIN}/preferences/set",
        f"{DOMAIN}/log",
        f"{DOMAIN}/log/set",
        f"{DOMAIN}/bedtime/save",
        f"{DOMAIN}/bedtime/delete",
        f"{DOMAIN}/night/set",
    }


async def test_stores(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """The stores an account writes when it is unloaded: their names, version and fields.

    The stores written only once there is something to keep (the learned
    chapters, the night modes) have their own tests.
    """
    push.last.connect()
    push.last.online(True)
    push.last.battery(80, "discharging")
    push.last.volume(7)
    push.last.playback(TONIE_ID, chapter=0)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done()

    assert STORAGE_VERSION == 1
    prefix = f"{DOMAIN}.{setup_entry.entry_id}."
    stores = {
        key.removeprefix(prefix): (stored["version"], set(stored["data"]))
        for key, stored in hass_storage.items()
        if key.startswith(prefix)
    }
    assert stores == {
        "analytics": (1, {"active", "chapters", "days", "hours", "placements"}),
        "battery": (1, {"cycles", "open"}),
        "favourites": (1, {"firsts", "gone", "runs", "tonies"}),
        "notices": (1, {"seen"}),
        "settings": (
            1,
            {
                "analytics",
                "analytics_days",
                "auto_lock",
                "cloud_check",
                "favourites_mode",
                "fetch_max_mb",
                "known",
                "mark_read",
                "presence",
                "presence_lag",
                "repeat",
                "speech_engine",
                "voice",
                "voice_language",
            },
        ),
        "shuffle": (1, {"last", "tonies"}),
        "volumes": (1, {"boxes", "tonies"}),
    }
