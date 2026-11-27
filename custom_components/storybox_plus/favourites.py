"""Favourite chapters of a figure: the box is steered by them.

A box plays a figure from front to back and knows no selection. Every
chapter of a figure can be marked as a favourite; how the favourites play
is a mode, set for the account and, where it differs, per figure:

- off: the stars are kept, the box plays as it would.
- first: placed on a Toniebox 2, the figure starts with its favourites,
  one after the other, and plays the other chapters after them.
- random: as first, with another favourite at the front each time.
- only: every other chapter is skipped; after the last favourite the box
  pauses.
- bedtime: first by day, only within a bedtime of the box.

The integration follows the playback reports of the push channel and sends
the box where the order wants it. The beginning of a chapter that is left
can be heard for a moment, because the box reports first and the command
travels through the cloud. Without the cloud or Home Assistant the box
plays everything in its own order.

The order belongs to the figure on the box and begins when the figure is
placed. The same figure taken off for less than two minutes goes on where
it was. A chapter chosen by hand is played: the buttons of the box and of
Home Assistant move along the order, a chapter picked anywhere else is left
alone and the order goes on from it. When a hand presses play on a box that
was paused after the last chapter of the order, the box is no longer
steered for the figure until it is taken off; the page can switch that on
and off as well. What each box plays is kept in the store with the stars,
so a restart of Home Assistant changes nothing for a figure that plays.

The chapters of a bought figure are kept by their position, those of a
creative figure by their ID, so a star stays with its chapter when the
chapters are arranged anew.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import random
import time
from typing import Any, Literal

from homeassistant.helpers.storage import Store

from .cloud import Playback, Tonie, TonieKind

_LOGGER = logging.getLogger(__name__)

type Mode = Literal["off", "first", "random", "only", "bedtime"]
type Steering = Literal["first", "random", "only"]
type Action = (
    tuple[Literal["jump"], int] | tuple[Literal["play"], int] | tuple[Literal["pause"], None]
)

MODES: tuple[Mode, ...] = ("off", "first", "random", "only", "bedtime")
DEFAULT_MODE: Mode = "first"
# The same figure placed again within this many seconds goes on where it was
SHORT_BREAK = 120.0
# What the boxes play is written this many seconds after it changed; unloading and
# stopping Home Assistant write at once
SAVE_DELAY = 60
# How often in a row a command is sent to a box that does not get it; after that the
# chapter plays, and the next chapter gets one try
TRIES = 3
# A figure that was placed is written after this many seconds
PLACED_SAVE_DELAY = 1
# A box missing from this many polls of the cloud in a row is gone: what it played is forgotten
MISSING_POLLS = 3
# The stars of a figure that left the account are kept this many seconds, in case it comes back
GONE_AFTER = 30 * 24 * 3600.0


@dataclass(frozen=True, slots=True)
class Favourites:
    """The favourite chapters of one figure and the mode that differs from the account's."""

    mode: Mode | None
    # Bought figures: positions from 0; creative figures: chapter IDs
    chapters: tuple[int, ...] = ()
    ids: tuple[str, ...] = ()

    def indexes(self, tonie: Tonie) -> tuple[int, ...]:
        """Return the positions of the favourites among the chapters the figure has now."""
        if tonie.kind is TonieKind.CREATIVE:
            return tuple(i for i, c in enumerate(tonie.chapters) if c.id in self.ids)
        if tonie.chapters:
            return tuple(c for c in self.chapters if c < len(tonie.chapters))
        return self.chapters

    def as_dict(self, tonie: Tonie) -> dict[str, Any]:
        """For the page."""
        return {"mode": self.mode, "chapters": list(self.indexes(tonie))}

    def stored(self) -> dict[str, Any]:
        """For the store."""
        data: dict[str, Any] = {"mode": self.mode}
        if self.ids:
            data["ids"] = list(self.ids)
        else:
            data["chapters"] = list(self.chapters)
        return data


@dataclass(frozen=True, slots=True)
class Plan:
    """How a figure is steered now: the mode at work, its favourites, its chapter count."""

    mode: Steering
    chapters: tuple[int, ...]
    count: int


