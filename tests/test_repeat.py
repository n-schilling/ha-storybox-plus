"""Repeat on a Toniebox 2: the whole figure or one chapter, steered from the push channel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.cloud import Playback
from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.repeat import decide

from .conftest import BOX_ID, CLASSIC_BOX_ID, TONIE_ID, PushChannels, entity_id

START = datetime(2026, 11, 22, 18, 0, tzinfo=UTC)
JUMP = lambda chapter: ("playback", {"action": "setPosition", "chapter": chapter, "ms": 0})
PLAY = ("playback", {"action": "start"})


def _report(chapter: int = 1, after: float = 0, **fields: Any) -> Playback:
    values: dict[str, Any] = {"paused": False, "ended": False, "duration": 200.0, "position": 0.0}
    values.update(fields)
    return Playback(
        tonie_id=fields.pop("tonie_id", "t1"),
        chapter=chapter,
        received_at=START + timedelta(seconds=after),
        **{k: v for k, v in values.items() if k != "tonie_id"},
    )


@pytest.mark.parametrize(
    ("mode", "playback", "last", "expected"),
    [
        # The figure ended: from the first chapter, or the last one again
        ("all", _report(4, ended=True), _report(4), 0),
        ("one", _report(4, ended=True), _report(4), 4),
        # An end found as it is, after a restart, starts nothing
        ("all", _report(4, ended=True), None, None),
        ("one", _report(4, ended=True), _report(4, tonie_id="other"), None),
        # Reported again while the command travels
        ("all", _report(4, ended=True), _report(4, ended=True), None),
        # A chapter ran out and the next began
        ("one", _report(2, after=200), _report(1), 1),
        ("one", _report(2, after=197), _report(1), 1),
        ("all", _report(2, after=200), _report(1), None),
        # A hand skipped: forwards early, backwards, two ahead
        ("one", _report(2, after=60), _report(1), None),
        ("one", _report(0, after=200), _report(1), None),
        ("one", _report(3, after=200), _report(1), None),
        # Nothing to go by
        ("one", _report(2, after=200), None, None),
        ("one", _report(2, after=200), _report(1, tonie_id="other"), None),
        ("one", _report(2, after=200), _report(1, paused=True), None),
        ("one", _report(2, after=200), _report(1, duration=None), None),
        ("one", _report(2, after=200, paused=True), _report(1), None),
        ("one", Playback(tonie_id=None), _report(1), None),
    ],
)
def test_decide(mode: Any, playback: Playback, last: Playback | None, expected: int | None) -> None:
    """Only the end of the figure, and with "one" a chapter that ran out, send the box back."""
    assert decide(mode, playback, last) == expected


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    answer: dict[str, Any] = await client.receive_json()
    return answer


def _repeat(mode: str | None, box: str = BOX_ID) -> dict[str, Any]:
    return {"type": f"{DOMAIN}/box/repeat", "box_id": box, "mode": mode}


async def test_one_chapter_repeats(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A chapter that runs out plays again; a skip by hand goes through."""
    client = await hass_ws_client(hass)
    channel = push.last
    channel.connect()
    channel.playback(chapter=0, position=0.0)
    answer = await _call(client, _repeat("one"))
    assert answer["result"]["repeat"] == "one"
    player = entity_id(hass, "media_player", BOX_ID)
    assert hass.states.get(player).attributes["repeat"] == "one"

    freezer.tick(timedelta(seconds=60))
    channel.playback(chapter=1, position=0.0)
    await hass.async_block_till_done()
    assert channel.commands == []

    freezer.tick(timedelta(seconds=200))
    channel.playback(chapter=2, position=0.0)
    await hass.async_block_till_done()
    assert [c[1:] for c in channel.commands] == [JUMP(1), PLAY]
    # The box follows; the same report again changes nothing
    channel.playback(chapter=1, position=0.0)
    channel.playback(chapter=1, position=0.0)
    await hass.async_block_till_done()
    assert len(channel.commands) == 2

    # The figure taken off ends the repeat
    channel.removed()
    await hass.async_block_till_done()
    assert hass.states.get(player).attributes.get("repeat") in (None, "off")
    await client.send_json_auto_id({"type": f"{DOMAIN}/overview"})
    boxes = (await client.receive_json())["result"]["boxes"]
    assert next(b for b in boxes if b["id"] == BOX_ID)["repeat"] is None


