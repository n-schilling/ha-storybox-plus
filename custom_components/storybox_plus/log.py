"""The integration's own log: a level and a retention kept across restarts, the lines on disk.

Like the log level of an app, the level is one setting for the whole
integration: it applies to the logger custom_components.storybox_plus and
so to every module beneath it, the cloud client included. Home Assistant's
log gets the same lines.

The lines are also written to one file per day (JSON Lines) under
.storage/storybox_plus_log, so the page shows them across restarts; files
older than the retention are deleted. With a retention of 0 days nothing is
written and the page shows the lines since the start only.

Turning on debug logging on Home Assistant's own integration page still
works and wins until it is turned off again or Home Assistant restarts.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
import json
import logging
from pathlib import Path
import re
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from .cloud.rest import short_ids
from .const import DOMAIN, STORAGE_VERSION

LOGGER_NAME = f"custom_components.{DOMAIN}"
LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}
DEFAULT_LEVEL = "info"
DEFAULT_DAYS = 7
MAX_DAYS = 90
# Lines kept in memory: all the page shows while nothing is written to disk
KEEP_LINES = 1000
# New lines go to disk this often
FLUSH_INTERVAL = timedelta(seconds=10)
FOLDER = f"{DOMAIN}_log"
_FILE = re.compile(r"(\d{4}-\d{2}-\d{2})\.jsonl")

DATA_LOG: HassKey[IntegrationLog] = HassKey(f"{DOMAIN}_log")


def log_dir(hass: HomeAssistant) -> Path:
    """Where the files of the log lie."""
    return Path(hass.config.path(".storage", FOLDER))


@dataclass(frozen=True, slots=True)
class LogLine:
    """One line of the log as the page shows it."""

    time: str
    level: str
    source: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        """For the page and the file."""
        return {
            "time": self.time,
            "level": self.level,
            "source": self.source,
            "message": self.message,
        }


class _Keeper(logging.Handler):
    """Keeps the lines of the integration's logger; any thread may log."""

    def __init__(self, keep: Callable[[LogLine], None]) -> None:
        super().__init__(logging.DEBUG)
        self._keep = keep

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except TypeError, ValueError:
            message = str(record.msg)
        if record.exc_info and record.exc_info[1] is not None:
            err = record.exc_info[1]
            message = f"{message}: {type(err).__name__}: {err}"
        source = record.name.removeprefix(LOGGER_NAME).lstrip(".") or "integration"
        self._keep(
            LogLine(
                time=dt_util.utc_from_timestamp(record.created).isoformat(timespec="milliseconds"),
                level=record.levelname.lower(),
                source=source,
                message=short_ids(message)[:2000],
            )
        )


def _day_of(line: LogLine) -> date:
    """The local day a line belongs to, which names its file."""
    stamp = dt_util.parse_datetime(line.time)
    return dt_util.as_local(stamp).date() if stamp else dt_util.now().date()


def _write(folder: Path, lines: list[LogLine]) -> None:
    """Append lines to the files of their days (executor)."""
    folder.mkdir(parents=True, exist_ok=True)
    by_day: dict[date, list[str]] = {}
    for line in lines:
        by_day.setdefault(_day_of(line), []).append(json.dumps(line.as_dict(), ensure_ascii=False))
    for day, texts in by_day.items():
        with (folder / f"{day.isoformat()}.jsonl").open("a", encoding="utf-8") as file:
            file.write("\n".join(texts) + "\n")


def _days(folder: Path) -> list[tuple[date, Path]]:
    """The files of the log by day, newest first (executor)."""
    if not folder.is_dir():
        return []
    found = []
    for path in folder.iterdir():
        if (match := _FILE.fullmatch(path.name)) is None:
            continue
        try:
            found.append((date.fromisoformat(match[1]), path))
        except ValueError:
            continue
    return sorted(found, reverse=True)


def _prune(folder: Path, keep_from: date | None) -> None:
    """Delete the files of days before keep_from; None deletes all of them (executor)."""
    for day, path in _days(folder):
        if keep_from is None or day < keep_from:
            path.unlink(missing_ok=True)
    if keep_from is None and folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()


def _read(folder: Path, limit: int | None) -> list[LogLine]:
    """The lines of the files, newest first, at most limit (executor)."""
    lines: list[LogLine] = []
    for _, path in _days(folder):
        day: list[LogLine] = []
        for text in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                raw = json.loads(text)
                day.append(
                    LogLine(
                        str(raw["time"]), str(raw["level"]), str(raw["source"]), str(raw["message"])
                    )
                )
            except ValueError, KeyError, TypeError:
                continue
        day.reverse()
        lines.extend(day)
        if limit is not None and len(lines) >= limit:
            return lines[:limit]
    return lines


