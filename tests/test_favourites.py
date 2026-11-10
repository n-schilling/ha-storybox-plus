"""Favourite chapters: the lists, their store, and how the box is steered by them."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.favourites import FavouriteChapters, Favourites, decide

from .conftest import BOX_ID, CREATIVE_ID, DISC_ID, MAC, TONIE_ID, FakeCloud, PushChannels

FAV = Favourites(active=True, chapters=(1, 3, 4))


@pytest.mark.parametrize(
    ("favourites", "chapter", "previous", "expected"),
    [
        # Favourites off, or none: nothing happens
        (Favourites(False, (1, 3)), 0, None, None),
        (Favourites(True, ()), 0, None, None),
        # A favourite plays: nothing happens
        (FAV, 1, None, None),
        (FAV, 3, 1, None),
        # Forwards: the next favourite, from the start and between favourites
        (FAV, 0, None, ("jump", 1)),
        (FAV, 2, 1, ("jump", 3)),
        # After the last favourite the box pauses
        (FAV, 5, 4, ("pause", None)),
        (FAV, 7, None, ("pause", None)),
        # Backwards: the previous favourite, or the first when none lies before
        (FAV, 2, 3, ("jump", 1)),
        (FAV, 0, 1, ("jump", 1)),
        # Backwards onto a favourite is fine
        (FAV, 3, 4, None),
    ],
)
def test_decide(favourites: Favourites, chapter: int, previous: int | None, expected: Any) -> None:
    """What the steering sends for a chapter, given the one before it."""
    assert decide(favourites, chapter, previous) == expected


async def test_store_round_trip(hass: HomeAssistant) -> None:
    """Lists are kept sorted and without doubles; an empty list forgets the figure."""
    store: Store[dict[str, Any]] = Store(hass, 1, "storybox_plus.test.favourites")
    chapters = FavouriteChapters(store)
    await chapters.async_load()
    assert chapters.get("t1") is None
    assert await chapters.async_set("t1", [4, 1, 4, 3], True) == Favourites(True, (1, 3, 4))
    assert await chapters.async_set("t2", [0], False) == Favourites(False, (0,))
    assert await chapters.async_set("t1", [], True) is None
    again = FavouriteChapters(Store(hass, 1, "storybox_plus.test.favourites"))
    await again.async_load()
    assert again.get("t1") is None
    assert again.get("t2") == Favourites(False, (0,))


async def test_store_leaves_out_what_does_not_fit(hass: HomeAssistant) -> None:
    """Odd entries in the store are dropped instead of breaking the load."""
    store: Store[dict[str, Any]] = Store(hass, 1, "storybox_plus.test.favourites")
    await store.async_save(
        {
            "tonies": {
                "ok": {"active": True, "chapters": [2, "x", -1, True, 0]},
                "empty": {"active": True, "chapters": []},
                "odd": {"active": True, "chapters": "no"},
                "worse": "no",
            }
        }
    )
    chapters = FavouriteChapters(store)
    await chapters.async_load()
    assert chapters.get("ok") == Favourites(True, (0, 2))
    assert chapters.get("empty") is None
    assert chapters.get("odd") is None
    chapters_no_store = FavouriteChapters(Store(hass, 1, "storybox_plus.other.favourites"))
    await chapters_no_store.async_load()
    assert chapters_no_store.get("ok") is None


async def _ask(client: Any, msg: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(msg)
    return await client.receive_json()


async def test_set_favourites(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The page sets the favourites of a bought figure and reads them with the library."""
    client = await hass_ws_client(hass)
    result = await _ask(
        client,
        {
            "type": f"{DOMAIN}/favourites/set",
            "tonie_id": TONIE_ID,
            "chapters": [1, 0],
            "active": True,
        },
    )
    assert result["success"], result
    assert result["result"] == {"favourites": {"active": True, "chapters": [0, 1]}}
    library = await _ask(client, {"type": f"{DOMAIN}/library"})
    by_id = {t["id"]: t for t in library["result"]["tonies"]}
    assert by_id[TONIE_ID]["favourites"] == {"active": True, "chapters": [0, 1]}
    assert by_id[CREATIVE_ID]["favourites"] is None
    # Switched off, the list stays; emptied, the figure is forgotten
    off = await _ask(
        client,
        {
            "type": f"{DOMAIN}/favourites/set",
            "tonie_id": TONIE_ID,
            "chapters": [1],
            "active": False,
        },
    )
    assert off["result"] == {"favourites": {"active": False, "chapters": [1]}}
    gone = await _ask(
        client,
        {"type": f"{DOMAIN}/favourites/set", "tonie_id": TONIE_ID, "chapters": [], "active": True},
    )
    assert gone["result"] == {"favourites": None}
    # A disc takes favourites too; its chapters are known, so a chapter beyond them is refused
    disc = await _ask(
        client,
        {"type": f"{DOMAIN}/favourites/set", "tonie_id": DISC_ID, "chapters": [0], "active": True},
    )
    assert disc["success"], disc