def order_of(
    plan: Plan,
    first: int | None = None,
    pick: random.Random | None = None,
    avoid: int | None = None,
) -> tuple[int, ...]:
    """Return the chapters in the order they play.

    With "only" the favourites; else the favourites and the other chapters
    after them. "random" puts one favourite at the front: the given one if
    it still is a favourite, else one picked by chance, and not the one to
    avoid (the one of last time) while there is another.
    """
    favourites = plan.chapters
    if plan.mode == "only":
        return favourites
    if plan.mode == "random":
        if first not in favourites:
            others = [c for c in favourites if c != avoid] or list(favourites)
            first = (pick or random.SystemRandom()).choice(others)
        favourites = (first, *(c for c in favourites if c != first))
    return (*favourites, *(c for c in range(plan.count) if c not in plan.chapters))


def following(order: tuple[int, ...], chapter: int) -> int | None:
    """Return the chapter that plays after one, or None at the end of the order.

    A chapter outside the order (one chosen by hand while only the
    favourites play) is followed by the next chapter of the order behind it.
    """
    if chapter in order:
        at = order.index(chapter) + 1
        return order[at] if at < len(order) else None
    return next((c for c in order if c > chapter), None)


def preceding(order: tuple[int, ...], chapter: int) -> int:
    """Return the chapter that plays before one; the first one has itself before it."""
    if chapter in order:
        return order[max(0, order.index(chapter) - 1)]
    return next((c for c in reversed(order) if c < chapter), order[0])


@dataclass(slots=True)
class Run:
    """What a box plays of the figure on it."""

    figure: str
    # None: the figure is not steered (off, no favourites)
    plan: Plan | None = None
    order: tuple[int, ...] = ()
    # Whether the figure was heard playing since it was placed
    started: bool = False
    # The chapter last reported, and the last one that was let play
    chapter: int | None = None
    base: int | None = None
    # The chapter the box was sent to; sent again until the box reports it
    wanted: int | None = None
    # The chapter a hand chose in Home Assistant; let play once the box reports it
    chosen: int | None = None
    # The pause after the end of the order: sent, then reported by the box
    paused: Literal["sent", "reported"] | None = None
    # The end of the figure was reported and looked at
    ended: bool = False
    # A hand wants to hear everything: not steered until the figure is taken off
    suspended: bool = False
    # When the figure was taken off (timestamp)
    left: float | None = None
    # How often in a row a command did not reach the box
    failures: int = 0
    # Read from the store: its plan follows with the first report, which is no change of it
    restored: bool = False
    # The chapter of the last report that played, as seen by this run of Home Assistant:
    # an end is acted on only if the chapter was heard running into it
    heard: int | None = None
    # The box reported another chapter than the chosen one, once: the chosen one may still come
    chosen_missed: bool = False

    @property
    def steered(self) -> bool:
        """Return whether the order is at work."""
        return self.plan is not None and not self.suspended


