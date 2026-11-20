"""The integration's own log, and the checks that a change really reached the cloud."""

from __future__ import annotations

from datetime import timedelta
import json
import logging
from pathlib import Path
from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import ClientSessionGenerator, WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.storybox_plus import coordinator as coordinator_module, fetcher
from custom_components.storybox_plus.cloud.rest import short_ids
from custom_components.storybox_plus.const import DOMAIN
from custom_components.storybox_plus.log import DATA_LOG, LOGGER_NAME, async_get_log

from .conftest import (
    CREATIVE_ID,
    HOUSEHOLD_ID,
    VIDEO_URL,
    FakeCloud,
    FakeFetcher,
    PushChannels,
    tune,
)


async def _ask(client: Any, msg: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(msg)
    return await client.receive_json()


async def _upload(hass_client: ClientSessionGenerator) -> str:
    import aiohttp

    http = await hass_client()
    data = aiohttp.FormData(quote_fields=False)
    data.add_field("file", b"audio", filename="Lied.mp3", content_type="audio/mpeg")
    response = await http.post("/api/file_upload", data=data)
    assert response.status == 200
    return str((await response.json())["file_id"])


@pytest.fixture(autouse=True)
def no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Tunes are read again at once in tests."""
    monkeypatch.setattr(coordinator_module, "TUNE_CONFIRM_PAUSE", 0)


def test_short_ids() -> None:
    """UUIDs and long hex IDs keep their first six characters; short words stay."""
    household = "4f9b3c2e-0000-4000-8000-000000000002"
    text = f"PUT /households/{household}/tonie/0123456789ABCDEF/tune file-1 1000001"
    assert short_ids(text) == "PUT /households/4f9b3c…/tonie/012345…/tune file-1 1000001"


# ------------------------------------------------------------------ the log


async def test_log_level_is_kept_and_lines_are_shown(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """The page reads the latest lines and sets the level, which the store keeps."""
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/log"})
    assert result["success"], result
    log = result["result"]
    assert log["level"] == "debug"
    # The reads of the setup are there, newest first, with cut IDs and the module
    lines = log["lines"]
    assert any(
        line["source"] == "cloud.rest" and line["message"].startswith("GET /households")
        for line in lines
    )
    assert lines[0]["time"] >= lines[-1]["time"]

    result = await _ask(client, {"type": f"{DOMAIN}/log/set", "level": "warning"})
    assert result["success"], result
    assert result["result"]["level"] == "warning"
    assert result["result"]["lines"] == []
    assert logging.getLogger(LOGGER_NAME).level == logging.WARNING
    assert hass_storage[f"{DOMAIN}.log"]["data"] == {"level": "warning", "days": 7}
    limited = await _ask(client, {"type": f"{DOMAIN}/log", "limit": 1})
    assert len(limited["result"]["lines"]) == 1

    refused = await _ask(client, {"type": f"{DOMAIN}/log/set", "level": "loud"})
    assert not refused["success"]


async def test_log_level_comes_back_after_a_restart(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """A stored level applies before the account is set up; unloading stops keeping lines."""
    hass_storage[f"{DOMAIN}.log"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.log",
        "data": {"level": "error"},
    }
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert logging.getLogger(LOGGER_NAME).level == logging.ERROR
    log = await async_get_log(hass)
    assert log.level == "error"
    assert not any(line.level in ("debug", "info") for line in log.lines)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert DATA_LOG not in hass.data
    assert log._handler not in logging.getLogger(LOGGER_NAME).handlers
    # A junk store falls back to the default
    hass_storage[f"{DOMAIN}.log"]["data"] = {"level": "loud"}
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    assert (await async_get_log(hass)).level == "debug"


async def test_removing_the_last_account_forgets_the_level(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """The level belongs to the integration; it goes with its last account."""
    client = await hass_ws_client(hass)
    await _ask(client, {"type": f"{DOMAIN}/log/set", "level": "info"})
    assert f"{DOMAIN}.log" in hass_storage
    assert await hass.config_entries.async_remove(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.log" not in hass_storage


async def test_requests_are_logged_by_kind(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A read is a debug line, a change an info line, a refused change a warning."""
    cloud.main.tunes = [tune()]
    await setup_entry.runtime_data.coordinator.async_refresh()
    caplog.clear()
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": "my-tune-1"}
    )
    assert result["success"], result
    levels = {r.getMessage().split(" answered")[0]: r.levelno for r in caplog.records}
    put = short_ids(f"PUT /households/{HOUSEHOLD_ID}/tonie/{CREATIVE_ID}/tune/my-tune-1")
    assert levels[put] == logging.INFO
    assert levels["POST /graphql tunesItems"] == logging.DEBUG
    assert "Laying Tune 'Bakabu' on" in caplog.text
    assert "lies on" in caplog.text

    cloud.main.chapters_error = (422, {"errors": [{"code": "invalid_chapters"}]})
    caplog.clear()
    result = await _ask(
        client,
        {"type": f"{DOMAIN}/figure/update", "tonie_id": CREATIVE_ID, "name": "Neu"},
    )
    assert not result["success"]
    (warning,) = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert "answered 422 (invalid_chapters)" in warning.getMessage()


