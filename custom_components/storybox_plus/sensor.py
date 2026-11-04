"""The battery of a Toniebox 2."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, async_follow_boxes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of the boxes."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        if not box_state.box.live:
            return []
        return [BatterySensor(coordinator, box_state.box.id)]

    async_follow_boxes(entry, async_add_entities, _factory)


class BatterySensor(BoxEntity, SensorEntity):
    """The battery level of the Toniebox 2, as the push channel reports it."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "battery")

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
    def native_value(self) -> int | None:
        """Return the battery level in percent."""
        battery = self.box_state.battery if self.box_state else None
        return battery.percent if battery else None