class FavouriteChapters:
    """The favourites of the figures of one account, and the steering by them."""

    def __init__(self, store: Store[dict[str, Any]], pick: random.Random | None = None) -> None:
        """Start empty; async_load reads the store."""
        self._store = store
        self._pick = pick
        self._tonies: dict[str, Favourites] = {}
        self._runs: dict[str, Run] = {}
        # Per figure the favourite that was at the front last time ("random")
        self._firsts: dict[str, int] = {}
        # Per box the polls in a row it was missing from; per figure since when it is gone
        self._missing: dict[str, int] = {}
        self._gone: dict[str, float] = {}
        # When the write that is on its way is due (monotonic seconds)
        self._write_by: float | None = None

    # ------------------------------------------------------------ the stars

    async def async_load(self) -> None:
        """Read the store; what does not fit is left out.

        Lists of before the modes carry "active": on was "only", off is "off".
        """
        raw = await self._store.async_load()
        if not isinstance(raw, dict):
            return
        tonies = raw.get("tonies")
        for tonie_id, item in tonies.items() if isinstance(tonies, dict) else ():
            if not isinstance(item, dict):
                continue
            mode = item.get("mode")
            if "active" in item and "mode" not in item:
                mode = "only" if item["active"] else "off"
            favourites = Favourites(
                mode if mode in MODES else None,
                _clean(item.get("chapters")),
                _clean_ids(item.get("ids")),
            )
            if favourites.mode or favourites.chapters or favourites.ids:
                self._tonies[str(tonie_id)] = favourites
        runs = raw.get("runs")
        for box_id, item in runs.items() if isinstance(runs, dict) else ():
            if (run := _run_from(item)) is not None:
                self._runs[str(box_id)] = run
        firsts = raw.get("firsts")
        for tonie_id, first in firsts.items() if isinstance(firsts, dict) else ():
            if isinstance(first, int) and not isinstance(first, bool):
                self._firsts[str(tonie_id)] = first
        gone = raw.get("gone")
        for tonie_id, since in gone.items() if isinstance(gone, dict) else ():
            if isinstance(since, (int, float)) and not isinstance(since, bool):
                self._gone[str(tonie_id)] = float(since)

    def get(self, tonie_id: str) -> Favourites | None:
        """The favourites of a figure, if any were set."""
        return self._tonies.get(tonie_id)

    def indexes(self, tonie: Tonie) -> tuple[int, ...]:
        """Return the positions of the favourite chapters of a figure."""
        favourites = self._tonies.get(tonie.id)
        return favourites.indexes(tonie) if favourites else ()

    def describe(self, tonie: Tonie) -> dict[str, Any] | None:
        """The favourites of a figure as the page shows them."""
        favourites = self._tonies.get(tonie.id)
        return favourites.as_dict(tonie) if favourites else None

    async def async_set(
        self, tonie: Tonie, chapters: list[int], mode: Mode | None
    ) -> Favourites | None:
        """Keep the favourites of a figure and its own mode; without either the figure is forgotten."""
        cleaned = _clean(chapters)
        if tonie.kind is TonieKind.CREATIVE:
            ids = tuple(dict.fromkeys(c.id for i, c in enumerate(tonie.chapters) if i in cleaned))
            favourites = Favourites(mode, (), ids)
        else:
            favourites = Favourites(mode, cleaned)
        if favourites.mode is None and not favourites.chapters and not favourites.ids:
            self._tonies.pop(tonie.id, None)
            await self.async_save()
            return None
        self._tonies[tonie.id] = favourites
        await self.async_save()
        return favourites

    async def async_set_mode(self, tonie: Tonie, mode: Mode | None) -> Favourites | None:
        """Keep the mode of a figure and leave its stars as they are."""
        kept = self._tonies.get(tonie.id)
        favourites = Favourites(mode, kept.chapters if kept else (), kept.ids if kept else ())
        await self._async_keep(tonie.id, favourites)
        return self._tonies.get(tonie.id)

    async def async_star(self, tonie: Tonie, chapter: int, favourite: bool | None = None) -> bool:
        """Mark one chapter as a favourite or not (None: the other way round); return what it is.

        A creative figure's star goes by the ID of the chapter: chapters that
        share an ID share the star, and it comes off for all of them.
        """
        kept = self._tonies.get(tonie.id)
        mode = kept.mode if kept else None
        if tonie.kind is TonieKind.CREATIVE:
            chapter_id = tonie.chapters[chapter].id
            present = {c.id for c in tonie.chapters}
            ids = [i for i in (kept.ids if kept else ()) if i in present]
            if favourite is None:
                favourite = chapter_id not in ids
            if favourite and chapter_id not in ids:
                ids.append(chapter_id)
            elif not favourite:
                ids = [i for i in ids if i != chapter_id]
            await self._async_keep(tonie.id, Favourites(mode, (), tuple(ids)))
            return favourite
        chapters = set(self.indexes(tonie))
        if favourite is None:
            favourite = chapter not in chapters
        if favourite:
            chapters.add(chapter)
        else:
            chapters.discard(chapter)
        await self.async_set(tonie, sorted(chapters), mode)
        return favourite

    async def _async_keep(self, tonie_id: str, favourites: Favourites) -> None:
        if favourites.mode is None and not favourites.chapters and not favourites.ids:
            self._tonies.pop(tonie_id, None)
        else:
            self._tonies[tonie_id] = favourites
        await self.async_save()

    def keep(self, box_ids: set[str], tonie_ids: set[str], now: float) -> None:
        """Forget what belongs to boxes and figures that left the account, after a while.

        One answer of the cloud that lacks a box or a figure proves nothing:
        what a box played goes once the box was missing from a few polls in
        a row, the stars of a figure a month after it was last seen.
        """
        changed = False
        for box_id in list(self._runs):
            if box_id in box_ids:
                self._missing.pop(box_id, None)
                continue
            self._missing[box_id] = self._missing.get(box_id, 0) + 1
            if self._missing[box_id] >= MISSING_POLLS:
                del self._runs[box_id]
                del self._missing[box_id]
                changed = True
        for tonie_id in {*self._tonies, *self._firsts, *self._gone}:
            if tonie_id in tonie_ids:
                changed = self._gone.pop(tonie_id, None) is not None or changed
            elif tonie_id not in self._gone:
                self._gone[tonie_id] = now
                changed = True
            elif now - self._gone[tonie_id] >= GONE_AFTER:
                self._tonies.pop(tonie_id, None)
                self._firsts.pop(tonie_id, None)
                del self._gone[tonie_id]
                changed = True
        if changed:
            self._save_soon()

    async def async_save(self) -> None:
        """Write everything now."""
        await self._store.async_save(self._data())

    def _save_soon(self, delay: float = SAVE_DELAY) -> None:
        """Write after a delay; a write that is due sooner is never put off by a later one."""
        now = time.monotonic()
        if self._write_by is not None and self._write_by > now:
            delay = min(delay, self._write_by - now)
        self._write_by = now + delay
        self._store.async_delay_save(self._data, delay)

    def _data(self) -> dict[str, Any]:
        return {
            "tonies": {k: v.stored() for k, v in self._tonies.items()},
            "runs": {box_id: _run_data(run) for box_id, run in self._runs.items()},
            "firsts": dict(self._firsts),
            "gone": dict(self._gone),
        }

    # ------------------------------------------------------------ what a box plays

    def steering(self, box_id: str, tonie_id: str | None) -> Steering | None:
        """Return the mode at work for the figure on a box; None while it is not steered."""
        run = self._runs.get(box_id)
        if run is None or run.figure != tonie_id or run.plan is None or run.suspended:
            return None
        return run.plan.mode

    def suspended(self, box_id: str, tonie_id: str | None) -> bool:
        """Return whether the figure on a box plays everything until it is taken off."""
        run = self._runs.get(box_id)
        return run is not None and run.figure == tonie_id and run.suspended

    def suspend(self, box_id: str, tonie_id: str, suspended: bool) -> None:
        """Let the figure on a box play everything until it is taken off, or steer it again."""
        run = self._runs.get(box_id)
        if run is None or run.figure != tonie_id:
            # Nothing was reported of it yet: it counts as playing, not as placed just now
            run = self._runs[box_id] = Run(tonie_id, started=True)
        run.suspended = suspended
        run.wanted = run.chosen = run.paused = None
        run.base = run.chapter if run.chapter is not None else run.base
        self._save_soon()

    def first(self, box_id: str, tonie_id: str | None) -> int | None:
        """Return the chapter the order of the figure on a box begins with, while it is steered."""
        run = self._runs.get(box_id)
        if run is None or run.figure != tonie_id or not run.steered or not run.order:
            return None
        return run.order[0]

    def neighbour(self, box_id: str, tonie_id: str | None, step: int) -> int | None:
        """Return the chapter after (1) or before (-1) the one that plays, by the order.

        None while the figure is not steered, and after the last chapter of
        the order: the box then has no chapter to go to by it.
        """
        run = self._runs.get(box_id)
        if (
            run is None
            or run.figure != tonie_id
            or not run.steered
            or not run.order
            or run.base is None
        ):
            return None
        return following(run.order, run.base) if step > 0 else preceding(run.order, run.base)

    def chosen(self, box_id: str, tonie_id: str | None, chapter: int) -> None:
        """Note the chapter Home Assistant sends a box to: it plays, whatever the order says.

        What the box was sent for before, and a pause after the end of the
        order, are dropped with it.
        """
        run = self._runs.get(box_id)
        if tonie_id is None:
            return
        if run is None or run.figure != tonie_id:
            # Nothing was reported of the figure yet: it counts as playing, not as placed
            run = self._runs[box_id] = Run(tonie_id, started=True)
        run.wanted = None
        run.paused = None
        run.failures = 0
        run.chosen_missed = False
        if chapter == run.chapter and run.started:
            # The chapter the box is in, from its start: no other one will be reported
            run.base = chapter
            run.chosen = None
        else:
            # Also for a figure that is to begin (placed, or over with its end): the
            # chapter is the one it begins with
            run.chosen = chapter

    def unchosen(self, box_id: str, chapter: int) -> None:
        """Take back a chapter Home Assistant chose: the command did not reach the box."""
        run = self._runs.get(box_id)
        if run is not None and run.chosen == chapter:
            run.chosen = None
            run.chosen_missed = False

    def failed(self, box_id: str) -> None:
        """Note that a command did not reach the box: the next report sends it again.

        After a few times in a row the chapter the box is in is let play; the
        chapter after it gets one more try.
        """
        run = self._runs.get(box_id)
        if run is None:
            return
        run.failures += 1
        if run.failures >= TRIES:
            _LOGGER.debug("The box did not get a command %s times: the chapter plays", TRIES)
            run.wanted = run.paused = None
            if run.chapter is not None:
                run.base = run.chapter
            return
        run.chapter = None
        run.ended = False

    def observe(
        self,
        box_id: str,
        playback: Playback | None,
        plan_for: Callable[[str], Plan | None],
    ) -> Action | None:
        """Take a playback report of a box and return what to send, if anything.

        ``plan_for`` tells how a figure is steered now. Only a report that
        plays, or the one that tells the figure ended, is acted on, and every
        chapter once: the reports that follow while the same chapter plays
        change nothing.
        """
        if playback is None:
            return None
        if playback.tonie_id is None:
            run = self._runs.get(box_id)
            if run is None:
                # An empty box: the figure that comes next is placed, not found playing
                self._runs[box_id] = Run("", left=playback.received_at.timestamp())
                self._save_soon()
            elif run.left is None:
                run.left = playback.received_at.timestamp()
                self._save_soon()
            return None
        if playback.chapter is None:
            return None
        known = self._runs.get(box_id)
        before = _run_data(known) if known is not None else None
        run = self._run(box_id, playback, plan_for(playback.tonie_id))
        action = self._decide(run, playback)
        if action is not None:
            _LOGGER.debug("Chapter %s of a figure on a box: %s", playback.chapter + 1, action)
        if run is not known:
            # Placed: written at once, so a crash right after does not make it "placed" again
            self._save_soon(PLACED_SAVE_DELAY)
        elif _run_data(run) != before:
            # Only what is kept counts: most reports change nothing of it
            self._save_soon()
        return action

    def sync(self, box_id: str, tonie_id: str | None, plan: Plan | None) -> None:
        """Give the figure on a box the plan it is steered by now.

        Before the buttons of Home Assistant ask for the order: after a
        restart the plan is not known until the box reports.
        """
        run = self._runs.get(box_id)
        if run is not None and run.figure == tonie_id and run.left is None:
            self._apply(run, plan)

    def _run(self, box_id: str, playback: Playback, plan: Plan | None) -> Run:
        """Return what the box plays of the figure reported, begun anew if it was placed."""
        figure = playback.tonie_id
        assert figure is not None
        run = self._runs.get(box_id)
        now = playback.received_at.timestamp()
        if run is None:
            # Nothing is known of the box (first use, a store that was lost): the figure
            # counts as playing, not as placed just now, so nothing jumps in mid-play
            run = self._runs[box_id] = Run(figure, started=True)
        elif run.figure != figure or (run.left is not None and now - run.left >= SHORT_BREAK):
            # Placed; a chapter Home Assistant chose for the figure meanwhile stays chosen
            chosen = run.chosen if run.figure == figure else None
            run = self._runs[box_id] = Run(figure, chosen=chosen)
        elif run.left is not None and run.paused is not None:
            # Back after a short break, and the order was over: placed again, it begins
            # anew. That the box plays now is no hand that pressed play
            run.paused = None
            run.started = False
        run.left = None
        self._apply(run, plan)
        return run

    def _apply(self, run: Run, plan: Plan | None) -> None:
        """Take the plan a run is steered by; a new one changes the order from where it is."""
        if plan != run.plan:
            first = run.order[0] if run.order else None
            # Placed anew, "random" takes another favourite than last time
            avoid = self._firsts.get(run.figure) if first is None else None
            run.plan = plan
            run.order = order_of(plan, first, self._pick, avoid) if plan else ()
            if plan is not None and plan.mode == "random":
                self._firsts[run.figure] = run.order[0]
            if run.wanted is not None or run.paused == "sent":
                # A command is on its way, or was lost: the chapter the box reports
                # next is judged anew by the new order
                run.chapter = None
            run.wanted = None
            if not (run.restored and run.paused is not None):
                # After a restart the pause behind the end of the order still stands
                run.paused = None
            run.failures = 0
        run.restored = False

    def _decide(self, run: Run, playback: Playback) -> Action | None:
        new = playback.chapter
        assert new is not None
        if not run.steered:
            run.chapter = run.base = new
            run.started = run.started or playback.playing
            run.wanted = run.chosen = run.paused = None
            if playback.playing:
                run.heard = new
            return None
        order = run.order
        if run.paused is not None:
            if not playback.playing:
                # The pause arrived; reports before it still said playing
                run.paused = "reported"
                run.failures = 0
                run.chapter = new
                return None
            if run.paused == "reported":
                run.paused = None
                run.suspended = True
                run.chapter = run.base = new
                _LOGGER.debug("Play pressed after the end of the order: the figure plays on")
                return None
        if playback.ended:
            # The last chapter of the figure ran out, the order may go on. An end found as
            # it is (after a restart, after a gap of the push channel) starts nothing:
            # the box would begin to play long after it fell silent
            if run.ended or not run.started or run.base is None or run.heard != new:
                return None
            run.ended = True
            target = following(order, run.base)
            if target is None:
                # The order is over with the figure: what plays next begins it anew
                run.started = False
                return None
            run.wanted = target
            return ("play", target)
        if not playback.playing:
            return None
        run.ended = False
        run.heard = new
        if not run.started:
            # Placed, or started again after its end: the order begins
            run.started = True
            run.chapter = new
            if new == run.chosen:
                # Home Assistant sent the box here
                run.base = new
                run.chosen = None
                return None
            run.chosen = None
            if run.plan is not None and run.plan.mode == "only":
                target = new if new in order else following(order, new)
                target = order[0] if target is None else target
            else:
                target = order[0]
            if target == new:
                run.base = new
                return None
            run.wanted = target
            return ("jump", target)
        if new == run.chapter:
            return None
        run.chapter = new
        if run.paused == "sent":
            # The pause did not arrive and the box moved on
            return ("pause", None)
        if run.wanted is not None:
            if new == run.wanted:
                run.base = new
                run.wanted = None
                run.failures = 0
                return None
            # The command did not arrive
            return ("jump", run.wanted)
        if new == run.chosen or run.base is None:
            run.base = new
            run.chosen = None
            run.chosen_missed = False
            return None
        if run.chosen is not None:
            if not run.chosen_missed:
                # The box moved on before it got the command: the chosen chapter may
                # still come, this one is let play meanwhile
                run.chosen_missed = True
                run.base = new
                return None
            run.chosen = None
            run.chosen_missed = False
        step = new - run.base
        if step == 1:
            target = following(order, run.base)
            if target is None:
                run.paused = "sent"
                return ("pause", None)
        elif step == -1:
            target = preceding(order, run.base)
        else:
            # Picked somewhere else: it plays, the order goes on from it
            run.base = new
            return None
        if target == new:
            run.base = new
            return None
        run.wanted = target
        return ("jump", target)


