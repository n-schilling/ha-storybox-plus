"""Whether a box is online, whether a Toniebox 2 charges, and whether the live channel is up."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, account_device_info, async_follow_boxes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors of the boxes."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        entities: list[Entity] = [ConnectivitySensor(coordinator, box_state.box.id)]
        if box_state.box.live:
            entities.append(ChargingSensor(coordinator, box_state.box.id))
        return entities

    async_follow_boxes(entry, async_add_entities, _factory)
    # Only a Toniebox 2 uses the live channel; without one it stays closed for good
    if any(b.box.live for b in entry.runtime_data.coordinator.data.boxes.values()):
        async_add_entities([LiveChannelSensor(entry)])


class ConnectivitySensor(BoxEntity, BinarySensorEntity):
    """Whether the box is connected to the cloud.

    A Toniebox 2 reports it; the classic box counts as connected while the
    cloud saw it in the last 30 minutes. Unknown stays unknown.
    """

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
