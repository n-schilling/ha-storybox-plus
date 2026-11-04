"""How long a charge of the Toniebox 2 lasts.

A cycle runs from the moment the box is off the charger until it charges
again. Only the hours the box is switched on count, so a box that sleeps
for a week on a shelf does not look like a week of battery life. A cycle
keeps the day it ended, its hours and its percentages, no times of day.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.helpers.storage import Store

# Completed cycles kept per box
KEEP_CYCLES = 60
# A charge is also recognised by the level jumping up this much between two reports
JUMP_PERCENT = 5
# Cycles shorter than this, or using less than MIN_USED_PERCENT, tell nothing and are dropped
MIN_SECONDS = 600
MIN_USED_PERCENT = 5
# The estimate per full charge averages the latest cycles
AVERAGE_OVER = 10
SAVE_DELAY = 60


@dataclass(slots=True)
class OpenCycle:
    """A discharge that is still running."""

    from_percent: int
    last_percent: int
    on_seconds: int = 0
    # When the box was last seen switched on, if it is on right now
    on_since: datetime | None = None

    def hours(self, now: datetime) -> float:
        """Return the hours switched on so far."""
        seconds = self.on_seconds
        if self.on_since is not None:
            seconds += int((now - self.on_since).total_seconds())
        return round(seconds / 3600, 2)

    def per_full(self, now: datetime) -> float | None:
        """Return the hours a full charge would last at this rate."""
        used = self.from_percent - self.last_percent
        if used < MIN_USED_PERCENT:
            return None
        return round(self.hours(now) * 100 / used, 1)


class BatteryStats:
    """Counts the discharge cycles of the boxes."""

    def __init__(self, store: Store[dict[str, Any]], now: Callable[[], datetime]) -> None:
        """Count with the given clock."""
        self._store = store
        self._now = now
        self._open: dict[str, OpenCycle] = {}
        self._cycles: dict[str, list[dict[str, Any]]] = {}
        self._dirty = False

    async def async_load(self) -> None:
        """Read the cycles of earlier runs; an open cycle continues."""
        data = await self._store.async_load()
        if not data:
            return
        cycles = data.get("cycles")
        if isinstance(cycles, dict):
            for box_id, items in cycles.items():
                if isinstance(items, list):
                    self._cycles[box_id] = [c for c in items if isinstance(c, dict)][-KEEP_CYCLES:]
        open_cycles = data.get("open")
        if isinstance(open_cycles, dict):
            for box_id, raw in open_cycles.items():
                if (
                    isinstance(raw, dict)
                    and isinstance(raw.get("from"), int)
                    and isinstance(raw.get("to"), int)
                ):
                    seconds = raw.get("seconds")
                    self._open[box_id] = OpenCycle(
                        from_percent=raw["from"],
                        last_percent=raw["to"],
                        on_seconds=int(seconds) if isinstance(seconds, int | float) else 0,
                    )

    # ------------------------------------------------------------ counting

    def observe(self, box_id: str, percent: int | None, charging: bool | None, on: bool) -> None:
        """Note the battery and whether the box is switched on."""
        now = self._now()
        cycle = self._open.get(box_id)
        if percent is None:
            # A box that shuts down reports only nulls: the clock stops, the cycle stays
            if cycle is not None:
                self._pause(cycle, now)
            return
        charged = charging is True or (
            cycle is not None and percent >= cycle.last_percent + JUMP_PERCENT
        )
        if charged:
            if cycle is not None:
                # The level the charger found is where the discharge ended
                if percent < cycle.last_percent:
                    cycle.last_percent = percent
                self._close(box_id, cycle, now)
            return
        if cycle is None:
            cycle = self._open[box_id] = OpenCycle(from_percent=percent, last_percent=percent)
            self._dirty = True
        if percent < cycle.last_percent:
            cycle.last_percent = percent
            self._dirty = True
        if on and cycle.on_since is None:
            cycle.on_since = now
        elif not on:
            self._pause(cycle, now)

    def tick(self) -> None:
        """Book the time switched on so far, so it survives a restart."""
        now = self._now()
        for cycle in self._open.values():
            if cycle.on_since is not None:
                self._pause(cycle, now)
                cycle.on_since = now

    def _pause(self, cycle: OpenCycle, now: datetime) -> None:
        if cycle.on_since is not None:
            cycle.on_seconds += max(0, int((now - cycle.on_since).total_seconds()))
            cycle.on_since = None
            self._dirty = True

    def _close(self, box_id: str, cycle: OpenCycle, now: datetime) -> None:
        self._pause(cycle, now)
        del self._open[box_id]
        self._dirty = True
        used = cycle.from_percent - cycle.last_percent
        if cycle.on_seconds < MIN_SECONDS or used < MIN_USED_PERCENT:
            return
        hours = round(cycle.on_seconds / 3600, 2)
        cycles = self._cycles.setdefault(box_id, [])
        cycles.append(
            {
                "day": now.date().isoformat(),
                "hours": hours,
                "from": cycle.from_percent,
                "to": cycle.last_percent,
                "per_full": round(hours * 100 / used, 1),
            }
        )
        del cycles[:-KEEP_CYCLES]

    # ------------------------------------------------------------ saving

    def save_soon(self) -> None:
        """Write the cycles after a short delay, if something changed."""
        if self._dirty:
            self._dirty = False
            self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_save(self) -> None:
        """Write the cycles now, including the running ones."""
        self.tick()
        self._dirty = False
        await self._store.async_save(self._data_to_save())

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "cycles": self._cycles,
            "open": {
                box_id: {"from": c.from_percent, "to": c.last_percent, "seconds": c.on_seconds}
                for box_id, c in self._open.items()
            },
        }

    # ------------------------------------------------------------ queries

    def summary(self, box_id: str) -> dict[str, Any]:
        """Return what the page shows for one box."""
        now = self._now()
        cycles = list(reversed(self._cycles.get(box_id, [])))
        estimates = [
            c["per_full"]
            for c in cycles[:AVERAGE_OVER]
            if isinstance(c.get("per_full"), int | float)
        ]
        current = self._open.get(box_id)
        return {
            "current": (
                None
                if current is None
                else {
                    "hours": current.hours(now),
                    "from": current.from_percent,
                    "to": current.last_percent,
                    "per_full": current.per_full(now),
                }
            ),
            "cycles": cycles[:20],
            "count": len(cycles),
            "average_full_hours": (
                round(sum(estimates) / len(estimates), 1) if estimates else None
            ),
        }