async def test_a_tune_laid_on_elsewhere_is_logged(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A Tune that comes or goes between two polls (the app, the web) is in the log."""
    cloud.main.tunes = [tune()]
    coordinator = setup_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    cloud.main.tunes = [tune(assigned=(CREATIVE_ID,))]
    await coordinator.async_refresh()
    assert "Tune 'Bakabu' lies on" in caplog.text
    cloud.main.tunes = [tune()]
    await coordinator.async_refresh()
    assert "Tune 'Bakabu' left" in caplog.text


# ------------------------------------------------------------------ Tunes


async def test_tune_taken_off_once_the_cloud_shows_it(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """The cloud carries out taking a Tune off a little later: the Tunes are read until it shows."""
    cloud.main.tunes = [tune(assigned=(CREATIVE_ID,))]
    await setup_entry.runtime_data.coordinator.async_refresh()
    cloud.main.tune_off_after_reads = 2
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": None}
    )
    assert result["success"], result
    assert result["result"]["tunes"][0]["assigned"] == []


async def test_tune_the_cloud_keeps_is_reported(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A Tune still on the figure after the reads is an error, not a success."""
    cloud.main.tunes = [tune(assigned=(CREATIVE_ID,))]
    await setup_entry.runtime_data.coordinator.async_refresh()
    cloud.main.tune_off_after_reads = None
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": None}
    )
    assert not result["success"]
    assert result["error"]["code"] == "tune_not_changed"
    assert "does not show it" in caplog.text
    assert setup_entry.runtime_data.coordinator.tune_on(CREATIVE_ID) is not None


async def test_tune_read_failing_is_reported(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Tunes that cannot be read again leave the change unconfirmed."""
    cloud.main.tunes = [tune()]
    await setup_entry.runtime_data.coordinator.async_refresh()
    cloud.main.tunes_status = 500
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/figure/tune", "tonie_id": CREATIVE_ID, "tune_id": "my-tune-1"}
    )
    assert not result["success"]
    assert result["error"]["code"] == "tune_not_changed"


# ------------------------------------------------------------------ chapters


async def test_no_chapter_while_a_tune_lies_on_the_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
) -> None:
    """The Tunes are read before the upload; one laid on in the app refuses it."""
    cloud.main.tunes = [tune(assigned=(CREATIVE_ID,))]
    file_id = await _upload(hass_client)
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add", "tonie_id": CREATIVE_ID, "file_id": file_id}
    )
    assert not result["success"]
    assert result["error"]["code"] == "tune_on"
    assert "Bakabu" in result["error"]["message"]
    assert cloud.upload_tickets == 0


async def test_a_chapter_the_cloud_drops_is_an_error(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The cloud answers without the new chapter: the page hears of it, the log says why."""
    cloud.main.chapters_dropped = True
    file_id = await _upload(hass_client)
    client = await hass_ws_client(hass)
    result = await _ask(
        client, {"type": f"{DOMAIN}/chapters/add", "tonie_id": CREATIVE_ID, "file_id": file_id}
    )
    assert not result["success"]
    assert result["error"]["code"] == "chapter_missing"
    assert "1 chapters before, 1 after" in caplog.text
    assert "Uploading Lied.mp3" in caplog.text


async def test_link_refused_while_a_tune_lies_on_the_figure(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    fetcher_app: FakeFetcher,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Nothing is fetched for a figure a Tune lies on; the end is in the log too."""
    monkeypatch.setattr(fetcher, "POLL", 0)
    cloud.main.tunes = [tune(assigned=(CREATIVE_ID,))]
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL}
    )
    assert (await client.receive_json())["success"]
    event = (await client.receive_json())["event"]
    assert event["stage"] == "error"
    assert event["code"] == "tune_on"
    assert fetcher_app.calls == []
    assert "Adding a chapter from a link failed" in caplog.text


async def test_link_success_is_logged(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    fetcher_app: FakeFetcher,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each step of a fetched link is in the log, up to the chapter on the figure."""
    monkeypatch.setattr(fetcher, "POLL", 0)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL}
    )
    assert (await client.receive_json())["success"]
    while (await client.receive_json())["event"]["stage"] not in ("done", "error"):
        pass
    for text in (
        "Fetching a link for",
        "The link is 'Me at the zoo'",
        "Media Fetcher job job-1 gave",
        "Chapter 'Me at the zoo' is on",
        "Adding a chapter from a link is done",
    ):
        assert text in caplog.text


