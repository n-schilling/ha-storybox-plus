"""Events: the figure on a Toniebox 2 changes, and the cloud has a notification."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .cloud import CloudNotice
from .const import (
    ATTR_KIND,
    ATTR_REASON,
    ATTR_TEXT,
    ATTR_TIME,
    ATTR_TONIE,
    ATTR_TONIE_ID,
    DOMAIN,
    EVENT_FIGURE_PLACED,
    EVENT_FIGURE_REMOVED,
    EVENT_NOTICE,
    MANUFACTURER,
)
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
    async_add_entities([NoticeEvent(entry)])


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


class NoticeEvent(EventEntity):
    """Fires once for every unread notification the cloud keeps for the account.

    It belongs to a device of the account, not to a box: notifications are
    about the account (figures, invitations, news).
    """

    _attr_event_types = [EVENT_NOTICE]
    _attr_has_entity_name = True
    _attr_translation_key = "notification"

    def __init__(self, entry: StoryboxConfigEntry) -> None:
        """Initialize for the account."""
        self._coordinator = entry.runtime_data.coordinator
        self._attr_unique_id = f"{entry.entry_id}_notification"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="Cloud account",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Take the notifications, those that came before the entity first."""
        await super().async_added_to_hass()
        self.async_on_remove(self._coordinator.async_set_notice_listener(self._notice))

    @callback
    def _notice(self, notice: CloudNotice) -> None:
        tonie = self._coordinator.tonie(notice.tonie_id)
        self._trigger_event(
            EVENT_NOTICE,
            {
                ATTR_KIND: notice.kind,
                ATTR_TEXT: notice.text,
                ATTR_TIME: notice.timestamp.isoformat() if notice.timestamp else None,
                ATTR_TONIE_ID: notice.tonie_id,
                ATTR_TONIE: tonie.name if tonie else None,
                ATTR_REASON: notice.reason,
            },
        )
        self.async_write_ha_state()
