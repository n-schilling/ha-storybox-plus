"""The yt-dlp wrapper: which links it takes, what it asks yt-dlp, and how it reads the answers."""

from __future__ import annotations

import logging
from pathlib import Path
import threading
from typing import Any, ClassVar

import pytest
from yt_dlp.utils import DownloadCancelled, DownloadError

from custom_components.storybox_plus import youtube

VIDEO_ID = "jNQXAC9IVRw"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
INFO: dict[str, Any] = {"id": VIDEO_ID, "title": "Me at the zoo", "duration": 19.06}


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL: keeps the options, answers canned info, writes a file."""

    info: ClassVar[dict[str, Any]] = INFO
    error: ClassVar[Exception | None] = None
    hooks: ClassVar[list[dict[str, Any]]] = [
        {"status": "downloading", "downloaded_bytes": 10, "total_bytes": 20},
        {"status": "downloading", "downloaded_bytes": 20, "total_bytes": 20},
        {"status": "finished"},
    ]
    instances: ClassVar[list[FakeYoutubeDL]] = []

    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options
        self.calls: list[tuple[str, bool]] = []
        FakeYoutubeDL.instances.append(self)

    def __enter__(self) -> FakeYoutubeDL:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        self.calls.append((url, download))
        if self.error is not None:
            raise self.error
        info = dict(self.info)
        if download:
            folder = Path(self.options["outtmpl"]).parent
            path = folder / f"{info['id']}.m4a"
            path.write_bytes(b"aac")
            for status in self.hooks:
                for hook in self.options.get("progress_hooks", []):
                    hook(status)
            info["requested_downloads"] = [{"filepath": str(path)}]
        return info


@pytest.fixture(autouse=True)
def fake_ydl(monkeypatch: pytest.MonkeyPatch) -> type[FakeYoutubeDL]:
    """Put the fake in place of yt-dlp and reset it."""
    monkeypatch.setattr(youtube.yt_dlp, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(FakeYoutubeDL, "info", INFO)
    monkeypatch.setattr(FakeYoutubeDL, "error", None)
    monkeypatch.setattr(FakeYoutubeDL, "instances", [])
    return FakeYoutubeDL


@pytest.mark.parametrize(
    ("url", "taken"),
    [
        (URL, True),
        (f"https://youtu.be/{VIDEO_ID}", True),
        (f" https://m.youtube.com/watch?v={VIDEO_ID} ", True),
        (f"http://music.youtube.com/watch?v={VIDEO_ID}", True),
        (f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}", True),
        (f"https://example.com/watch?v={VIDEO_ID}", False),
        (f"https://youtube.com.example.net/watch?v={VIDEO_ID}", False),
        (f"ftp://www.youtube.com/watch?v={VIDEO_ID}", False),
        (f"www.youtube.com/watch?v={VIDEO_ID}", False),
        ("", False),
        ("not a link", False),
    ],
)
def test_is_youtube(url: str, taken: bool) -> None:
    """Only addresses of YouTube pass; everything else is refused before yt-dlp sees it."""
    assert youtube.is_youtube(url) is taken


def test_probe(fake_ydl: type[FakeYoutubeDL]) -> None:
    """Probing reads ID, title and the rounded length, without downloading."""
    assert youtube.probe(URL) == youtube.Video(id=VIDEO_ID, title="Me at the zoo", seconds=19)
    (ydl,) = fake_ydl.instances
    assert ydl.calls == [(URL, False)]
    options = ydl.options
    assert options["noplaylist"] is True
    assert options["allowed_extractors"] == ["youtube"]
    assert options["cachedir"] is False
    assert options["quiet"] is True
    assert options["format"].startswith("bestaudio[ext=m4a]")
    assert "postprocessors" not in options
    assert isinstance(options["logger"], youtube._Log)


def test_probe_title_falls_back_to_the_id(fake_ydl: type[FakeYoutubeDL]) -> None:
    """A video without a title is named by its ID."""
    fake_ydl.info = {"id": VIDEO_ID, "duration": 60}
    assert youtube.probe(URL).title == VIDEO_ID


@pytest.mark.parametrize(
    ("info", "message"),
    [
        ({"_type": "playlist", "id": "PL1", "title": "Songs"}, "playlist"),
        ({"id": VIDEO_ID, "title": "Live", "duration": 100, "is_live": True}, "live stream"),
        ({"id": VIDEO_ID, "title": "No length"}, "length"),
        ({"id": VIDEO_ID, "title": "Zero", "duration": 0}, "length"),
        ({"id": VIDEO_ID, "title": "Text", "duration": "19"}, "length"),
        ({"title": "No id", "duration": 19}, "ID"),
    ],
)
def test_probe_refuses_what_cannot_be_a_chapter(
    fake_ydl: type[FakeYoutubeDL], info: dict[str, Any], message: str
) -> None:
    """Playlists, live streams and videos of unknown length are refused."""
    fake_ydl.info = info
    with pytest.raises(youtube.YouTubeError, match=message):
        youtube.probe(URL)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (DownloadError(f"ERROR: [youtube] {VIDEO_ID}: Video unavailable"), "Video unavailable"),
        (
            DownloadError("ERROR: Unsupported URL: https://www.youtube.com/playlist"),
            "Unsupported URL: https://www.youtube.com/playlist",
        ),
        (DownloadError("[youtube:tab] Sign in\nmore"), "Sign in"),
        (DownloadError("x" * 300), "x" * 199 + "…"),
        (DownloadError(""), "DownloadError"),
    ],
)
def test_probe_shortens_yt_dlp_errors(
    fake_ydl: type[FakeYoutubeDL], error: Exception, message: str
) -> None:
    """yt-dlp's errors lose their level and extractor prefix and keep their first line."""
    fake_ydl.error = error
    with pytest.raises(youtube.YouTubeError) as caught:
        youtube.probe(URL)
    assert str(caught.value) == message