async def test_the_figure_repeats(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """After its end the figure starts again, by the media player's action as by the page."""
    channel = push.last
    channel.connect()
    channel.playback(chapter=1)
    player = entity_id(hass, "media_player", BOX_ID)
    await hass.services.async_call(
        "media_player", "repeat_set", {"entity_id": player, "repeat": "all"}, blocking=True
    )
    assert hass.states.get(player).attributes["repeat"] == "all"
    channel.playback(chapter=1, ended=True)
    channel.playback(chapter=1, ended=True)
    await hass.async_block_till_done()
    assert [c[1:] for c in channel.commands] == [JUMP(0), PLAY]

    await hass.services.async_call(
        "media_player", "repeat_set", {"entity_id": player, "repeat": "off"}, blocking=True
    )
    channel.playback(chapter=0)
    channel.playback(chapter=1, ended=True)
    await hass.async_block_till_done()
    assert len(channel.commands) == 2


async def test_all_starts_at_the_first_favourite(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """With favourite chapters the figure repeats from the first of them instead of pausing."""
    client = await hass_ws_client(hass)
    await setup_entry.runtime_data.favourites.async_set(TONIE_ID, [0], True)
    channel = push.last
    channel.connect()
    channel.playback(chapter=0)
    assert (await _call(client, _repeat("all")))["success"]
    # The chapter after the last favourite would pause the box
    channel.playback(chapter=1, position=0.0)
    await hass.async_block_till_done()
    assert [c[1:] for c in channel.commands] == [JUMP(0), PLAY]
    # The box plays on: the favourites keep steering, nothing counts as a pause by hand
    channel.playback(chapter=0, position=0.0)
    channel.playback(chapter=1, position=0.0)
    await hass.async_block_till_done()
    assert [c[1:] for c in channel.commands][2:] == [JUMP(0), PLAY]


@pytest.mark.parametrize(
    ("message", "code"),
    [
        (_repeat("all", "nobox"), "unknown_box"),
        (_repeat("all", CLASSIC_BOX_ID), "not_supported"),
        (_repeat("one"), "nothing_plays"),
        (_repeat("twice"), "invalid_format"),
    ],
)
async def test_refused(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    message: dict[str, Any],
    code: str,
) -> None:
    """Only a Toniebox 2 with a figure on it repeats."""
    client = await hass_ws_client(hass)
    push.last.connect()
    push.last.removed()
    answer = await _call(client, message)
    assert answer["error"]["code"] == code
    assert (await _call(client, _repeat(None)))["success"]


async def test_the_player_says_why_not(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """Without a figure the media player's action is refused in words."""
    from homeassistant.exceptions import ServiceValidationError

    push.last.connect()
    push.last.removed()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "media_player",
            "repeat_set",
            {"entity_id": entity_id(hass, "media_player", BOX_ID), "repeat": "one"},
            blocking=True,
        )


def _stored(hass_storage: dict[str, Any], entry: MockConfigEntry, repeat: dict[str, Any]) -> None:
    key = f"{DOMAIN}.{entry.entry_id}.settings"
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": {"repeat": repeat}}


async def test_the_repeat_goes_on_after_a_restart(
    hass: HomeAssistant,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """The repeat is kept with its figure; an end not seen happening is not caught up."""
    client = await hass_ws_client(hass)
    push.last.connect()
    push.last.playback(chapter=1, position=0.0)
    assert (await _call(client, _repeat("one")))["success"]
    assert await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    stored = hass_storage[f"{DOMAIN}.{setup_entry.entry_id}.settings"]["data"]["repeat"]
    assert stored == {BOX_ID: {"mode": "one", "tonie": TONIE_ID}}

    player = entity_id(hass, "media_player", BOX_ID)
    assert hass.states.get(player).attributes["repeat"] == "one"
    channel = push.last
    channel.connect()
    # The figure had ended while Home Assistant was away: the box stays silent
    channel.playback(chapter=1, ended=True)
    await hass.async_block_till_done()
    assert channel.commands == []
    # Played on by hand, the chapter repeats as before
    channel.playback(chapter=1, position=0.0)
    freezer.tick(timedelta(seconds=200))
    channel.playback(chapter=2, position=0.0)
    await hass.async_block_till_done()
    assert [c[1:] for c in channel.commands] == [JUMP(1), PLAY]

    # Another figure ends it, and the store forgets it
    channel.playback(tonie_id="other", chapter=0)
    await hass.async_block_till_done()
    assert hass.states.get(player).attributes.get("repeat") in (None, "off")
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert hass_storage[f"{DOMAIN}.{setup_entry.entry_id}.settings"]["data"]["repeat"] == {}


async def test_a_kept_repeat_that_no_longer_fits_is_dropped(
    hass: HomeAssistant,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Kept for another figure, a box that left or in another shape, the repeat is gone."""
    _stored(
        hass_storage,
        config_entry,
        {
            BOX_ID: {"mode": "all", "tonie": "replaced"},
            "gone": {"mode": "one", "tonie": TONIE_ID},
            CLASSIC_BOX_ID: {"mode": "twice", "tonie": TONIE_ID},
            "odd": 3,
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.runtime_data.preferences.repeat == {}
    player = entity_id(hass, "media_player", BOX_ID)
    assert hass.states.get(player).attributes.get("repeat") in (None, "off")
