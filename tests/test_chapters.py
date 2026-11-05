"""The chapters of bought figures: learned from the box they stand on, kept in a store."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.components.media_player import DOMAIN as MP_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.coordinator import DETAILS_PER_POLL

from .conftest import (
    BOX_ID,
    CONTENT_VERSION,
    CREATIVE_ID,
    HOUSEHOLD_ID,
    PLAYBACK_INFO_IMAGE,
    PLAYBACK_INFO_SERIES,
    TONIE_ID,
    TONIE_NAME,
    TONIE_SERIES,
    FakeCloud,
    PushChannels,
    content_tonie,
    entity_id,
    playback_info,
    tb2_box,
)

# The store writes a little after the chapters were learned
SAVE_DELAY = timedelta(seconds=10)
BOX_CHAPTERS = ["Box-Kapitel 1", "Box-Kapitel 2", "Box-Kapitel 3"]


def _chapters_key(entry: MockConfigEntry) -> str:
    return f"{DOMAIN}.{entry.entry_id}.chapters"


def _bought_without_chapters(cloud: FakeCloud, known: bool = True) -> None:
    """Let the cloud refuse the app's library queries: the bought figure comes without chapters.

    Only the box it stands on can tell them then (playback info), if the cloud knows them.
    """
    cloud.main.library_query_refused = True
    cloud.main.detail_query_refused = True
    if known:
        cloud.main.playback_info[(BOX_ID, TONIE_ID)] = playback_info()


def _media_title(hass: HomeAssistant) -> str | None:
    state = hass.states.get(entity_id(hass, MP_DOMAIN, BOX_ID))
    assert state is not None
    return state.attributes.get("media_title")


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _save(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Let the delayed write of the store happen."""
    freezer.tick(SAVE_DELAY + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _background_done(hass: HomeAssistant, push: PushChannels) -> None:
    """Wait for the fetch started by a placement; the push channel's endless loop is ended first."""
    push.last.end()
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_chapters_are_learned_from_the_box_at_setup(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A bought figure without chapters on a box is asked about once; the figure gets them."""
    _bought_without_chapters(cloud)
    await _setup(hass, config_entry)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    # Without a playback message the content version of the box is unknown
    assert cloud.playback_info_versions == [0]
    # What the box told spares the app's detail query
    assert cloud.detail_calls == []
    coordinator = config_entry.runtime_data.coordinator
    tonie = coordinator.data.tonies[TONIE_ID]
    assert [c.title for c in tonie.chapters] == BOX_CHAPTERS
    assert tonie.seconds == 480
    # What the library knows stays: name, series and picture
    assert tonie.name == TONIE_NAME
    assert tonie.series == TONIE_SERIES
    assert tonie.image_url == f"https://img.example.com/{TONIE_ID}.png"
    # The media player names the chapter that plays
    push.last.playback(chapter=1)
    assert _media_title(hass) == "Box-Kapitel 2"
    # The page lists the chapters
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/library"})
    result = await client.receive_json()
    listed = next(t for t in result["result"]["tonies"] if t["id"] == TONIE_ID)
    assert [c["id"] for c in listed["chapters"]] == ["0", "1", "2"]
    # The next poll asks nothing new and keeps the chapters
    await coordinator.async_refresh()
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert [c.title for c in coordinator.data.tonies[TONIE_ID].chapters] == BOX_CHAPTERS


async def test_box_fills_only_what_the_library_lacks(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Series and picture come from the box only when the library has none."""
    _bought_without_chapters(cloud)
    cloud.main.content_tonies[0].update({"series": None, "imageUrl": None})
    await _setup(hass, config_entry)
    tonie = config_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    assert tonie.name == TONIE_NAME
    assert tonie.series == PLAYBACK_INFO_SERIES
    assert tonie.image_url == PLAYBACK_INFO_IMAGE
    push.last.playback(chapter=0)
    attributes = hass.states.get(entity_id(hass, MP_DOMAIN, BOX_ID)).attributes
    assert attributes["media_title"] == "Box-Kapitel 1"
    assert attributes["media_artist"] == PLAYBACK_INFO_SERIES
    assert attributes["entity_picture"].startswith("/api/media_player_proxy/")


async def test_figures_with_chapters_are_not_asked(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The library's chapter names serve the player and the page; only their lengths are asked from the box."""
    assert cloud.graphql_calls[0] == ("households", None)
    # The box with the figure is asked once for the lengths already at setup;
    # it knows none here (404), so the library's names stay
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert cloud.detail_calls == []
    push.last.playback(chapter=1)
    await _background_done(hass, push)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    attributes = hass.states.get(entity_id(hass, MP_DOMAIN, BOX_ID)).attributes
    assert attributes["media_title"] == "Kapitel 2"
    assert attributes["media_track"] == 2
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/library"})
    result = await client.receive_json()
    listed = next(t for t in result["result"]["tonies"] if t["id"] == TONIE_ID)
    assert listed["chapters"] == [
        {"id": "0", "title": "Kapitel 1", "seconds": None, "transcoding": False},
        {"id": "1", "title": "Kapitel 2", "seconds": None, "transcoding": False},
    ]
    assert listed["seconds"] == 500
    # Not again for that figure, nor for creative figures (timed already) or unknown ones
    push.last.playback(tonie_id=CREATIVE_ID)
    push.last.playback(tonie_id="unknown-figure")
    push.last.removed()
    push.last.playback(tonie_id=TONIE_ID)
    await _background_done(hass, push)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert cloud.detail_calls == []
    await _save(hass, freezer)
    assert _chapters_key(setup_entry) not in hass_storage


async def test_learned_chapters_survive_a_restart(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """The chapters are written a little later and read back at the next setup, without asking."""
    _bought_without_chapters(cloud)
    await _setup(hass, config_entry)
    key = _chapters_key(config_entry)
    assert key not in hass_storage
    await _save(hass, freezer)
    assert hass_storage[key]["data"] == {
        "tonies": {
            TONIE_ID: {
                "title": TONIE_NAME,
                "series": PLAYBACK_INFO_SERIES,
                "image_url": PLAYBACK_INFO_IMAGE,
                "chapters": [
                    {"id": "0", "title": "Box-Kapitel 1", "seconds": 180, "transcoding": False},
                    {"id": "1", "title": "Box-Kapitel 2", "seconds": 240, "transcoding": False},
                    {"id": "2", "title": "Box-Kapitel 3", "seconds": 60, "transcoding": False},
                ],
            }
        }
    }
    # A restart: the entry is set up again and knows the chapters from the store
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    tonie = config_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    assert [c.title for c in tonie.chapters] == BOX_CHAPTERS
    assert tonie.series == TONIE_SERIES
    push.last.playback(chapter=2)
    assert _media_title(hass) == "Box-Kapitel 3"


async def test_stored_chapters_are_read_and_junk_is_skipped(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Stored chapters win over the library's names, as far as they make sense; junk is skipped."""
    key = _chapters_key(config_entry)
    hass_storage[key] = {
        "version": 1,
        "minor_version": 1,
        "key": key,
        "data": {
            "tonies": {
                TONIE_ID: {
                    "title": 5,
                    "series": ["x"],
                    "image_url": "https://img.example.com/stored.png",
                    "chapters": [
                        {"id": "s1", "title": "Stored 1", "seconds": 90, "transcoding": False},
                        "junk",
                        {"title": "no id"},
                        {"id": "", "title": "empty id"},
                        {"id": 2, "seconds": "90", "transcoding": 1},
                    ],
                },
                "t-none": {"chapters": None},
                "t-number": {"chapters": 7},
                "t-dict": {"chapters": {"id": "x"}},
                "t-string": "junk",
                "t-bare": {},
            }
        },
    }
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert cloud.playback_info_calls == []
    tonie = config_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    assert [(c.id, c.title, c.seconds, c.transcoding) for c in tonie.chapters] == [
        ("s1", "Stored 1", 90, False),
        ("2", "", None, True),
    ]
    # The library's own series, picture and total length win over the stored ones
    assert tonie.series == TONIE_SERIES
    assert tonie.image_url == f"https://img.example.com/{TONIE_ID}.png"
    assert tonie.seconds == 500


async def test_learned_lengths_win_when_the_library_returns(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """Chapters learned from a box keep their lengths once the library lists names again."""
    _bought_without_chapters(cloud)
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.data.tonies[TONIE_ID].seconds == 480
    cloud.main.library_query_refused = False
    await coordinator.async_refresh()
    tonie = coordinator.data.tonies[TONIE_ID]
    assert [(c.title, c.seconds) for c in tonie.chapters] == [
        ("Box-Kapitel 1", 180.0),
        ("Box-Kapitel 2", 240.0),
        ("Box-Kapitel 3", 60.0),
    ]
    # The total length is the library's
    assert tonie.seconds == 500
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert cloud.detail_calls == []


@pytest.mark.parametrize("data", [{"tonies": "junk"}, {"tonies": None}, {}, []])
async def test_damaged_store_is_ignored(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    data: Any,
) -> None:
    """A store without usable figures changes nothing; the box is asked as usual."""
    _bought_without_chapters(cloud)
    key = _chapters_key(config_entry)
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": data}
    await _setup(hass, config_entry)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    tonie = config_entry.runtime_data.coordinator.data.tonies[TONIE_ID]
    assert [c.title for c in tonie.chapters] == BOX_CHAPTERS


@pytest.mark.parametrize(
    "answer",
    [None, playback_info(chapters=[]), playback_info(chapters=[], status="unavailable")],
    ids=["404", "no chapters", "unavailable"],
)
async def test_unknown_figure_is_asked_once_per_run(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    answer: dict[str, Any] | None,
) -> None:
    """A figure the cloud has no chapters for is asked once per run, and again after a restart."""
    cloud.main.boxes[HOUSEHOLD_ID] = [tb2_box(placed=None)]
    _bought_without_chapters(cloud, known=False)
    if answer is not None:
        cloud.main.playback_info[(BOX_ID, TONIE_ID)] = answer
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert cloud.playback_info_calls == []

    # Placed: asked once, nothing learned
    push.last.playback(tonie_id=TONIE_ID, chapter=0)
    await _background_done(hass, push)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert coordinator.data.tonies[TONIE_ID].chapters == ()
    assert _media_title(hass) == TONIE_NAME
    # Placed again, and seen on the box by a poll: not asked again
    push.last.removed()
    push.last.playback(tonie_id=TONIE_ID, chapter=0)
    await hass.async_block_till_done(wait_background_tasks=True)
    cloud.main.box(BOX_ID)["placement"] = {"tonie": {"id": TONIE_ID}}
    await coordinator.async_refresh()
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert _chapters_key(config_entry) not in hass_storage

    # A restart asks once more
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)] * 2


async def test_cloud_error_during_fetch_is_tolerated(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A failing playback-info call does not spoil the poll; the figure is asked again next time."""
    _bought_without_chapters(cloud)
    cloud.main.playback_info_status = 500
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.last_update_success
    assert coordinator.data.tonies[TONIE_ID].chapters == ()
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)] * 2
    # Once the cloud answers, the chapters are there
    cloud.main.playback_info_status = None
    await coordinator.async_refresh()
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)] * 3
    assert [c.title for c in coordinator.data.tonies[TONIE_ID].chapters] == BOX_CHAPTERS


async def test_outdated_content_is_asked_again(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A box whose content is outdated gets no chapters yet; it is asked again, with its version."""
    caplog.set_level(logging.DEBUG, logger="custom_components.storybox_plus.coordinator")
    _bought_without_chapters(cloud, known=False)
    cloud.main.playback_info[(BOX_ID, TONIE_ID)] = playback_info(chapters=[], status="outdated")
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert cloud.playback_info_versions == [0]
    assert "No chapters for a figure (status outdated, content version 0)" in caplog.text
    assert coordinator.data.tonies[TONIE_ID].chapters == ()
    # The box reports its content version; placing the figure again asks with it
    push.last.removed()
    push.last.playback(tonie_id=TONIE_ID, chapter=0, content_version=CONTENT_VERSION)
    await _background_done(hass, push)
    assert cloud.playback_info_versions == [0, CONTENT_VERSION]
    # So does the next poll, as long as the answer stays outdated
    await coordinator.async_refresh()
    assert cloud.playback_info_versions == [0, CONTENT_VERSION, CONTENT_VERSION]
    # Once the cloud has the chapters they are learned and the figure is left alone
    cloud.main.playback_info[(BOX_ID, TONIE_ID)] = playback_info()
    await coordinator.async_refresh()
    assert len(cloud.playback_info_calls) == 4
    assert [c.title for c in coordinator.data.tonies[TONIE_ID].chapters] == BOX_CHAPTERS
    assert _media_title(hass) == "Box-Kapitel 1"
    await coordinator.async_refresh()
    assert len(cloud.playback_info_calls) == 4


async def test_placing_a_figure_fetches_its_chapters(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A chapter-less figure placed on the box is asked about in the background; the entities follow."""
    cloud.main.boxes[HOUSEHOLD_ID] = [tb2_box(placed=None)]
    _bought_without_chapters(cloud)
    gate = cloud.main.playback_info_gate = asyncio.Event()
    await _setup(hass, config_entry)
    assert cloud.playback_info_calls == []

    push.last.playback(tonie_id=TONIE_ID, chapter=2, content_version=CONTENT_VERSION)
    # Asked at once, with the content version the box reported; until the cloud
    # answers the figure's name stands in for the chapter
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert cloud.playback_info_versions == [CONTENT_VERSION]
    assert _media_title(hass) == TONIE_NAME
    gate.set()
    await _background_done(hass, push)
    assert _media_title(hass) == "Box-Kapitel 3"
    coordinator = config_entry.runtime_data.coordinator
    assert [c.title for c in coordinator.data.tonies[TONIE_ID].chapters] == BOX_CHAPTERS
    # Taking it off and placing it again asks nothing new
    push.last.removed()
    push.last.playback(tonie_id=TONIE_ID, chapter=0)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert _media_title(hass) == "Box-Kapitel 1"


async def test_figure_gone_before_the_box_answered(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A figure that left the library while the box was asked keeps its chapters for its return."""
    cloud.main.boxes[HOUSEHOLD_ID] = [tb2_box(placed=None)]
    _bought_without_chapters(cloud)
    gate = cloud.main.playback_info_gate = asyncio.Event()
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator

    push.last.playback(tonie_id=TONIE_ID)
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    node = cloud.main.content_tonies.pop()
    await coordinator.async_refresh()
    assert TONIE_ID not in coordinator.data.tonies
    gate.set()
    await _background_done(hass, push)
    assert TONIE_ID not in coordinator.data.tonies

    cloud.main.content_tonies.append(node)
    await coordinator.async_refresh()
    assert cloud.playback_info_calls == [(BOX_ID, TONIE_ID)]
    assert [c.title for c in coordinator.data.tonies[TONIE_ID].chapters] == BOX_CHAPTERS


async def test_details_are_asked_in_batches_when_the_library_has_no_chapters(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """With the older library a few figures per poll are asked for their chapters and kept."""
    cloud.main.library_query_refused = True
    cloud.main.boxes[HOUSEHOLD_ID] = [tb2_box(placed=None)]
    count = DETAILS_PER_POLL + 2
    cloud.main.content_tonies = [content_tonie(f"t{i}", f"Figur {i}") for i in range(1, count + 1)]
    # The cloud has no chapters for t3 and does not find t4: both are left alone afterwards
    cloud.main.content_tonie_details["t3"] = content_tonie("t3", chapters=[])
    cloud.main.content_tonie_details["t4"] = None
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert cloud.detail_calls == [(HOUSEHOLD_ID, f"t{i}") for i in range(1, DETAILS_PER_POLL + 1)]
    assert cloud.playback_info_calls == []
    tonies = coordinator.data.tonies
    assert [(c.id, c.title) for c in tonies["t1"].chapters] == [
        ("0", "Kapitel 1"),
        ("1", "Kapitel 2"),
    ]
    assert [c.title for c in tonies["t5"].chapters] == ["Kapitel 1", "Kapitel 2"]
    assert tonies["t3"].chapters == ()
    assert tonies["t4"].chapters == ()
    assert tonies["t6"].chapters == ()
    # The store holds the learned ones only
    await _save(hass, freezer)
    stored = hass_storage[_chapters_key(config_entry)]["data"]["tonies"]
    assert sorted(stored) == ["t1", "t2", "t5"]
    assert stored["t1"] == {
        "title": "Figur 1",
        "series": TONIE_SERIES,
        "image_url": "https://img.example.com/t1.png",
        "chapters": [
            {"id": "0", "title": "Kapitel 1", "seconds": None, "transcoding": False},
            {"id": "1", "title": "Kapitel 2", "seconds": None, "transcoding": False},
        ],
    }
    # The next poll asks the rest, the one after that nothing
    await coordinator.async_refresh()
    assert cloud.detail_calls[DETAILS_PER_POLL:] == [(HOUSEHOLD_ID, "t6"), (HOUSEHOLD_ID, "t7")]
    assert [c.title for c in coordinator.data.tonies["t7"].chapters] == ["Kapitel 1", "Kapitel 2"]
    await coordinator.async_refresh()
    assert len(cloud.detail_calls) == count


async def test_detail_error_stops_the_batch_but_not_the_poll(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """A refused detail query ends the batch; the poll succeeds and the next one tries again."""
    cloud.main.library_query_refused = True
    cloud.main.detail_query_refused = True
    cloud.main.boxes[HOUSEHOLD_ID] = [tb2_box(placed=None)]
    cloud.main.content_tonies = [content_tonie("t1"), content_tonie("t2")]
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data.coordinator
    assert config_entry.state is ConfigEntryState.LOADED
    assert coordinator.last_update_success
    assert cloud.detail_calls == [(HOUSEHOLD_ID, "t1")]
    assert coordinator.data.tonies["t1"].chapters == ()
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert cloud.detail_calls == [(HOUSEHOLD_ID, "t1")] * 2
    # Once the cloud answers, the batch runs through
    cloud.main.detail_query_refused = False
    await coordinator.async_refresh()
    assert cloud.detail_calls[2:] == [(HOUSEHOLD_ID, "t1"), (HOUSEHOLD_ID, "t2")]
    assert [c.title for c in coordinator.data.tonies["t2"].chapters] == ["Kapitel 1", "Kapitel 2"]


async def test_remove_entry_deletes_chapters(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Removing the account forgets the chapters learned for it."""
    _bought_without_chapters(cloud)
    await _setup(hass, config_entry)
    await _save(hass, freezer)
    key = _chapters_key(config_entry)
    assert key in hass_storage
    await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage
