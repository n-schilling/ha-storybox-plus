"""The Media Fetcher app: found through the Supervisor, asked over HTTP.

The app, a Home Assistant app of its own, fetches the audio of a video with
yt-dlp and a JavaScript runtime, which Home Assistant's own container lacks.
The integration asks the Supervisor whether the app is installed and
started, whenever the page needs it, and talks to the app's HTTP API in
Home Assistant's app network. The app trusts Home Assistant's address
there, so no token travels; other clients of the app need its token.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from aiohasupervisor import SupervisorError
from aiohasupervisor.models import AddonState
import aiohttp

from homeassistant.components.hassio import get_supervisor_client, hostname_from_addon_slug
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.hassio import is_hassio

_LOGGER = logging.getLogger(__name__)

# The app's slug; the Supervisor puts the repository's prefix before it
SLUG = "media_fetcher"
PORT = 8099
API = "/api/v1"
TIMEOUT = aiohttp.ClientTimeout(total=30)
FILE_TIMEOUT = aiohttp.ClientTimeout(total=600)
# How often a running job is asked about (s)
POLL = 1.0
# The largest file taken from the app: far more than the 90 minutes of audio
# a figure holds, as m4a
MAX_FILE_BYTES = 200 * 1024 * 1024

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
    # Only a client outside Home Assistant needs one
    token: str | None = None

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
    """Return the app as the Supervisor lists it, if it is installed and started.

    The Supervisor names the app's container after its slug in the app
    network, so the slug is all the integration needs.
    """
    if not is_hassio(hass):
        return None
    try:
        addons = await get_supervisor_client(hass).addons.list()
    except SupervisorError as err:
        _LOGGER.debug("The Supervisor did not list the apps: %s", err)
        return None
    for addon in addons:
        if addon.slug != SLUG and not addon.slug.endswith(f"_{SLUG}"):
            continue
        if addon.state is AddonState.STARTED:
            return Fetcher(hostname_from_addon_slug(addon.slug), PORT)
        _LOGGER.debug("The app %s is installed but not started", addon.slug)
    return None


def _object(body: Any, what: str) -> dict[str, Any]:
    """Return the JSON object the app answered, or refuse an answer of another shape."""
    if not isinstance(body, dict):
        raise FetcherError("bad_answer", f"The app answered {what} without a JSON object")
    return body


def _video(data: dict[str, Any]) -> Video:
    video_id = str(data.get("id") or "")
    duration = data.get("duration")
    return Video(
        id=video_id,
        title=str(data.get("title") or video_id),
        seconds=round(duration) if isinstance(duration, int | float) else None,
    )


def _job(data: dict[str, Any]) -> Job:
    error = data.get("error")
    if not isinstance(error, dict):
        error = {}
    total = data.get("total_bytes")
    return Job(
        id=str(data.get("id") or ""),
        state=str(data.get("state") or ""),
        done=int(data.get("done_bytes") or 0),
        total=int(total) if isinstance(total, int | float) and total > 0 else None,
        content_type=_audio_type(data.get("content_type")),
        error_code=str(error["code"]) if error.get("code") else None,
        error_message=str(error["message"]) if error.get("message") else None,
    )


def _audio_type(value: Any) -> str | None:
    """Return the content type of the file if it names audio; anything else is not passed on."""
    if isinstance(value, str) and value.lower().startswith("audio/"):
        return value
    return None


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
        """Ask the app; an error answer becomes a FetcherError, silence FetcherUnavailable.

        A JSON answer comes back decoded, anything else as bytes, at most
        MAX_FILE_BYTES of them.
        """
        headers = {"Authorization": f"Bearer {self._fetcher.token}"} if self._fetcher.token else {}
        try:
            async with self._session.request(
                method, f"{self._fetcher.url}{path}", json=json, headers=headers, timeout=wait
            ) as resp:
                if resp.status == 204:
                    return None
                if resp.content_type == "application/json":
                    body = await resp.json()
                else:
                    body = await _read_limited(resp)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FetcherUnavailable("unreachable", f"The app does not answer: {err}") from err
        except ValueError as err:
            raise FetcherError("bad_answer", f"{method} {path} answered broken JSON") from err
        if resp.status >= 400:
            error = body.get("error") if isinstance(body, dict) else None
            if isinstance(error, dict) and error.get("code"):
                raise FetcherError(str(error["code"]), str(error.get("message") or error["code"]))
            raise FetcherError("app_error", f"{method} {path} answered {resp.status}")
        return body

    async def async_info(self, url: str) -> Video:
        """Ask what the video is, without fetching it."""
        return _video(_object(await self._request("POST", "/info", {"url": url}), "the info"))

    async def async_start(self, url: str, max_seconds: int | None) -> str:
        """Start a job for the audio of the video; return its ID."""
        body: dict[str, Any] = {"url": url, "kind": KIND, "format": FORMAT}
        if max_seconds is not None:
            body["max_duration"] = max_seconds
        answer = _object(await self._request("POST", "/jobs", body), "the job")
        if not answer.get("id"):
            raise FetcherError("bad_answer", "The app answered the job without an ID")
        return str(answer["id"])

    async def async_job(self, job_id: str) -> Job:
        """Ask how far a job is."""
        return _job(_object(await self._request("GET", f"/jobs/{job_id}"), "the job"))

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


async def _read_limited(resp: aiohttp.ClientResponse) -> bytes:
    """Read a body of at most MAX_FILE_BYTES; a larger one is refused, also while it arrives."""
    if resp.content_length is not None and resp.content_length > MAX_FILE_BYTES:
        raise FetcherError("too_large", "The app's file is larger than a figure can hold")
    data = bytearray()
    async for chunk in resp.content.iter_chunked(1024 * 1024):
        data.extend(chunk)
        if len(data) > MAX_FILE_BYTES:
            raise FetcherError("too_large", "The app's file is larger than a figure can hold")
    return bytes(data)
