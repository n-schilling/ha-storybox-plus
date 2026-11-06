"""The Media Fetcher app: found through the Supervisor, asked over HTTP.

The app, a Home Assistant app of its own, fetches the audio of a video with
yt-dlp and a JavaScript runtime, which Home Assistant's own container lacks.
It announces itself to the Supervisor as the service "media_fetcher" with
host, port and token; the integration reads that announcement whenever the
page needs the app and talks to the app's HTTP API.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from aiohasupervisor import SupervisorError
import aiohttp

from homeassistant.components.hassio import get_supervisor_client
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.hassio import is_hassio

_LOGGER = logging.getLogger(__name__)

# The service the app announces to the Supervisor
SERVICE = "media_fetcher"
API = "/api/v1"
TIMEOUT = aiohttp.ClientTimeout(total=30)
FILE_TIMEOUT = aiohttp.ClientTimeout(total=600)
# How often a running job is asked about (s)
POLL = 1.0

# The audio as the cloud takes it
KIND = "audio"
FORMAT = "m4a"
CONTENT_TYPE = "audio/mp4"

_ENDED = ("done", "failed", "cancelled")


class FetcherError(Exception):
    """The app refused or failed; the code and the message are the app's."""

    def __init__(self, code: str, message: str) -> None:
        """Keep the code and the message."""
        super().__init__(message)
        self.code = code
        self.message = message


class FetcherUnavailable(FetcherError):
    """The app does not answer."""


class FetchCancelled(Exception):
    """The job was given up before it ended."""


@dataclass(frozen=True, slots=True)
class Fetcher:
    """Where the app answers."""

    host: str
    port: int
    token: str

    @property
    def url(self) -> str:
        """The base of the API."""
        return f"http://{self.host}:{self.port}{API}"


@dataclass(frozen=True, slots=True)
class Video:
    """What the app tells about a video before it is fetched."""

    id: str
    title: str
    seconds: int | None


@dataclass(frozen=True, slots=True)
class Job:
    """A job of the app, as last asked."""

    id: str
    state: str
    done: int
    total: int | None
    content_type: str | None
    error_code: str | None
    error_message: str | None

    @property
    def ended(self) -> bool:
        """Whether the job will not change any more."""
        return self.state in _ENDED


async def async_find(hass: HomeAssistant) -> Fetcher | None:
    """Return the app as it announced itself to the Supervisor, if it did."""
    if not is_hassio(hass):
        return None
    try:
        messages = await get_supervisor_client(hass).discovery.list()
    except SupervisorError as err:
        _LOGGER.debug("The Supervisor did not list the discoveries: %s", err)
        return None
    for message in messages:
        if message.service != SERVICE:
            continue
        host = message.config.get("host")
        port = message.config.get("port")
        token = message.config.get("token")
        if isinstance(host, str) and host and isinstance(port, int) and isinstance(token, str):
            return Fetcher(host, port, token)
        _LOGGER.debug("The app announced itself without host, port or token")
    return None


def _video(data: dict[str, Any]) -> Video:
    video_id = str(data.get("id") or "")
    duration = data.get("duration")
    return Video(
        id=video_id,
        title=str(data.get("title") or video_id),
        seconds=round(duration) if isinstance(duration, int | float) else None,
    )


def _job(data: dict[str, Any]) -> Job:
    error = data.get("error") or {}
    total = data.get("total_bytes")
    return Job(
        id=str(data.get("id") or ""),
        state=str(data.get("state") or ""),
        done=int(data.get("done_bytes") or 0),
        total=int(total) if isinstance(total, int | float) and total > 0 else None,
        content_type=data.get("content_type") or None,
        error_code=error.get("code") or None,
        error_message=error.get("message") or None,
    )


class FetcherClient:
    """The app's HTTP API."""

    def __init__(self, hass: HomeAssistant, fetcher: Fetcher) -> None:
        """Use Home Assistant's session."""
        self._session = async_get_clientsession(hass)
        self._fetcher = fetcher

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        wait: aiohttp.ClientTimeout = TIMEOUT,
    ) -> Any:
        """Ask the app; an error answer becomes a FetcherError, silence FetcherUnavailable."""
        headers = {"Authorization": f"Bearer {self._fetcher.token}"}
        try:
            async with self._session.request(
                method, f"{self._fetcher.url}{path}", json=json, headers=headers, timeout=wait
            ) as resp:
                if resp.status == 204:
                    return None
                if resp.content_type == "application/json":
                    body = await resp.json()
                else:
                    body = await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FetcherUnavailable("unreachable", f"The app does not answer: {err}") from err
        if resp.status >= 400:
            error = body.get("error") if isinstance(body, dict) else None
            if isinstance(error, dict) and error.get("code"):
                raise FetcherError(str(error["code"]), str(error.get("message") or error["code"]))
            raise FetcherError("app_error", f"{method} {path} answered {resp.status}")
        return body

    async def async_info(self, url: str) -> Video:
        """Ask what the video is, without fetching it."""
        return _video(await self._request("POST", "/info", {"url": url}))

    async def async_start(self, url: str, max_seconds: int | None) -> str:
        """Start a job for the audio of the video; return its ID."""
        body: dict[str, Any] = {"url": url, "kind": KIND, "format": FORMAT}
        if max_seconds is not None:
            body["max_duration"] = max_seconds
        answer = await self._request("POST", "/jobs", body)
        return str(answer["id"])

    async def async_job(self, job_id: str) -> Job:
        """Ask how far a job is."""
        return _job(await self._request("GET", f"/jobs/{job_id}"))

    async def async_wait(
        self, job_id: str, report: Callable[[Job], None], cancelled: asyncio.Event
    ) -> Job:
        """Ask about the job until it ended; a set event gives it up.

        Every answer of a running job goes to the report callback. A job
        that failed raises with the app's code and message; one the app
        cancelled, or the event, raises FetchCancelled.
        """
        while True:
            if cancelled.is_set():
                raise FetchCancelled
            job = await self.async_job(job_id)
            if job.state == "done":
                return job
            if job.state == "failed":
                raise FetcherError(
                    job.error_code or "failed", job.error_message or "The app failed"
                )
            if job.state == "cancelled":
                raise FetchCancelled
            report(job)
            await asyncio.sleep(POLL)

    async def async_file(self, job_id: str) -> bytes:
        """Take the file of a job that ended well."""
        body = await self._request("GET", f"/jobs/{job_id}/file", wait=FILE_TIMEOUT)
        if not isinstance(body, bytes):
            raise FetcherError("no_file", "The app answered without a file")
        return body

    async def async_forget(self, job_id: str) -> None:
        """Cancel or delete the job; the app's refusal does not matter any more."""
        try:
            await self._request("DELETE", f"/jobs/{job_id}")
        except FetcherError as err:
            _LOGGER.debug("The job %s was not deleted: %s", job_id, err)