# ------------------------------------------------------------------ the log on disk


async def test_lines_are_kept_on_disk_by_day(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    tmp_path: Path,
) -> None:
    """Lines go to a file per day; the page reads them back, also after the account reloads."""
    folder = tmp_path / "log"
    log = await async_get_log(hass)
    await log.async_flush()
    today = dt_util.now().date()
    (path,) = folder.iterdir()
    assert path.name == f"{today.isoformat()}.jsonl"
    written = [json.loads(text) for text in path.read_text().splitlines()]
    assert written and set(written[0]) == {"time", "level", "source", "message"}
    # Another day's file and junk next to it: read, newest day first, junk skipped
    yesterday = today - timedelta(days=1)
    old = {
        "time": "2000-01-01T00:00:00.000+00:00",
        "level": "info",
        "source": "x",
        "message": "old",
    }
    (folder / f"{yesterday.isoformat()}.jsonl").write_text(json.dumps(old) + "\n{broken\n")
    (folder / "notes.txt").write_text("not ours")
    (folder / "2026-13-45.jsonl").write_text("")
    assert await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    everything = (await _ask(client, {"type": f"{DOMAIN}/log"}))["result"]
    assert everything["days"] == 7
    assert everything["lines"][-1]["message"] == "old"
    assert len(everything["lines"]) > len(written)
    limited = (await _ask(client, {"type": f"{DOMAIN}/log", "limit": 2}))["result"]
    assert len(limited["lines"]) == 2


async def test_retention_deletes_old_days(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Days beyond the retention go at once; 0 days writes nothing and keeps lines in memory."""
    folder = tmp_path / "log"
    folder.mkdir(exist_ok=True)
    today = dt_util.now().date()
    for back in (1, 2, 5):
        (folder / f"{(today - timedelta(days=back)).isoformat()}.jsonl").write_text("")
    client = await hass_ws_client(hass)
    result = await _ask(client, {"type": f"{DOMAIN}/log/set", "days": 2})
    assert result["success"], result
    assert result["result"]["days"] == 2
    assert hass_storage[f"{DOMAIN}.log"]["data"] == {"level": "debug", "days": 2}
    names = {p.name for p in folder.iterdir()}
    kept = {f"{(today - timedelta(days=back)).isoformat()}.jsonl" for back in (0, 1)}
    assert f"{(today - timedelta(days=1)).isoformat()}.jsonl" in names
    assert names <= kept

    result = await _ask(client, {"type": f"{DOMAIN}/log/set", "days": 0})
    assert result["success"], result
    assert not folder.exists()
    lines = (await _ask(client, {"type": f"{DOMAIN}/log"}))["result"]["lines"]
    assert any("kept for 0 days" in line["message"] for line in lines)
    log = await async_get_log(hass)
    await log.async_flush()
    assert not folder.exists()
    for wrong in (-1, 91):
        refused = await _ask(client, {"type": f"{DOMAIN}/log/set", "days": wrong})
        assert not refused["success"]
    with pytest.raises(ValueError):
        await log.async_set(days=100)


async def test_stored_retention_and_files_go_with_the_last_account(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    tmp_path: Path,
) -> None:
    """A stored retention applies at the start; removing the last account deletes the files."""
    hass_storage[f"{DOMAIN}.log"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.log",
        "data": {"level": "info", "days": 30},
    }
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    log = await async_get_log(hass)
    assert (log.level, log.days) == ("info", 30)
    logging.getLogger(LOGGER_NAME).warning("Something to keep")
    await log.async_flush()
    assert (tmp_path / "log").is_dir()
    assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()
    assert not (tmp_path / "log").exists()
    assert f"{DOMAIN}.log" not in hass_storage


async def test_link_file_over_the_chosen_size_is_refused(
    hass: HomeAssistant,
    cloud: FakeCloud,
    push: PushChannels,
    fetcher_app: FakeFetcher,
    setup_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The largest file from the app follows the account's preference."""
    monkeypatch.setattr(fetcher, "POLL", 0)
    await setup_entry.runtime_data.preferences.async_set(fetch_max_mb=10)
    fetcher_app.file = b"x" * (10 * 1024 * 1024 + 1)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/chapters/add_link", "tonie_id": CREATIVE_ID, "url": VIDEO_URL}
    )
    assert (await client.receive_json())["success"]
    while (event := (await client.receive_json())["event"])["stage"] not in ("done", "error"):
        pass
    assert event["code"] == "too_large"
    assert "10 MB" in event["message"]
    assert not cloud.chapter_adds