class IntegrationLog:
    """The level and retention of the integration's log, and its lines."""

    def __init__(self, hass: HomeAssistant, store: Store[dict[str, Any]], folder: Path) -> None:
        """Start with the defaults; async_load reads the stored settings."""
        self._hass = hass
        self._store = store
        self.folder = folder
        self.level = DEFAULT_LEVEL
        self.days = DEFAULT_DAYS
        self.lines: deque[LogLine] = deque(maxlen=KEEP_LINES)
        # Lines not yet on disk; appended from any thread, taken in the event loop
        self._pending: deque[LogLine] = deque()
        self._handler = _Keeper(self._keep)
        self._unsub: CALLBACK_TYPE | None = None
        self._unsub_final: CALLBACK_TYPE | None = None

    def _keep(self, line: LogLine) -> None:
        self.lines.append(line)
        if self.days:
            self._pending.append(line)

    async def async_load(self) -> None:
        """Read the stored settings, start keeping lines and writing them."""
        raw = await self._store.async_load()
        if isinstance(raw, dict):
            if raw.get("level") in LEVELS:
                self.level = raw["level"]
            days = raw.get("days")
            if isinstance(days, int) and not isinstance(days, bool) and 0 <= days <= MAX_DAYS:
                self.days = days
        self._apply()
        logger = logging.getLogger(LOGGER_NAME)
        if self._handler not in logger.handlers:
            logger.addHandler(self._handler)
        await self._async_prune()
        # The timer ends with Home Assistant; the last lines are written at its final write
        self._unsub = async_track_time_interval(
            self._hass, self._flush_soon, FLUSH_INTERVAL, cancel_on_shutdown=True
        )
        self._unsub_final = self._hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_FINAL_WRITE, self._async_final
        )

    async def _async_final(self, _event: Any) -> None:
        self._unsub_final = None
        await self.async_flush()

    async def async_close(self) -> None:
        """Stop keeping lines and write the last ones; the settings stay."""
        logging.getLogger(LOGGER_NAME).removeHandler(self._handler)
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        if self._unsub_final is not None:
            self._unsub_final()
            self._unsub_final = None
        await self.async_flush()

    @callback
    def _flush_soon(self, _now: Any = None) -> None:
        self._hass.async_create_background_task(self._async_tick(), f"{DOMAIN} log flush")

    async def _async_tick(self) -> None:
        await self.async_flush()
        await self._async_prune()

    async def async_flush(self) -> None:
        """Write the lines not yet on disk."""
        lines: list[LogLine] = []
        while self._pending:
            lines.append(self._pending.popleft())
        if lines and self.days:
            await self._hass.async_add_executor_job(_write, self.folder, lines)

    async def _async_prune(self) -> None:
        """Delete what is older than the retention; with 0 days, every file."""
        keep_from = dt_util.now().date() - timedelta(days=self.days - 1) if self.days else None
        await self._hass.async_add_executor_job(_prune, self.folder, keep_from)

    async def async_set(self, level: str | None = None, days: int | None = None) -> None:
        """Change level and retention, now and for the next start."""
        if level is not None:
            if level not in LEVELS:
                raise ValueError(level)
            self.level = level
            self._apply()
        if days is not None:
            if not 0 <= days <= MAX_DAYS:
                raise ValueError(days)
            self.days = days
            if not days:
                self._pending.clear()
            await self._async_prune()
        await self._store.async_save({"level": self.level, "days": self.days})

    def _apply(self) -> None:
        logging.getLogger(LOGGER_NAME).setLevel(LEVELS[self.level])

    async def async_lines(self, limit: int | None) -> list[LogLine]:
        """The latest lines, newest first: from disk while it is kept, else from memory."""
        if not self.days:
            lines = list(self.lines)
            lines.reverse()
            return lines[:limit] if limit is not None else lines
        await self.async_flush()
        return await self._hass.async_add_executor_job(_read, self.folder, limit)

    async def async_as_dict(self, limit: int | None = None) -> dict[str, Any]:
        """For the page: the settings and the latest lines, newest first."""
        lines = await self.async_lines(limit) if limit != 0 else []
        return {
            "level": self.level,
            "days": self.days,
            "effective": logging.getLevelName(
                logging.getLogger(LOGGER_NAME).getEffectiveLevel()
            ).lower(),
            "lines": [line.as_dict() for line in lines],
        }


def log_store(hass: HomeAssistant) -> Store[dict[str, Any]]:
    """The store of the log's settings."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.log")


async def async_get_log(hass: HomeAssistant) -> IntegrationLog:
    """Return the integration's log, set up once for all accounts."""
    if (log := hass.data.get(DATA_LOG)) is None:
        log = IntegrationLog(hass, log_store(hass), log_dir(hass))
        hass.data[DATA_LOG] = log
        await log.async_load()
    return log


async def async_remove_log(hass: HomeAssistant) -> None:
    """Forget settings and files, with the integration's last account."""
    await log_store(hass).async_remove()
    await hass.async_add_executor_job(_prune, log_dir(hass), None)
