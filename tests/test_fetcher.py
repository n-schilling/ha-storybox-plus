"""The client of the Media Fetcher app: finding it, asking it, reading its answers."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiohasupervisor import SupervisorError
from aiohasupervisor.models import Discovery
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant

from custom_components.storybox_plus import fetcher

from .conftest import FETCHER_HOST, FETCHER_PORT, FETCHER_TOKEN, VIDEO_ID, VIDEO_URL, FakeFetcher

APP = fetcher.Fetcher(FETCHER_HOST, FETCHER_PORT, FETCHER_TOKEN)


async def test_find_without_a_supervisor(hass: HomeAssistant) -> None:
    """Without the Supervisor there is no app."""
    assert await fetcher.async_find(hass) is None


async def test_find(hass: HomeAssistant, fetcher_app: FakeFetcher) -> None:
    """The app is what it announced to the Supervisor."""
    assert await fetcher.async_find(hass) == APP
    assert APP.url == f"http://{FETCHER_HOST}:{FETCHER_PORT}/api/v1"
    fetcher_app.announced = False
    assert await fetcher.async_find(hass) is None


@pytest.mark.parametrize(
    "discoveries",
    [
        [],
        [
            Discovery(
                addon="x",
                service="other",
                uuid=MagicMock(),
                config={"host": "h", "port": 1, "token": "t"},
            )
        ],
        [
            Discovery(
                addon="x",
                service="media_fetcher",
                uuid=MagicMock(),
                config={"host": "", "port": 1, "token": "t"},
            )
        ],
        [
            Discovery(
                addon="x",
                service="media_fetcher",
                uuid=MagicMock(),
                config={"host": "h", "port": "1", "token": "t"},
            )
        ],
        [
            Discovery(
                addon="x",
                service="media_fetcher",
                uuid=MagicMock(),
                config={"host": "h", "port": 1},
            )
        ],
        SupervisorError("no"),
    ],
)
async def test_find_nothing_usable(hass: HomeAssistant, discoveries: Any) -> None:
    """Other services, incomplete announcements and a silent Supervisor mean no app."""
    hass.config.components.add("hassio")
    supervisor = MagicMock()
    supervisor.discovery.list = (
        AsyncMock(side_effect=discoveries)
        if isinstance(discoveries, Exception)
        else AsyncMock(return_value=discoveries)
    )
    with patch(
        "custom_components.storybox_plus.fetcher.get_supervisor_client", return_value=supervisor
    ):
        assert await fetcher.async_find(hass) is None


async def test_info(
    hass: HomeAssistant, fetcher_app: FakeFetcher, aioclient_mock: AiohttpClientMocker
) -> None:
    """The video comes back with ID, title and rounded length; the token goes along."""
    client = fetcher.FetcherClient(hass, APP)
    assert await client.async_info(VIDEO_URL) == fetcher.Video(VIDEO_ID, "Me at the zoo", 19)
    assert fetcher_app.calls == [("POST", "/info", {"url": VIDEO_URL})]
    assert aioclient_mock.mock_calls[-1][3]["Authorization"] == f"Bearer {FETCHER_TOKEN}"
    fetcher_app.info = {"id": VIDEO_ID, "duration": 19.6}
    assert await client.async_info(VIDEO_URL) == fetcher.Video(VIDEO_ID, VIDEO_ID, 20)
    fetcher_app.info = {"id": VIDEO_ID, "title": "No length", "duration": None}
    assert (await client.async_info(VIDEO_URL)).seconds is None


async def test_errors(
    hass: HomeAssistant, fetcher_app: FakeFetcher, aioclient_mock: AiohttpClientMocker
) -> None:
    """The app's refusals keep code and message; other answers and silence are told apart."""
    client = fetcher.FetcherClient(hass, APP)
    fetcher_app.info_error = (422, "not_available", "This video is not available")
    with pytest.raises(fetcher.FetcherError) as caught:
        await client.async_info(VIDEO_URL)
    assert (caught.value.code, caught.value.message) == (
        "not_available",
        "This video is not available",
    )
    # An error without the app's shape
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{APP.url}/info", status=500, text="boom")
    with pytest.raises(fetcher.FetcherError) as caught:
        await client.async_info(VIDEO_URL)
    assert caught.value.code == "app_error"
    assert "500" in caught.value.message
    # Silence
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{APP.url}/info", exc=TimeoutError())
    with pytest.raises(fetcher.FetcherUnavailable) as unavailable:
        await client.async_info(VIDEO_URL)
    assert unavailable.value.code == "unreachable"