def _clean(chapters: Any) -> tuple[int, ...]:
    if not isinstance(chapters, list):
        return ()
    return tuple(
        sorted({c for c in chapters if isinstance(c, int) and not isinstance(c, bool) and c >= 0})
    )


def _clean_ids(ids: Any) -> tuple[str, ...]:
    if not isinstance(ids, list):
        return ()
    return tuple(dict.fromkeys(i for i in ids if isinstance(i, str)))


def _run_data(run: Run) -> dict[str, Any]:
    """What is kept of a run."""
    return {
        "figure": run.figure,
        "first": run.order[0] if run.order else None,
        "started": run.started,
        "base": run.base,
        "suspended": run.suspended,
        "left": run.left,
        # The pause behind the end of the order: play pressed after it sets the figure free
        "paused": run.paused,
    }


def _run_from(item: Any) -> Run | None:
    """Read what a box played from the store; the plan follows with the next report."""
    if not isinstance(item, dict) or not isinstance(item.get("figure"), str):
        return None

    def number(key: str) -> int | None:
        value = item.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    first = number("first")
    left = item.get("left")
    return Run(
        item["figure"],
        order=() if first is None else (first,),
        started=item.get("started") is True,
        base=number("base"),
        chapter=number("base"),
        suspended=item.get("suspended") is True,
        paused=item["paused"] if item.get("paused") in ("sent", "reported") else None,
        restored=True,
        left=float(left) if isinstance(left, (int, float)) and not isinstance(left, bool) else None,
    )
