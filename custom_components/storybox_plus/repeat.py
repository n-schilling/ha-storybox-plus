"""Repeat: a Toniebox 2 plays a figure, or one chapter of it, again and again.

The box knows no repeat. While one is set for a box, the integration follows
the playback reports of the push channel and sends the box back: with "all"
to the first chapter once the figure has ended, with "one" to the start of
the chapter that just ran out. The beginning of the next chapter can be
heard for a moment, because the box reports first and the command travels
through the cloud. Without the cloud or Home Assistant the box plays on as
it would. The repeat belongs to the figure on the box: it ends when the
figure is taken off.
"""

from __future__ import annotations

from typing import Literal

from .cloud import Playback

type Mode = Literal["all", "one"]
MODES: tuple[Mode, ...] = ("all", "one")
# A chapter that begins this close to the end of the one before it followed by itself (s);
# earlier, a hand skipped to it
NATURAL_END = 5.0


def decide(mode: Mode, playback: Playback, last: Playback | None) -> int | None:
    """Return the chapter to play from its start, given a report and the one before it.

    The end of the figure starts the first chapter again ("all") or the last
    one ("one"). A chapter that follows the one before it by itself is sent
    back with "one"; one a hand skipped to is left alone, and so is anything
    with "all" before the end.
    """
    if playback.tonie_id is None or playback.chapter is None:
        return None
    same = last is not None and last.tonie_id == playback.tonie_id
    if playback.ended:
        # Reported again while the command travels: acted on once
        if same and last is not None and last.ended:
            return None
        return 0 if mode == "all" else playback.chapter
    if mode != "one" or not playback.playing or not same or last is None:
        return None
    if last.chapter is None or playback.chapter != last.chapter + 1 or not last.playing:
        return None
    if last.duration is None or last.position is None:
        return None
    runs_out = last.received_at.timestamp() + last.duration - last.position
    if playback.received_at.timestamp() < runs_out - NATURAL_END:
        return None
    return last.chapter