async def test_job_and_file(
    hass: HomeAssistant, fetcher_app: FakeFetcher, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job is started with kind, format and limit, followed until done, and its file taken."""
    monkeypatch.setattr(fetcher, "POLL", 0)
    client = fetcher.FetcherClient(hass, APP)
    job_id = await client.async_start(VIDEO_URL, 5000)
    assert job_id == "job-1"
    assert fetcher_app.calls[-1] == (
        "POST",
        "/jobs",
        {"url": VIDEO_URL, "kind": "audio", "format": "m4a", "max_duration": 5000},
    )
    seen: list[fetcher.Job] = []
    job = await client.async_wait(job_id, seen.append, asyncio.Event())
    assert job.state == "done"
    assert job.ended
    assert [(j.state, j.done, j.total) for j in seen] == [
        ("downloading", 10, 20),
        ("converting", 20, 20),
    ]
    assert await client.async_file(job_id) == b"aac"
    await client.async_forget(job_id)
    assert fetcher_app.jobs[job_id]["deleted"] is True
    # Without a limit none is sent
    await client.async_start(VIDEO_URL, None)
    assert "max_duration" not in fetcher_app.calls[-1][2]


async def test_job_failed_or_cancelled(
    hass: HomeAssistant, fetcher_app: FakeFetcher, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed job raises with the app's words; a cancelled one, or a set event, raises FetchCancelled."""
    monkeypatch.setattr(fetcher, "POLL", 0)
    client = fetcher.FetcherClient(hass, APP)
    fetcher_app.states = [
        {"state": "downloading", "done_bytes": 1, "total_bytes": 0},
        {
            "state": "failed",
            "error": {"code": "download_failed", "message": "HTTP Error 403: Forbidden"},
        },
    ]
    seen: list[fetcher.Job] = []
    with pytest.raises(fetcher.FetcherError) as caught:
        await client.async_wait(
            await client.async_start(VIDEO_URL, None), seen.append, asyncio.Event()
        )
    assert (caught.value.code, caught.value.message) == (
        "download_failed",
        "HTTP Error 403: Forbidden",
    )
    assert seen[0].total is None
    fetcher_app.states = [{"state": "failed"}]
    with pytest.raises(fetcher.FetcherError) as bare:
        await client.async_wait(
            await client.async_start(VIDEO_URL, None), seen.append, asyncio.Event()
        )
    assert (bare.value.code, bare.value.message) == ("failed", "The app failed")
    fetcher_app.states = [{"state": "cancelled"}]
    with pytest.raises(fetcher.FetchCancelled):
        await client.async_wait(
            await client.async_start(VIDEO_URL, None), seen.append, asyncio.Event()
        )
    given_up = asyncio.Event()
    given_up.set()
    polls = len(fetcher_app.calls)
    with pytest.raises(fetcher.FetchCancelled):
        await client.async_wait("job-1", seen.append, given_up)
    assert len(fetcher_app.calls) == polls


async def test_file_refused(
    hass: HomeAssistant, fetcher_app: FakeFetcher, aioclient_mock: AiohttpClientMocker
) -> None:
    """A file asked too early is the app's refusal; a JSON answer in its place is an error too."""
    client = fetcher.FetcherClient(hass, APP)
    job_id = await client.async_start(VIDEO_URL, None)
    with pytest.raises(fetcher.FetcherError) as caught:
        await client.async_file(job_id)
    assert caught.value.code == "not_ready"
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{APP.url}/jobs/{job_id}/file",
        json={"odd": True},
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(fetcher.FetcherError) as odd:
        await client.async_file(job_id)
    assert odd.value.code == "no_file"
    # Forgetting a job the app no longer knows is no error
    aioclient_mock.clear_requests()
    aioclient_mock.delete(
        f"{APP.url}/jobs/{job_id}",
        status=404,
        json={"error": {"code": "not_found", "message": "gone"}},
    )
    await client.async_forget(job_id)
