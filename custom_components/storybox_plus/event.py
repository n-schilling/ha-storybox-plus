"""The figure on a Toniebox 2 changes: placed or taken off."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ATTR_TONIE, ATTR_TONIE_ID, EVENT_FIGURE_PLACED, EVENT_FIGURE_REMOVED
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, async_follow_boxes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the figure events of the boxes that have the push channel."""

    def _factory(coordinator: StoryboxCoordinator, box_state: BoxState) -> list[Entity]:
        if not box_state.box.live:
            return []
        return [FigureEvent(coordinator, box_state.box.id)]

    async_follow_boxes(entry, async_add_entities, _factory)


class FigureEvent(BoxEntity, EventEntity):
    """Fires when a figure is placed on the box or taken off, and names it."""

    _attr_event_types = [EVENT_FIGURE_PLACED, EVENT_FIGURE_REMOVED]

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "figure")

    async def async_added_to_hass(self) -> None:
        """Listen for the figure changing."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_placement_listener(self._box_id, self._changed)
        )

    @callback
    def _changed(self, before: str | None, after: str | None) -> None:
        if after is not None:
            tonie = self.coordinator.tonie(after)
            self._trigger_event(
                EVENT_FIGURE_PLACED,
                {ATTR_TONIE_ID: after, ATTR_TONIE: tonie.name if tonie else None},
            )
        elif before is not None:
            tonie = self.coordinator.tonie(before)
            self._trigger_event(
                EVENT_FIGURE_REMOVED,
                {ATTR_TONIE_ID: before, ATTR_TONIE: tonie.name if tonie else None},
            )
        else:
            return
        self.async_write_ha_state()
