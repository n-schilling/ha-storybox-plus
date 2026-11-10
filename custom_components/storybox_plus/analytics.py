"""Listening time, as daily sums.

Only how long which figure played on which box on which day is kept: no
single plays, no times of day. The sums live in the integration's own store,
not in the recorder, and count from the setup on; the cloud has no history.
Only a Toniebox 2 reports playback, so only its listening is counted.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TypedDict

from homeassistant.helpers.storage import Store

from .const import ANALYTICS_KEEP_DAYS

# Seconds between two writes of the store while something plays
SAVE_DELAY = 60

type DaySums = dict[str, dict[str, int]]  # box_id -> tonie_id -> seconds


class AnalyticsData(TypedDict):
    days: dict[str, DaySums]  # ISO date -> sums


class Analytics:
    """Counts listening seconds per figure, box and day."""

    def __init__(self, store: Store[AnalyticsData], now: Callable[[], datetime]) -> None:
        """Count with the given clock (local time of Home Assistant)."""
        self._store = store
        self._now = now
        self._days: dict[str, DaySums] = {}
        # box_id -> (tonie_id, playing since)
        self._active: dict[str, tuple[str, datetime]] = {}
        self._dirty = False

    async def async_load(self) -> None:
        """Read the sums of earlier runs."""
        data = await self._store.async_load()
        if data and isinstance(data.get("days"), dict):
            self._days = {
                day: {
                    box: {tonie: int(seconds) for tonie, seconds in tonies.items()}
                    for box, tonies in boxes.items()
                }
                for day, boxes in data["days"].items()
            }
        self._prune()

    # ------------------------------------------------------------ counting

    def observe(self, box_id: str, tonie_id: str | None, playing: bool) -> None:
        """Note what a box does now: playing a figure, or not."""
        now = self._now()
        active = self._active.get(box_id)
        if active is not None and (not playing or active[0] != tonie_id):
            self._add(box_id, active[0], active[1], now)
            del self._active[box_id]
            active = None
        if playing and tonie_id is not None and active is None:
            self._active[box_id] = (tonie_id, now)

    def tick(self) -> None:
        """Book the time counted so far, so the sums are current and survive a restart."""
        now = self._now()
        for box_id, (tonie_id, since) in list(self._active.items()):
            self._add(box_id, tonie_id, since, now)
            self._active[box_id] = (tonie_id, now)

    def _add(self, box_id: str, tonie_id: str, start: datetime, end: datetime) -> None:
        """Add a played span to the days it touches."""
        while start < end:
            midnight = datetime.combine(start.date() + timedelta(days=1), datetime.min.time())
            midnight = midnight.replace(tzinfo=start.tzinfo)
            stop = min(end, midnight)
            seconds = int((stop - start).total_seconds())
            if seconds > 0:
                day = self._days.setdefault(start.date().isoformat(), {})
                box = day.setdefault(box_id, {})
                box[tonie_id] = box.get(tonie_id, 0) + seconds
                self._dirty = True
            start = stop

    def _prune(self) -> None:
        oldest = (self._now().date() - timedelta(days=ANALYTICS_KEEP_DAYS)).isoformat()
        for day in [d for d in self._days if d < oldest]:
            del self._days[day]
            self._dirty = True

    # ------------------------------------------------------------ saving

    def save_soon(self) -> None:
        """Write the sums after a short delay, if something changed."""
        if self._dirty:
            self._dirty = False
            self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_save(self) -> None:
        """Write the sums now, including what plays right now."""
        self.tick()
        self._dirty = False
        await self._store.async_save(self._data_to_save())

    def _data_to_save(self) -> AnalyticsData:
        return {"days": self._days}

    # ------------------------------------------------------------ queries

    @property
    def first_day(self) -> date | None:
        """Return the first day with a count."""
        return date.fromisoformat(min(self._days)) if self._days else None

    def _days_since(self, days: int | None) -> list[tuple[str, DaySums]]:
        if days is None:
            return sorted(self._days.items())
        first = (self._now().date() - timedelta(days=days - 1)).isoformat()
        return sorted((d, s) for d, s in self._days.items() if d >= first)

    def per_tonie(self, days: int | None = None) -> dict[str, int]:
        """Return seconds per figure over the last days (None: all time)."""
        result: dict[str, int] = {}
        for _, boxes in self._days_since(days):
            for tonies in boxes.values():
                for tonie_id, seconds in tonies.items():
                    result[tonie_id] = result.get(tonie_id, 0) + seconds
        return result

    def per_box(self, days: int | None = None) -> dict[str, int]:
        """Return seconds per box over the last days."""
        result: dict[str, int] = {}
        for _, boxes in self._days_since(days):
            for box_id, tonies in boxes.items():
                result[box_id] = result.get(box_id, 0) + sum(tonies.values())
        return result

    def per_day(self, days: int | None = None) -> dict[str, int]:
        """Return seconds per day over the last days."""
        return {
            day: sum(sum(t.values()) for t in boxes.values())
            for day, boxes in self._days_since(days)
        }

    def total(self, days: int | None = None) -> int:
        """Return the seconds listened over the last days."""
        return sum(self.per_day(days).values())
