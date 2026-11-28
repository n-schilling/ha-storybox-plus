"""The battery of a Toniebox 2, the end of its sleep timer, its next alarm; the account's boxes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import bedtime
from .const import DOMAIN
from .coordinator import BoxState, StoryboxConfigEntry, StoryboxCoordinator
from .entity import BoxEntity, TimedBoxEntity, account_device_info, async_follow_boxes
from .ids import box_identifier, box_unique_id

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
        box = box_state.box
        entities: list[Entity] = [
            BatterySensor(coordinator, box.id),
            SleepTimerSensor(coordinator, box.id),
        ]
        # Only a box that rings alarms has a next one
        if box.alarm_capable:
            entities.append(NextAlarmSensor(coordinator, box.id))
        return entities

    async_follow_boxes(entry, async_add_entities, _factory)
    async_add_entities([BoxesSensor(entry)])


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


class SleepTimerSensor(TimedBoxEntity, SensorEntity):
    """When the running sleep timer of the Toniebox 2 ends; unknown while none runs.

    A timer that ends with an alarm is the bedtime's: it is the next alarm,
    not a sleep timer somebody set.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "sleep_timer")

    @property
    def native_value(self) -> datetime | None:
        """Return the end of the timer while it runs."""
        timer = self.box_state.sleep_timer if self.box_state else None
        if timer is None or not timer.running or timer.alarm or timer.until is None:
            return None
        return timer.until if timer.until > dt_util.utcnow() else None

    def _next_change(self) -> datetime | None:
        """A timer that ran out is none."""
        return self.native_value


class NextAlarmSensor(TimedBoxEntity, SensorEntity):
    """When the next alarm of the box rings (a bedtime's or the wake-up light); unknown without one."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: StoryboxCoordinator, box_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator, box_id, "next_alarm")

    @property
    def native_value(self) -> datetime | None:
        """Return the next wake-up over the enabled bedtimes with an alarm and the wake-up light."""
        box_state = self.box_state
        if box_state is None:
            return None
        upcoming = self.coordinator.next_alarm(box_state)
        return upcoming.at if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return whether the alarm is due and whether it is the wake-up light.

        Due: close enough for the box's timer to carry it. While it is, the
        timer is the alarm's and a sleep timer is refused.
        """
        box_state = self.box_state
        upcoming = self.coordinator.next_alarm(box_state) if box_state else None
        return {
            "due": self.coordinator.due_alarm(self._box_id) is not None,
            "wake_up_light": upcoming is not None and upcoming.schedule is None,
        }

    def _next_change(self) -> datetime | None:
        """It becomes due first; once it rang, the one after it is next."""
        box_state = self.box_state
        at = self.native_value
        if box_state is None or at is None:
            return None
        arming = at - bedtime.ARM_WINDOW
        return arming if arming > self.coordinator.now_at(box_state.box) else at


class BoxesSensor(CoordinatorEntity[StoryboxCoordinator], SensorEntity):
    """How many Tonieboxes 2 the account has, and which: the list a dashboard shows.

    The attribute names every box with a media player by its name in Home
    Assistant, the media player's entity ID and the box's picture, so a card
    lists the boxes without searching the registry. It follows the registry:
    a media player that is registered or renamed, a device given another name.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "boxes"
    # Names and entity IDs are no history
    _unrecorded_attributes = frozenset({"boxes"})

    def __init__(self, entry: StoryboxConfigEntry) -> None:
        """Initialize for the account."""
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_boxes"
        self._attr_device_info = account_device_info(entry)

    async def async_added_to_hass(self) -> None:
        """Follow the registries: the media players come after this sensor."""
        await super().async_added_to_hass()

        @callback
        def _changed(_event: Event[Any]) -> None:
            self.async_write_ha_state()

        @callback
        def _player(data: Any) -> bool:
            return any(
                str(data.get(key, "")).startswith("media_player.")
                for key in ("entity_id", "old_entity_id")
            )

        self.async_on_remove(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, _changed, event_filter=_player
            )
        )
        self.async_on_remove(self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _changed))

    def _boxes(self) -> list[dict[str, Any]]:
        entry = self.coordinator.config_entry
        entities = er.async_get(self.hass)
        devices = dr.async_get(self.hass)
        found: list[dict[str, Any]] = []
        for box_id, box_state in self.coordinator.data.boxes.items():
            player = entities.async_get_entity_id(
                "media_player", DOMAIN, box_unique_id(entry, box_id)
            )
            if player is None:
                continue
            device = devices.async_get_device_by_identifier(
                box_identifier(entry, box_id), entry.entry_id
            )
            name = (device.name_by_user or device.name) if device else None
            found.append(
                {
                    "name": name or box_state.box.name,
                    "entity_id": player,
                    "picture": self.coordinator.box_picture(box_state.box),
                }
            )
        return sorted(found, key=lambda box: str(box["name"]).lower())

    @property
    def native_value(self) -> int:
        """Return how many boxes have a media player."""
        return len(self._boxes())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the boxes a dashboard lists."""
        return {"boxes": self._boxes()}
