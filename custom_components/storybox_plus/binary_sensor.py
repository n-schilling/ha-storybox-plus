"""A Toniebox 2: online, charging, headphones, night mode; and whether the live channel is up."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import bedtime, night
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, TimedBoxEntity, account_device_info, async_follow_boxes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors of the boxes."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        # A Toniebox 1 reports no connection state to the cloud: it gets no sensor
        if not box_state.box.live:
            return []
        entities: list[Entity] = [
            ConnectivitySensor(coordinator, box_state.box.id),
            ChargingSensor(coordinator, box_state.box.id),
            HeadphonesSensor(coordinator, box_state.box.id),
            NightModeSensor(coordinator, box_state.box.id),
        ]
        if box_state.box.alarm_capable:
            entities.append(AlarmRingingSensor(coordinator, box_state.box.id))
        return entities

    async_follow_boxes(entry, async_add_entities, _factory)
    # Only a Toniebox 2 uses the live channel; without one it stays closed for good
    if any(b.box.live for b in entry.runtime_data.coordinator.data.boxes.values()):
        async_add_entities([LiveChannelSensor(entry)])


class ConnectivitySensor(BoxEntity, BinarySensorEntity):
    """Whether a Toniebox 2 is connected to the cloud, as it reports; unknown stays unknown."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "connectivity")

    @property
    def is_on(self) -> bool | None:
        """Return whether the box is online."""
        return self.box_state.online if self.box_state else None


class ChargingSensor(BoxEntity, BinarySensorEntity):
    """Whether the Toniebox 2 is charging."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "charging")

    @property
    def available(self) -> bool:
        """Return whether the box has reported its battery and is not switched off."""
        box_state = self.box_state
        return (
            super().available
            and box_state is not None
            and box_state.battery is not None
            and box_state.online is not False
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the box charges."""
        battery = self.box_state.battery if self.box_state else None
        return battery.charging if battery else None


class HeadphonesSensor(BoxEntity, BinarySensorEntity):
    """Whether headphones are connected to the Toniebox 2, with their kind and battery."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "headphones")

    @property
    def available(self) -> bool:
        """Return whether the box is not switched off: then nothing is known of headphones."""
        box_state = self.box_state
        return super().available and box_state is not None and box_state.online is not False

    @property
    def is_on(self) -> bool | None:
        """Return whether headphones are connected; unknown until the box says."""
        headphones = self.box_state.headphones if self.box_state else None
        return headphones.connected if headphones else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the kind the box names and the battery of wireless headphones."""
        headphones = self.box_state.headphones if self.box_state else None
        connected = headphones is not None and headphones.connected
        return {
            "kind": headphones.kind if headphones and connected else None,
            "battery": headphones.battery if headphones and connected else None,
        }


class NightModeSensor(TimedBoxEntity, BinarySensorEntity):
    """Whether the night mode of the light ring is at work: switched on and within its span."""

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "night_mode")

    @property
    def is_on(self) -> bool | None:
        """Return whether it is night for the box's light ring."""
        box_state = self.box_state
        if box_state is None:
            return None
        return self.coordinator.night_phase(box_state) == "night"

    def _next_change(self) -> datetime | None:
        """The start or the end of the span, whichever comes first."""
        box_state = self.box_state
        mode = self.coordinator.night_modes.get(self._box_id) if box_state else None
        if box_state is None or mode is None or not mode.enabled:
            return None
        return night.next_change(mode, self.coordinator.now_at(box_state.box))


class AlarmRingingSensor(BoxEntity, BinarySensorEntity):
    """Whether the box's alarm rings right now, with its tone; off once it stopped.

    The box says so itself the moment it starts and stops, also when a child
    stops it on the box. A tone the app plays as a preview counts too.
    """

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "alarm_ringing")

    @property
    def is_on(self) -> bool | None:
        """Return whether an alarm rings."""
        box_state = self.box_state
        if box_state is None or box_state.online is None:
            return None
        return box_state.ringing is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the tone it rings, by the name the actions use."""
        tone = self.box_state.ringing if self.box_state else None
        return {"tone": bedtime.TONE_NAME.get(tone, tone) if tone else None}


class LiveChannelSensor(CoordinatorEntity[StoryboxCoordinator], BinarySensorEntity):
    """Whether the push channel of the account is connected.

    Live state of every Toniebox 2 and all commands to it go through it; an
    automation can tell the admin when it stays down.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_translation_key = "live_channel"

    def __init__(self, entry: StoryboxConfigEntry) -> None:
        """Initialize for the account."""
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_live_channel"
        self._attr_device_info = account_device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return whether the channel is connected."""
        return self.coordinator.data.push_connected
