"""Base entity of a box, and how platforms follow boxes that come and go."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceEntryType,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .cloud import Generation
from .const import MANUFACTURER
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .ids import account_identifier, box_identifier, box_unique_id

MODEL_NAMES = {Generation.CLASSIC: "Toniebox 1", Generation.TONIEBOX_2: "Toniebox 2"}


class BoxEntity(CoordinatorEntity[StoryboxCoordinator]):
    """An entity of one box."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str, key: str | None) -> None:
        """Initialize for the box; key None is the box's main entity."""
        super().__init__(coordinator)
        self._box_id = box_id
        entry = coordinator.config_entry
        self._attr_unique_id = box_unique_id(entry, box_id, key)
        if key:
            self._attr_translation_key = key
        box = coordinator.data.boxes[box_id].box
        self._attr_device_info = DeviceInfo(
            identifiers={box_identifier(entry, box_id)},
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


class TimedBoxEntity(BoxEntity):
    """An entity of a box whose state also changes with the clock.

    The coordinator tells its listeners when the cloud or the box says
    something new; a time that passes (a timer that ran out, an alarm that
    rang, the start of the night) says nothing, so the entity writes its
    state again right after the moment it names.
    """

    _cancel_timed: CALLBACK_TYPE | None = None

    def _next_change(self) -> datetime | None:
        """Return the moment the state changes by the clock alone; None: never."""
        raise NotImplementedError

    @callback
    def _async_schedule(self) -> None:
        self._async_cancel_timed()
        at = self._next_change()
        if at is None:
            return
        # A second later, so the state is past the moment for sure
        due = dt_util.as_utc(at) + timedelta(seconds=1)
        if due <= dt_util.utcnow():
            return

        @callback
        def _write(_now: datetime) -> None:
            self._cancel_timed = None
            self.async_write_ha_state()
            self._async_schedule()

        self._cancel_timed = async_track_point_in_utc_time(self.hass, _write, due)

    @callback
    def _async_cancel_timed(self) -> None:
        if self._cancel_timed is not None:
            self._cancel_timed()
            self._cancel_timed = None

    async def async_added_to_hass(self) -> None:
        """Wait for the first change by the clock."""
        await super().async_added_to_hass()
        self.async_on_remove(self._async_cancel_timed)
        self._async_schedule()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Something new from the cloud or the box may move the next change."""
        self._async_schedule()
        super()._handle_coordinator_update()


def account_device_info(entry: StoryboxConfigEntry) -> DeviceInfo:
    """Return the device of the account: its notifications and its live channel."""
    return DeviceInfo(
        identifiers={account_identifier(entry)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model="Cloud account",
        entry_type=DeviceEntryType.SERVICE,
    )


@callback
def async_follow_boxes(
    entry: StoryboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[StoryboxCoordinator, BoxState], list[Entity]],
) -> None:
    """Create the entities of every box, also of boxes that join later."""
    coordinator = entry.runtime_data.coordinator
    devices = dr.async_get(coordinator.hass)
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        # A box whose device was removed lost its entities; should it come
        # back, it gets new ones
        for box_id in known - set(coordinator.data.boxes):
            if devices.async_get_device(identifiers={box_identifier(entry, box_id)}) is None:
                known.discard(box_id)
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
