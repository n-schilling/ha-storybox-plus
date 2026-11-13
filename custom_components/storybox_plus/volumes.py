"""Volume per figure: while a figure stands on a Toniebox 2, the box plays at its level.

A figure can carry a volume level (1 to 13, the box's own steps). When it is
placed on a Toniebox 2, the integration remembers the level the box had and
sets the figure's; when the figure is taken off or replaced, the remembered
level comes back exactly, whatever was turned at the box in between. A
figure placed right after another one with a level starts from the level
before that one, so a chain of figures never drifts.

The remembered levels live in the store, so a restart in between still
restores them. Without a known level of the box (it has not reported one
yet) the figure's level is not set, because it could not be undone.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.storage import Store

from .cloud import VOLUME_LEVELS

_LOGGER = logging.getLogger(__name__)


class FigureVolumes:
    """The levels of the figures of one account, and the levels to restore per box."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start empty; async_load reads the store."""
        self._store = store
        self._levels: dict[str, int] = {}
        # Per box: the figure whose level is set, and the level the box had before
        self._raised: dict[str, tuple[str, int]] = {}

    async def async_load(self) -> None:
        """Read the store; what does not fit is left out."""
        raw = await self._store.async_load()
        if not isinstance(raw, dict):
            return
        levels = raw.get("tonies")
        if isinstance(levels, dict):
            self._levels = {
                str(k): v for k, v in levels.items() if isinstance(v, int) and _valid(v)
            }
        raised = raw.get("boxes")
        if isinstance(raised, dict):
            for box_id, item in raised.items():
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("tonie"), str)
                    and isinstance(item.get("previous"), int)
                ):
                    self._raised[str(box_id)] = (item["tonie"], item["previous"])

    def get(self, tonie_id: str) -> int | None:
        """Return the level of a figure, if one was set."""
        return self._levels.get(tonie_id)

    async def async_set(self, tonie_id: str, level: int | None) -> None:
        """Keep the level of a figure; None forgets it."""
        if level is None:
            self._levels.pop(tonie_id, None)
        else:
            self._levels[tonie_id] = level
        await self.async_save()

    def placed(self, box_id: str, after: str | None, current: int | None) -> int | None:
        """Take a change of the figure on a box; return the level to send, if any.

        ``current`` is the level the box reports right now. The answer is
        the figure's level when one is set and the level before it is known,
        else the level to restore when a figure with a level left, else None.
        """
        before = self._raised.pop(box_id, None)
        base = before[1] if before is not None else current
        level = self._levels.get(after) if after is not None else None
        if after is not None and level is not None and base is not None:
            self._raised[box_id] = (after, base)
            return level
        if level is not None:
            _LOGGER.debug("The box's volume is unknown, so the figure's level is not set")
        return before[1] if before is not None else None

    def raised(self, box_id: str) -> str | None:
        """Return the figure whose level is set on a box now."""
        item = self._raised.get(box_id)
        return item[0] if item else None

    def save_soon(self) -> None:
        """Write the levels to restore after a change of figure."""
        self._store.async_delay_save(self._data, 2)

    async def async_save(self) -> None:
        """Write everything now."""
        await self._store.async_save(self._data())

    def _data(self) -> dict[str, Any]:
        return {
            "tonies": dict(self._levels),
            "boxes": {k: {"tonie": t, "previous": p} for k, (t, p) in self._raised.items()},
        }


def _valid(level: int) -> bool:
    return 1 <= level <= VOLUME_LEVELS
