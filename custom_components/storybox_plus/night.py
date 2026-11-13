"""Night mode of the light ring: dimmed during a time span, back to normal afterwards.

Per Toniebox 2 the user sets a span (start and end, in the box's time zone,
across midnight if the end comes first), a brightness for the night and one
for the rest of the day. The integration sets the box's light ring when the
span begins and when it ends.

It acts on the change of phase only, not on every poll: a brightness set in
the app in between stays until the next change. Which phase was applied last
is kept in the store, so a change missed while Home Assistant was not running
is made up at the next start; a change the cloud refused is tried again with
the next poll.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
import logging
from typing import Any, Literal

from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

type Phase = Literal["night", "day"]


@dataclass(frozen=True, slots=True)
class NightMode:
    """The night mode of one box."""

    enabled: bool
    start: str
    end: str
    night: int
    day: int
    # The phase whose brightness was set on the box last; None: nothing yet
    applied: Phase | None = None

    def as_dict(self) -> dict[str, Any]:
        """For the store and the page."""
        return {
            "enabled": self.enabled,
            "start": self.start,
            "end": self.end,
            "night": self.night,
            "day": self.day,
            "applied": self.applied,
        }


def _clock(value: str) -> time:
    hour, minute = (int(p) for p in value.split(":"))
    return time(hour, minute)


def phase(mode: NightMode, now: datetime) -> Phase:
    """Return whether it is night or day for the box at that (box-local) time."""
    start, end, current = _clock(mode.start), _clock(mode.end), now.time()
    if start == end:
        return "day"
    if start < end:
        return "night" if start <= current < end else "day"
    return "night" if current >= start or current < end else "day"


def next_change(mode: NightMode, now: datetime) -> datetime:
    """Return the next start or end of the span after now (box-local)."""
    found: list[datetime] = []
    for value in (mode.start, mode.end):
        at = datetime.combine(now.date(), _clock(value), tzinfo=now.tzinfo)
        if at <= now:
            at = datetime.combine(now.date() + timedelta(days=1), _clock(value), tzinfo=now.tzinfo)
        found.append(at)
    return min(found)


def brightness(mode: NightMode, current: Phase) -> int:
    """Return the brightness of a phase."""
    return mode.night if current == "night" else mode.day


class NightModes:
    """The night modes of the boxes of one account, kept in the integration's store."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start empty; async_load reads the store."""
        self._store = store
        self._boxes: dict[str, NightMode] = {}

    async def async_load(self) -> None:
        """Read the store; an entry that does not fit is left out."""
        raw = await self._store.async_load()
        boxes = raw.get("boxes") if isinstance(raw, dict) else None
        if not isinstance(boxes, dict):
            return
        for box_id, item in boxes.items():
            try:
                mode = NightMode(
                    enabled=bool(item["enabled"]),
                    start=str(item["start"]),
                    end=str(item["end"]),
                    night=int(item["night"]),
                    day=int(item["day"]),
                    applied=item.get("applied")
                    if item.get("applied") in ("night", "day")
                    else None,
                )
                _clock(mode.start)
                _clock(mode.end)
            except KeyError, TypeError, ValueError:
                _LOGGER.debug("A night mode in the store is not readable and left out")
                continue
            self._boxes[str(box_id)] = mode

    def get(self, box_id: str) -> NightMode | None:
        """Return the night mode of a box, if one was set."""
        return self._boxes.get(box_id)

    async def async_set(self, box_id: str, mode: NightMode) -> NightMode:
        """Keep a new night mode; it is applied anew, whatever was applied before."""
        mode = replace(mode, applied=None)
        self._boxes[box_id] = mode
        await self._async_save()
        return mode

    async def async_applied(self, box_id: str, current: Phase) -> None:
        """Note that the brightness of a phase is on the box now."""
        if (mode := self._boxes.get(box_id)) is not None:
            self._boxes[box_id] = replace(mode, applied=current)
            await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save({"boxes": {k: v.as_dict() for k, v in self._boxes.items()}})
