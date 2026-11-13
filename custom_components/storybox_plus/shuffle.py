"""Shuffle on swap: a creative figure gets a new order once another figure replaces it.

Per creative figure the user can switch it on. When on a Toniebox 2 a
different figure is placed after it, its chapters are shuffled, so it plays
in a new order the next time. Only a replacement counts: taking the figure
off and putting it back keeps where it was. Between the two figures the box
reports an empty spot; the last figure per box is kept across it, and in
the store, so a restart in between does not lose it. A figure that stands
on another box by then is left alone.
"""

from __future__ import annotations

import random
from typing import Any

from homeassistant.helpers.storage import Store

# A figure needs this many chapters for a new order
MIN_CHAPTERS = 2


class ShuffleOnSwap:
    """The figures to shuffle when replaced, and the last figure per box."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start empty; async_load reads the store."""
        self._store = store
        self._tonies: set[str] = set()
        self._last: dict[str, str] = {}

    async def async_load(self) -> None:
        """Read the store; what does not fit is left out."""
        raw = await self._store.async_load()
        if not isinstance(raw, dict):
            return
        tonies = raw.get("tonies")
        if isinstance(tonies, list):
            self._tonies = {t for t in tonies if isinstance(t, str)}
        last = raw.get("last")
        if isinstance(last, dict):
            self._last = {str(k): v for k, v in last.items() if isinstance(v, str)}

    def enabled(self, tonie_id: str) -> bool:
        """Return whether a figure is shuffled when replaced."""
        return tonie_id in self._tonies

    async def async_set(self, tonie_id: str, enabled: bool) -> None:
        """Switch shuffling on swap on or off for a figure."""
        if enabled:
            self._tonies.add(tonie_id)
        else:
            self._tonies.discard(tonie_id)
        await self.async_save()

    def placed(self, box_id: str, tonie_id: str | None) -> str | None:
        """Take a change of the figure on a box; return the figure to shuffle, if any.

        An empty box changes nothing: the figure before it counts as the
        last one until another is placed.
        """
        if tonie_id is None:
            return None
        before = self._last.get(box_id)
        if before == tonie_id:
            return None
        self._last[box_id] = tonie_id
        self._store.async_delay_save(self._data, 2)
        return before if before is not None and before in self._tonies else None

    async def async_save(self) -> None:
        """Write everything now."""
        await self._store.async_save(self._data())

    def _data(self) -> dict[str, Any]:
        return {"tonies": sorted(self._tonies), "last": dict(self._last)}


def new_order(ids: list[str], pick: random.Random | None = None) -> list[str]:
    """Return the IDs in a random order that differs from the given one."""
    pick = pick or random.SystemRandom()
    if len(set(ids)) < MIN_CHAPTERS:
        return list(ids)
    order = list(ids)
    while order == ids:
        pick.shuffle(order)
    return order
