"""Favourite chapters of bought figures: the box is steered to them.

A box plays a figure from front to back and knows no selection. While a
figure's favourites are switched on and the figure plays on a Toniebox 2,
the integration follows the playback reports of the push channel: a
chapter that is no favourite is left at once, forwards to the next
favourite or, after a jump back at the box, to the previous one; after the
last favourite the box pauses. The beginning of a skipped chapter can be
heard for a moment, because the box reports first and the command travels
through the cloud. Without the cloud or Home Assistant the box plays
everything. The lists live in the integration's own store.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Literal

from homeassistant.helpers.storage import Store

from .cloud import Playback

_LOGGER = logging.getLogger(__name__)

type Action = tuple[Literal["jump"], int] | tuple[Literal["pause"], None]


@dataclass(frozen=True, slots=True)
class Favourites:
    """The favourite chapters of one figure, as 0-based indexes, and whether they steer."""

    active: bool
    chapters: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        """For the page and the store."""
        return {"active": self.active, "chapters": list(self.chapters)}


def decide(favourites: Favourites, chapter: int, previous: int | None) -> Action | None:
    """What to do about a chapter that began to play, given the chapter before it.

    Nothing while the favourites are off, empty, or the chapter is one of
    them. Backwards (the chapter lies before the previous one) the previous
    favourite is taken, or the first when none lies before; otherwise the
    next favourite, and after the last one the box pauses.
    """
    if not favourites.active or not favourites.chapters or chapter in favourites.chapters:
        return None
    if previous is not None and chapter < previous:
        earlier = [c for c in favourites.chapters if c < chapter]
        return ("jump", earlier[-1] if earlier else favourites.chapters[0])
    later = [c for c in favourites.chapters if c > chapter]
    return ("jump", later[0]) if later else ("pause", None)


class FavouriteChapters:
    """The favourites of the figures of one account, and the steering by them."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start empty; async_load reads the store."""
        self._store = store
        self._tonies: dict[str, Favourites] = {}
        # The playback each box was last looked at for: (figure, chapter)
        self._seen: dict[str, tuple[str, int]] = {}

    async def async_load(self) -> None:
        """Read the lists from the store; what does not fit is left out."""
        raw = await self._store.async_load()
        tonies = raw.get("tonies") if isinstance(raw, dict) else None
        if not isinstance(tonies, dict):
            return
        for tonie_id, item in tonies.items():
            if not isinstance(item, dict) or not isinstance(item.get("chapters"), list):
                continue
            chapters = _clean(item["chapters"])
            if chapters:
                self._tonies[str(tonie_id)] = Favourites(bool(item.get("active")), chapters)

    def get(self, tonie_id: str) -> Favourites | None:
        """The favourites of a figure, if any were set."""
        return self._tonies.get(tonie_id)

    async def async_set(
        self, tonie_id: str, chapters: list[int], active: bool
    ) -> Favourites | None:
        """Keep the list of a figure; an empty list forgets the figure."""
        cleaned = _clean(chapters)
        favourites = Favourites(active, cleaned) if cleaned else None
        if favourites is None:
            self._tonies.pop(tonie_id, None)
        else:
            self._tonies[tonie_id] = favourites
        await self._store.async_save({"tonies": {k: v.as_dict() for k, v in self._tonies.items()}})
        return favourites

    def observe(self, box_id: str, playback: Playback | None) -> Action | None:
        """Take a playback report of a box and return what to send, if anything.

        Every (figure, chapter) pair is looked at once per box: the reports
        that follow while the same chapter plays, and while a command is on
        its way, change nothing. A report that is not playing is remembered
        but never acted on: a box paused after the last favourite plays the
        chapter it stopped in when a hand presses play, and is paused again
        when the next chapter begins.
        """
        if playback is None or playback.tonie_id is None or playback.chapter is None:
            self._seen.pop(box_id, None)
            return None
        now = (playback.tonie_id, playback.chapter)
        last = self._seen.get(box_id)
        if last == now:
            return None
        self._seen[box_id] = now
        if not playback.playing:
            return None
        favourites = self._tonies.get(playback.tonie_id)
        if favourites is None:
            return None
        previous = last[1] if last is not None and last[0] == playback.tonie_id else None
        action = decide(favourites, playback.chapter, previous)
        if action is not None:
            _LOGGER.debug(
                "Chapter %s of a figure is no favourite: %s", playback.chapter + 1, action
            )
        return action


def _clean(chapters: list[Any]) -> tuple[int, ...]:
    return tuple(
        sorted({c for c in chapters if isinstance(c, int) and not isinstance(c, bool) and c >= 0})
    )
