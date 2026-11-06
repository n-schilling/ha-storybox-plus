"""The audio of a YouTube video as a file, through the yt-dlp Home Assistant ships.

Home Assistant's own Media extractor integration carries yt-dlp; this
integration depends on it and uses the same library, so the version follows
Home Assistant. Home Assistant's container has no JavaScript runtime, which
yt-dlp asks for since late 2025: it still serves the audio formats, but calls
that path deprecated, and warns about it on every call. The warning goes to
the debug log.

Everything here blocks and runs in the executor.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
import re
import threading
import time
from typing import Any
from urllib.parse import urlsplit

import yt_dlp
from yt_dlp.utils import DownloadCancelled, YoutubeDLError

_LOGGER = logging.getLogger(__name__)

# The hosts a link may name; yt-dlp never sees any other, and only its YouTube
# extractor is switched on: the generic one would fetch any address
_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtube-nocookie.com",
}

# The audio as the cloud takes it, AAC in an MP4 container; anything else is
# converted to that by ffmpeg, which Home Assistant's container ships
AUDIO_EXTENSION = "m4a"
_FORMAT = "bestaudio[ext=m4a]/bestaudio/best"
_CONVERT = {"key": "FFmpegExtractAudio", "preferredcodec": AUDIO_EXTENSION}

# How often the page hears about a running download at most (s)
_PROGRESS_EVERY = 0.5

# What yt-dlp puts before its messages: the level and the extractor with the video's ID
_MESSAGE_PREFIX = re.compile(r"^(?:ERROR: )?(?:\[[\w:]+\] )?(?:[\w-]{11}: )?")
_MESSAGE_MAX = 200

type Progress = Callable[[int, int | None], None]


class YouTubeError(Exception):
    """The video could not be read or fetched; the message is yt-dlp's, shortened."""


class YouTubeCancelled(YouTubeError):
    """The download was cancelled through its event."""


@dataclass(frozen=True, slots=True)
class Video:
    """What matters about a video before it is fetched."""

    id: str
    title: str
    seconds: int


def is_youtube(url: str) -> bool:
    """Whether the link names a YouTube video, as far as the address tells."""
    parts = urlsplit(url.strip())
    return parts.scheme in ("http", "https") and parts.hostname in _HOSTS


class _Log:
    """yt-dlp's messages, warnings included, go to the debug log; errors become the exception."""

    def debug(self, message: str) -> None:
        _LOGGER.debug("yt-dlp: %s", message)

    def info(self, message: str) -> None:
        _LOGGER.debug("yt-dlp: %s", message)

    def warning(self, message: str) -> None:
        _LOGGER.debug("yt-dlp warns: %s", message)

    def error(self, message: str) -> None:
        _LOGGER.debug("yt-dlp failed: %s", message)


def _options(**extra: Any) -> dict[str, Any]:
    return {
        "logger": _Log(),
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
        "allowed_extractors": ["youtube"],
        "cachedir": False,
        "format": _FORMAT,
        **extra,
    }


def _message(err: Exception) -> str:
    text = _MESSAGE_PREFIX.sub("", str(err).strip().splitlines()[0] if str(err).strip() else "")
    text = text or err.__class__.__name__
    return text if len(text) <= _MESSAGE_MAX else text[: _MESSAGE_MAX - 1] + "…"


def _video(info: dict[str, Any]) -> Video:
    """Read what matters from yt-dlp's answer, or refuse what cannot become a chapter."""
    if info.get("_type") in ("playlist", "multi_video"):
        raise YouTubeError("The link names a playlist, not a video")
    if info.get("is_live"):
        raise YouTubeError("The video is a live stream")
    duration = info.get("duration")
    if not isinstance(duration, int | float) or duration <= 0:
        raise YouTubeError("The length of the video is not known")
    video_id = str(info.get("id") or "")
    if not video_id:
        raise YouTubeError("The video has no ID")
    return Video(id=video_id, title=str(info.get("title") or video_id), seconds=round(duration))


def probe(url: str) -> Video:
    """Ask what the video is, without fetching it."""
    try:
        with yt_dlp.YoutubeDL(_options()) as ydl:
            info = ydl.extract_info(url, download=False)
    except YoutubeDLError as err:
        raise YouTubeError(_message(err)) from err
    return _video(info)


def download(url: str, folder: Path, progress: Progress, cancelled: threading.Event) -> Path:
    """Fetch the audio of the video into the folder and return the file.

    The progress callback hears the bytes done and the total, if known, from
    the download thread, at most every half second. Setting the event stops
    the download at the next progress report.
    """
    last = 0.0

    def hook(status: dict[str, Any]) -> None:
        nonlocal last
        if cancelled.is_set():
            raise DownloadCancelled("The download was cancelled")
        if status.get("status") != "downloading":
            return
        now = time.monotonic()
        if now - last < _PROGRESS_EVERY:
            return
        last = now
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        progress(int(status.get("downloaded_bytes") or 0), int(total) if total else None)

    options = _options(
        outtmpl=str(folder / "%(id)s.%(ext)s"),
        progress_hooks=[hook],
        postprocessors=[_CONVERT],
    )
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadCancelled as err:
        raise YouTubeCancelled(_message(err)) from err
    except YoutubeDLError as err:
        raise YouTubeError(_message(err)) from err
    downloads = info.get("requested_downloads") or []
    path = Path(str(downloads[0].get("filepath") or "")) if downloads else None
    if path is None or not path.is_file():
        raise YouTubeError("yt-dlp left no file behind")
    return path