def test_download(
    fake_ydl: type[FakeYoutubeDL], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The audio lands in the folder as M4A, converted by ffmpeg if need be, with progress."""
    monkeypatch.setattr(youtube, "_PROGRESS_EVERY", 0)
    heard: list[tuple[int, int | None]] = []
    path = youtube.download(URL, tmp_path, lambda d, t: heard.append((d, t)), threading.Event())
    assert path == tmp_path / f"{VIDEO_ID}.m4a"
    assert path.read_bytes() == b"aac"
    assert heard == [(10, 20), (20, 20)]
    (ydl,) = fake_ydl.instances
    assert ydl.calls == [(URL, True)]
    assert ydl.options["outtmpl"] == str(tmp_path / "%(id)s.%(ext)s")
    assert ydl.options["postprocessors"] == [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]
    assert ydl.options["noplaylist"] is True


def test_download_reports_at_most_every_half_second(
    fake_ydl: type[FakeYoutubeDL], tmp_path: Path
) -> None:
    """Two reports within half a second become one; an unknown total is passed as None."""
    fake_ydl.hooks = [
        {"status": "downloading", "downloaded_bytes": 5, "total_bytes_estimate": 50.0},
        {"status": "downloading", "downloaded_bytes": 6},
        {"status": "finished"},
    ]
    heard: list[tuple[int, int | None]] = []
    youtube.download(URL, tmp_path, lambda d, t: heard.append((d, t)), threading.Event())
    assert heard == [(5, 50)]


def test_download_stops_when_cancelled(fake_ydl: type[FakeYoutubeDL], tmp_path: Path) -> None:
    """A set event makes the next progress report abort the download."""
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(youtube.YouTubeCancelled):
        youtube.download(URL, tmp_path, lambda d, t: None, cancelled)


def test_download_without_a_file(fake_ydl: type[FakeYoutubeDL], tmp_path: Path) -> None:
    """yt-dlp answering without a download is an error, not a silent empty chapter."""

    class NoFile(FakeYoutubeDL):
        def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
            return dict(INFO)

    fake_ydl_module = youtube.yt_dlp
    fake_ydl_module.YoutubeDL = NoFile  # type: ignore[attr-defined]
    with pytest.raises(youtube.YouTubeError, match="no file"):
        youtube.download(URL, tmp_path, lambda d, t: None, threading.Event())


def test_download_errors_are_shortened(fake_ydl: type[FakeYoutubeDL], tmp_path: Path) -> None:
    """A failed download tells yt-dlp's reason, shortened."""
    fake_ydl.error = DownloadError(f"ERROR: [youtube] {VIDEO_ID}: HTTP Error 403: Forbidden")
    with pytest.raises(youtube.YouTubeError, match=r"^HTTP Error 403: Forbidden$"):
        youtube.download(URL, tmp_path, lambda d, t: None, threading.Event())


def test_cancelled_from_yt_dlp_is_cancelled(fake_ydl: type[FakeYoutubeDL], tmp_path: Path) -> None:
    """yt-dlp's own cancellation is told apart from a failure."""
    fake_ydl.error = DownloadCancelled("stopped")
    with pytest.raises(youtube.YouTubeCancelled):
        youtube.download(URL, tmp_path, lambda d, t: None, threading.Event())


def test_yt_dlp_messages_go_to_the_debug_log(caplog: pytest.LogCaptureFixture) -> None:
    """Warnings and errors of yt-dlp are debug lines here; the exception carries the error."""
    log = youtube._Log()
    with caplog.at_level(logging.DEBUG, logger="custom_components.storybox_plus.youtube"):
        log.debug("[debug] loaded")
        log.info("Downloading webpage")
        log.warning("No supported JavaScript runtime")
        log.error("Video unavailable")
    assert all(r.levelno == logging.DEBUG for r in caplog.records)
    assert [r.getMessage() for r in caplog.records] == [
        "yt-dlp: [debug] loaded",
        "yt-dlp: Downloading webpage",
        "yt-dlp warns: No supported JavaScript runtime",
        "yt-dlp failed: Video unavailable",
    ]
