"""Whether a box is online, and whether a Toniebox 2 charges."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
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
    """Set up the binary sensors of the boxes."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        entities: list[Entity] = [ConnectivitySensor(coordinator, box_state.box.id)]
        if box_state.box.live:
            entities.append(ChargingSensor(coordinator, box_state.box.id))
        return entities

    async_follow_boxes(entry, async_add_entities, _factory)


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