@pytest.mark.parametrize(
    ("msg", "code"),
    [
        ({"tonie_id": "nope", "chapters": [0], "active": True}, "unknown_figure"),
        ({"tonie_id": CREATIVE_ID, "chapters": [0], "active": True}, "not_bought"),
        ({"tonie_id": TONIE_ID, "chapters": [0, 9], "active": True}, "unknown_chapter"),
        ({"tonie_id": TONIE_ID, "chapters": [-1], "active": True}, "invalid_format"),
    ],
)
async def test_set_favourites_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    msg: dict[str, Any],
    code: str,
) -> None:
    """Unknown figures, creative figures and chapters the figure does not have are refused."""
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/favourites/set", **msg})
    assert not result["success"]
    assert result["error"]["code"] == code


async def test_set_favourites_needs_an_admin(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """Favourites are set on the page, which is for administrators."""
    client = await hass_ws_client(hass, access_token=hass_read_only_access_token)
    result = await _ask(
        client,
        {"type": f"{DOMAIN}/favourites/set", "tonie_id": TONIE_ID, "chapters": [0], "active": True},
    )
    assert not result["success"]
    assert result["error"]["code"] == "unauthorized"


async def _settle(hass: HomeAssistant) -> None:
    """Let the steering task run; the push channel's endless loop is a background task too."""
    for _ in range(5):
        await asyncio.sleep(0)
    await hass.async_block_till_done()


def _jump(chapter: int) -> tuple[str, str, dict[str, Any]]:
    return (MAC, "playback", {"action": "setPosition", "chapter": chapter, "ms": 0})


PAUSE = (MAC, "playback", {"action": "pause"})


async def test_box_is_steered_to_the_favourites(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """The box leaves every chapter that is no favourite, forwards, backwards, and pauses after the last."""
    favourites = setup_entry.runtime_data.favourites
    await favourites.async_set(TONIE_ID, [1, 3], True)
    channel = push.last
    channel.connect()
    channel.playback(chapter=0)
    await _settle(hass)
    assert channel.commands == [_jump(1)]
    # The box still reports the skipped chapter while the command travels: nothing more is sent
    channel.playback(chapter=0, position=51.0)
    await _settle(hass)
    assert channel.commands == [_jump(1)]
    # The favourite plays, then the chapter after it: forwards to the next favourite
    channel.playback(chapter=1)
    channel.playback(chapter=2)
    await _settle(hass)
    assert channel.commands == [_jump(1), _jump(3)]
    # A jump back at the box from the favourite: the previous favourite
    channel.playback(chapter=3)
    channel.playback(chapter=2)
    await _settle(hass)
    assert channel.commands == [_jump(1), _jump(3), _jump(1)]
    # After the last favourite the box pauses; a hand pressing play lets it go on
    channel.playback(chapter=3)
    channel.playback(chapter=4)
    await _settle(hass)
    assert channel.commands[-1] == PAUSE
    channel.playback(chapter=4, paused=True)
    channel.playback(chapter=4, paused=False)
    await _settle(hass)
    assert channel.commands[-1] == PAUSE
    assert len(channel.commands) == 4


async def test_box_is_left_alone(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
) -> None:
    """Switched-off lists, other figures, paused and empty reports send nothing."""
    favourites = setup_entry.runtime_data.favourites
    await favourites.async_set(TONIE_ID, [1], False)
    channel = push.last
    channel.connect()
    channel.playback(chapter=0)
    channel.playback(chapter=0, tonie_id=DISC_ID)
    channel.playback(chapter=0, paused=True)
    channel.playback(tonie_id=None, chapter=None)
    await _settle(hass)
    assert channel.commands == []
    await favourites.async_set(TONIE_ID, [1], True)
    # A figure placed again starts the steering afresh
    channel.playback(chapter=0)
    await _settle(hass)
    assert channel.commands == [_jump(0 + 1)]


async def test_steering_survives_a_refused_command(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A command the channel cannot send is logged, not raised."""
    from custom_components.storybox_plus.cloud import CloudConnectionError

    await setup_entry.runtime_data.favourites.async_set(TONIE_ID, [1], True)
    channel = push.last
    channel.connect()
    channel.command_error = CloudConnectionError("gone")
    channel.playback(chapter=0)
    await _settle(hass)
    assert "not steered" in caplog.text
    assert BOX_ID
