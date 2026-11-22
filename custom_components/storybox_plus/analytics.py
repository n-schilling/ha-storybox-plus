"""Listening time, as daily sums.

Kept are sums only, never single plays: per day how long which figure played
on which box, how long each chapter of a figure played, how long each box
played in each hour of the day (for all figures together), and how often
each figure was placed on a box. The
sums live in the integration's own store, not in the recorder, and count
from the setup on; the cloud has no history. Only a Toniebox 2 reports
playback, so only its listening is counted.

A Toniebox 1 with a presence entity (see preferences) gets its active time
instead: how long it was in the network, per day and hour. That is an
indication only, never listening time: the box stays awake for a while after
the last sound, and the entity notices its leaving late. That lag is taken
off the end of every stretch in the network, so a stretch no longer than the
lag counts nothing; time is booked only once it is older than the lag. A
restart of Home Assistant ends a stretch, so one that spans it loses the lag
twice. It is kept apart and enters none of the listening sums.
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
type ChapterSums = dict[str, dict[str, int]]  # tonie_id -> chapter index (from 0) -> seconds
type HourSums = dict[str, dict[str, int]]  # box_id -> hour of the day (0 to 23) -> seconds
type PlacementSums = dict[str, dict[str, int]]  # box_id -> tonie_id -> times placed


class AnalyticsData(TypedDict, total=False):
    days: dict[str, DaySums]  # ISO date -> sums
    chapters: dict[str, ChapterSums]  # ISO date -> sums per chapter
    hours: dict[str, HourSums]  # ISO date -> sums per box and hour
    placements: dict[str, PlacementSums]  # ISO date -> times placed per box and figure
    active: dict[str, HourSums]  # ISO date -> seconds in the network per box and hour


class Analytics:
    """Counts listening seconds per figure, box and day."""

    def __init__(
        self,
        store: Store[AnalyticsData],
        now: Callable[[], datetime],
        keep_days: int = ANALYTICS_KEEP_DAYS,
    ) -> None:
        """Count with the given clock (local time of Home Assistant); keep_days 0 keeps all."""
        self._store = store
        self._now = now
        self.keep_days = keep_days
        self._days: dict[str, DaySums] = {}
        self._chapters: dict[str, ChapterSums] = {}
        self._hours: dict[str, HourSums] = {}
        self._placements: dict[str, PlacementSums] = {}
        # box_id -> (tonie_id, chapter index or None, playing since)
        self._active: dict[str, tuple[str, int | None, datetime]] = {}
        self._awake_sums: dict[str, HourSums] = {}
        # box_id -> (in the network and not yet booked since, the lag to take off its end)
        self._awake: dict[str, tuple[datetime, timedelta]] = {}
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
        if data and isinstance(data.get("chapters"), dict):
            self._chapters = {
                day: {
                    tonie: {index: int(seconds) for index, seconds in chapters.items()}
                    for tonie, chapters in tonies.items()
                }
                for day, tonies in data["chapters"].items()
            }
        if data and isinstance(data.get("hours"), dict):
            self._hours = {
                day: {
                    box: {hour: int(seconds) for hour, seconds in hours.items()}
                    for box, hours in boxes.items()
                    if isinstance(hours, dict)
                }
                for day, boxes in data["hours"].items()
                if isinstance(boxes, dict)
            }
        if data and isinstance(data.get("placements"), dict):
            self._placements = {
                day: {
                    box: {tonie: int(times) for tonie, times in tonies.items()}
                    for box, tonies in boxes.items()
                    if isinstance(tonies, dict)
                }
                for day, boxes in data["placements"].items()
                if isinstance(boxes, dict)
            }
        if data and isinstance(data.get("active"), dict):
            self._awake_sums = {
                day: {
                    box: {hour: int(seconds) for hour, seconds in hours.items()}
                    for box, hours in boxes.items()
                    if isinstance(hours, dict)
                }
                for day, boxes in data["active"].items()
                if isinstance(boxes, dict)
            }
        self._prune()

    # ------------------------------------------------------------ counting

    def awake(self, box_id: str, awake: bool, lag: float = 0) -> None:
        """Note whether a Toniebox 1 is in the network now; anything else than yes ends the count.

        lag: the seconds the box stays in the network after its last use,
        taken off the end of the stretch. A box that is in the network
        already keeps its stretch; only the lag follows.
        """
        now = self._now()
        delay = timedelta(seconds=max(0.0, lag))
        current = self._awake.get(box_id)
        if awake:
            self._awake[box_id] = (current[0] if current else now, delay)
            return
        if current is not None:
            del self._awake[box_id]
            self._add_awake(box_id, current[0], now - current[1])

    def _add_awake(self, box_id: str, start: datetime, end: datetime) -> None:
        for key, hour, seconds in _by_hour(start, end):
            hours = self._awake_sums.setdefault(key, {}).setdefault(box_id, {})
            hours[hour] = hours.get(hour, 0) + seconds
            self._dirty = True

    def placed(self, box_id: str, tonie_id: str) -> None:
        """Count a figure placed on a box."""
        key = self._now().date().isoformat()
        box = self._placements.setdefault(key, {}).setdefault(box_id, {})
        box[tonie_id] = box.get(tonie_id, 0) + 1
        self._dirty = True

    def observe(
        self, box_id: str, tonie_id: str | None, playing: bool, chapter: int | None = None
    ) -> None:
        """Note what a box does now: playing a chapter of a figure, or not."""
        now = self._now()
        active = self._active.get(box_id)
        if active is not None and (not playing or active[0] != tonie_id or active[1] != chapter):
            self._add(box_id, active[0], active[1], active[2], now)
            del self._active[box_id]
            active = None
        if playing and tonie_id is not None and active is None:
            self._active[box_id] = (tonie_id, chapter, now)

    def tick(self) -> None:
        """Book the time counted so far, so the sums are current and survive a restart."""
        now = self._now()
        for box_id, (tonie_id, chapter, since) in list(self._active.items()):
            self._add(box_id, tonie_id, chapter, since, now)
            self._active[box_id] = (tonie_id, chapter, now)
        for box_id, (since, delay) in list(self._awake.items()):
            # Only what stays counted even if the box leaves right now
            until = now - delay
            if until > since:
                self._add_awake(box_id, since, until)
                self._awake[box_id] = (until, delay)

    def _add(
        self, box_id: str, tonie_id: str, chapter: int | None, start: datetime, end: datetime
    ) -> None:
        """Add a played span to the days and hours it touches."""
        for key, hour, seconds in _by_hour(start, end):
            box = self._days.setdefault(key, {}).setdefault(box_id, {})
            box[tonie_id] = box.get(tonie_id, 0) + seconds
            hours = self._hours.setdefault(key, {}).setdefault(box_id, {})
            hours[hour] = hours.get(hour, 0) + seconds
            if chapter is not None:
                chapters = self._chapters.setdefault(key, {}).setdefault(tonie_id, {})
                chapters[str(chapter)] = chapters.get(str(chapter), 0) + seconds
            self._dirty = True

    def set_keep_days(self, days: int) -> None:
        """Keep this many days from now on; older sums go at once (0 keeps all)."""
        self.keep_days = days
        self._prune()
        self.save_soon()

    def _prune(self) -> None:
        if not self.keep_days:
            return
        oldest = (self._now().date() - timedelta(days=self.keep_days)).isoformat()
        for sums in (
            self._days,
            self._chapters,
            self._hours,
            self._placements,
            self._awake_sums,
        ):
            for day in [d for d in sums if d < oldest]:
                del sums[day]
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
        return {
            "days": self._days,
            "chapters": self._chapters,
            "hours": self._hours,
            "placements": self._placements,
            "active": self._awake_sums,
        }

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

    def active_per_box(self, days: int | None = None) -> dict[str, int]:
        """Return the seconds each Toniebox 1 was in the network over the last days."""
        first = None if days is None else self._first_key(days)
        result: dict[str, int] = {}
        for day, boxes in self._awake_sums.items():
            if first is not None and day < first:
                continue
            for box_id, hours in boxes.items():
                result[box_id] = result.get(box_id, 0) + sum(hours.values())
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

    def per_chapter(self, days: int | None = None) -> dict[tuple[str, int], int]:
        """Return seconds per chapter of a figure (index from 0) over the last days."""
        first = None if days is None else self._first_key(days)
        result: dict[tuple[str, int], int] = {}
        for day, tonies in self._chapters.items():
            if first is not None and day < first:
                continue
            for tonie_id, chapters in tonies.items():
                for index, seconds in chapters.items():
                    key = (tonie_id, int(index))
                    result[key] = result.get(key, 0) + seconds
        return result

    def placements_per_tonie(self, days: int | None = None) -> dict[str, int]:
        """Return how often each figure was placed over the last days."""
        first = None if days is None else self._first_key(days)
        result: dict[str, int] = {}
        for day, boxes in self._placements.items():
            if first is not None and day < first:
                continue
            for tonies in boxes.values():
                for tonie_id, times in tonies.items():
                    result[tonie_id] = result.get(tonie_id, 0) + times
        return result

    def per_weekday_hour(
        self, days: int | None = None, box_id: str | None = None
    ) -> list[list[int]]:
        """Return seconds per weekday (Monday first) and hour over the last days, of one box or all."""
        first = None if days is None else self._first_key(days)
        grid = [[0] * 24 for _ in range(7)]
        for day, boxes in self._hours.items():
            if first is not None and day < first:
                continue
            weekday = date.fromisoformat(day).weekday()
            for box, hours in boxes.items():
                if box_id is not None and box != box_id:
                    continue
                for hour, seconds in hours.items():
                    grid[weekday][int(hour)] += seconds
        return grid

    def hour_boxes(self, days: int | None = None) -> set[str]:
        """Return the boxes with hours counted over the last days."""
        first = None if days is None else self._first_key(days)
        return {
            box
            for day, boxes in self._hours.items()
            if first is None or day >= first
            for box in boxes
        }

    def total_before(self, days: int) -> int | None:
        """Return the seconds of the window of the same length right before the last days.

        None while counting did not cover that whole window: a comparison
        with a window that was only partly counted would mislead.
        """
        start, end = self._first_key(2 * days), self._first_key(days)
        if not self._days or min(self._days) > start:
            return None
        return sum(
            sum(sum(t.values()) for t in boxes.values())
            for day, boxes in self._days.items()
            if start <= day < end
        )

    def _first_key(self, days: int) -> str:
        return (self._now().date() - timedelta(days=days - 1)).isoformat()


def _by_hour(start: datetime, end: datetime) -> list[tuple[str, str, int]]:
    """Split a span into the hours it touches: ISO date, hour of the day, seconds."""
    parts: list[tuple[str, str, int]] = []
    while start < end:
        hour_end = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        stop = min(end, hour_end)
        seconds = int((stop - start).total_seconds())
        if seconds > 0:
            parts.append((start.date().isoformat(), str(start.hour), seconds))
        start = stop
    return parts
