"""Base entity of a box, and how platforms follow boxes that come and go."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .cloud import Generation
from .const import DOMAIN, MANUFACTURER
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator

MODEL_NAMES = {Generation.CLASSIC: "Toniebox", Generation.TONIEBOX_2: "Toniebox 2"}


class BoxEntity(CoordinatorEntity[StoryboxCoordinator]):
    """An entity of one box."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str, key: str | None) -> None:
        """Initialize for the box; key None is the box's main entity."""
        super().__init__(coordinator)
        self._box_id = box_id
        self._attr_unique_id = f"{box_id}_{key}" if key else box_id
        if key:
            self._attr_translation_key = key
        box = coordinator.data.boxes[box_id].box
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, box_id)},
            connections={(CONNECTION_NETWORK_MAC, format_mac(box.mac))} if box.mac else set(),
            name=box.name,
            manufacturer=MANUFACTURER,
            model=MODEL_NAMES[box.generation],
            sw_version=box.firmware,
        )

    @property
    def box_state(self) -> BoxState | None:
        """Return the box, if the account still has it."""
        return self.coordinator.data.boxes.get(self._box_id)

    @property
    def available(self) -> bool:
        """Return whether the cloud answers and the box is still in the account."""
        return super().available and self.box_state is not None


@callback
def async_follow_boxes(
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[StoryboxCoordinator, BoxState], list[Entity]],
) -> None:
    """Create the entities of every box, also of boxes that join later."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new: list[Entity] = []
        for box_id, box_state in coordinator.data.boxes.items():
            if box_id in known:
                continue
            known.add(box_id)
            new.extend(factory(coordinator, box_state))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
