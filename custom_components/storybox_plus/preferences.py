"""The account's preferences from the page's settings tab, and which figures were locked.

Three preferences, each per account:

- analytics (on by default): listening time is counted (daily sums for the
  listening tab). Switched off, the sums are deleted; the entry reloads.
- auto_lock (on by default): a bought figure or disc that is new in the
  account is locked to the household once, so it cannot be claimed into
  another one. Unlocking it on the page or in the app is final: a figure is
  looked at only the first time it shows up. Switched off, new figures are
  noted without being locked, so switching it on later touches only figures
  that come after.
- mark_read (off by default): a notification of the cloud is marked as read
  there once it was passed on, so the app shows it no more.
- analytics_days (730 by default): how many days of listening sums are
  kept; 0 keeps them all.
- speech_engine (none by default): the text-to-speech entity that speaks text
  chapters; none is Piper, if it is set up. A voice of a cloud service gets
  the text.
- voice, voice_language (none by default): the voice of that entity; none is
  its own default voice. A new entity starts with its default voice.
- fetch_max_mb (200 by default): the largest file taken from the Media
  Fetcher app.
- presence (none by default): per Toniebox 1 an entity of Home Assistant that
  tells whether the box is in the network (a device tracker, or a binary
  sensor for connectivity). The cloud knows nothing live of such a box; with
  the entity the page shows it as online or offline and counts how long it
  was awake (see analytics, active time).
- repeat (none by default): per Toniebox 2 the repeat set for the figure on it
  ("all" or "one") with that figure, so it goes on after a restart.
- favourites_mode ("first" by default): how the favourite chapters of a figure
  play on a Toniebox 2, unless the figure has a mode of its own (see favourites).
- cloud_check (none by default): what the last check of the cloud's interface
  found, with the release it ran against; no setting, kept so the page shows it
  after a restart.
- presence_lag (20 minutes by default): per Toniebox 1 how long it stays in
  the network after its last use, by the entity; taken off its active time.

The figures that were already in the account when the integration first ran
count as known: whether they are locked stays as it was.
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.storage import Store

from .cloud import Tonie, TonieKind
from .favourites import DEFAULT_MODE, MODES, Mode

DEFAULT_ANALYTICS = True
DEFAULT_AUTO_LOCK = True
DEFAULT_MARK_READ = False
DEFAULT_ANALYTICS_DAYS = 730
ANALYTICS_DAYS = (0, 365, 730, 1825)
DEFAULT_FETCH_MAX_MB = 200
FETCH_MAX_MB = (10, 2000)
LOCKABLE = frozenset({TonieKind.CONTENT, TonieKind.DISC})
PRESENCE_DOMAINS = ("device_tracker", "binary_sensor")
# Minutes a Toniebox 1 stays in the network after its last use, as its tracker sees it:
# the box's own standby and the tracker's delay together, measured at about 20
DEFAULT_PRESENCE_LAG = 20
PRESENCE_LAG = (0, 120)
_PREFIXES = tuple(f"{domain}." for domain in PRESENCE_DOMAINS)


class Preferences:
    """The preferences of one account and the figures looked at for locking."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start with the defaults; async_load reads the store."""
        self._store = store
        self.analytics = DEFAULT_ANALYTICS
        self.auto_lock = DEFAULT_AUTO_LOCK
        self.mark_read = DEFAULT_MARK_READ
        self.analytics_days = DEFAULT_ANALYTICS_DAYS
        self.speech_engine: str | None = None
        self.voice: str | None = None
        self.voice_language: str | None = None
        self.fetch_max_mb = DEFAULT_FETCH_MAX_MB
        self.favourites_mode: Mode = DEFAULT_MODE
        # What the last check of the cloud's interface found (see cloud/contract.py)
        self.cloud_check: dict[str, Any] | None = None
        # box_id -> entity_id
        self.presence: dict[str, str] = {}
        # box_id -> (mode, the figure it was set for)
        self.repeat: dict[str, tuple[str, str]] = {}
        # box_id -> minutes, where it differs from the default
        self._presence_lag: dict[str, int] = {}
        self._known: set[str] = set()
        # None until the figures of the first run were taken as known
        self._started = False

    async def async_load(self) -> None:
        """Read the store."""
        raw = await self._store.async_load()
        if not isinstance(raw, dict):
            return
        if isinstance(raw.get("analytics"), bool):
            self.analytics = raw["analytics"]
        if isinstance(raw.get("auto_lock"), bool):
            self.auto_lock = raw["auto_lock"]
        if isinstance(raw.get("mark_read"), bool):
            self.mark_read = raw["mark_read"]
        if raw.get("analytics_days") in ANALYTICS_DAYS:
            self.analytics_days = raw["analytics_days"]
        engine = raw.get("speech_engine")
        if isinstance(engine, str) and engine.startswith("tts."):
            self.speech_engine = engine
        if isinstance(raw.get("voice"), str) and isinstance(raw.get("voice_language"), str):
            self.voice = raw["voice"]
            self.voice_language = raw["voice_language"]
        mb = raw.get("fetch_max_mb")
        if (
            isinstance(mb, int)
            and not isinstance(mb, bool)
            and FETCH_MAX_MB[0] <= mb <= FETCH_MAX_MB[1]
        ):
            self.fetch_max_mb = mb
        if raw.get("favourites_mode") in MODES:
            self.favourites_mode = raw["favourites_mode"]
        check = raw.get("cloud_check")
        if isinstance(check, dict) and isinstance(check.get("results"), list):
            self.cloud_check = check
        presence = raw.get("presence")
        if isinstance(presence, dict):
            self.presence = {
                box: entity
                for box, entity in presence.items()
                if isinstance(entity, str) and entity.startswith(_PREFIXES)
            }
        repeats = raw.get("repeat")
        if isinstance(repeats, dict):
            self.repeat = {
                box: (item["mode"], item["tonie"])
                for box, item in repeats.items()
                if isinstance(item, dict)
                and item.get("mode") in ("all", "one")
                and isinstance(item.get("tonie"), str)
            }
        lags = raw.get("presence_lag")
        if isinstance(lags, dict):
            self._presence_lag = {
                box: lag
                for box, lag in lags.items()
                if isinstance(lag, int)
                and not isinstance(lag, bool)
                and PRESENCE_LAG[0] <= lag <= PRESENCE_LAG[1]
            }
        known = raw.get("known")
        if isinstance(known, list):
            self._known = {k for k in known if isinstance(k, str)}
            self._started = True

    def as_dict(self) -> dict[str, Any]:
        """For the page."""
        return {
            "analytics": self.analytics,
            "auto_lock": self.auto_lock,
            "mark_read": self.mark_read,
            "analytics_days": self.analytics_days,
            "speech_engine": self.speech_engine,
            "voice": self.voice,
            "voice_language": self.voice_language,
            "fetch_max_mb": self.fetch_max_mb,
            "favourites_mode": self.favourites_mode,
        }

    @property
    def fetch_max_bytes(self) -> int:
        """The largest file taken from the Media Fetcher app, in bytes."""
        return self.fetch_max_mb * 1024 * 1024

    async def async_set(self, **changes: Any) -> None:
        """Change the given preferences; None leaves one as it is, except for the voice.

        A voice comes with its language; an empty voice is the engine's default.
        Another engine starts with its default voice, unless one comes with it.
        """
        for key in ("analytics", "auto_lock", "mark_read"):
            if isinstance(changes.get(key), bool):
                setattr(self, key, changes[key])
        if (days := changes.get("analytics_days")) is not None:
            if days not in ANALYTICS_DAYS:
                raise ValueError(days)
            self.analytics_days = days
        if (mb := changes.get("fetch_max_mb")) is not None:
            if not FETCH_MAX_MB[0] <= mb <= FETCH_MAX_MB[1]:
                raise ValueError(mb)
            self.fetch_max_mb = mb
        if (mode := changes.get("favourites_mode")) is not None:
            if mode not in MODES:
                raise ValueError(mode)
            self.favourites_mode = mode
        if "speech_engine" in changes:
            engine = changes["speech_engine"] or None
            if engine is not None and not engine.startswith("tts."):
                raise ValueError("speech_engine")
            if engine != self.speech_engine:
                self.voice = self.voice_language = None
            self.speech_engine = engine
        if "voice" in changes:
            voice = changes["voice"] or None
            language = changes.get("voice_language") or None
            if voice is not None and language is None:
                raise ValueError("voice_language")
            self.voice = voice
            self.voice_language = language if voice else None
        await self.async_save()

    async def async_set_presence(self, box_id: str, entity_id: str | None) -> None:
        """Set or clear the entity that tells whether a Toniebox 1 is in the network."""
        if entity_id is None:
            self.presence.pop(box_id, None)
        elif entity_id.startswith(_PREFIXES):
            self.presence[box_id] = entity_id
        else:
            raise ValueError(entity_id)
        await self.async_save()

    def set_cloud_check(self, report: dict[str, Any]) -> None:
        """Keep what the last check of the cloud's interface found; written after a short delay."""
        self.cloud_check = report
        self._store.async_delay_save(self._data, 2)

    def set_repeat(self, box_id: str, mode: str | None, tonie_id: str | None = None) -> None:
        """Keep or drop the repeat of the figure on a box; written after a short delay."""
        if mode is None or tonie_id is None:
            if self.repeat.pop(box_id, None) is None:
                return
        else:
            self.repeat[box_id] = (mode, tonie_id)
        self._store.async_delay_save(self._data, 2)

    def presence_lag(self, box_id: str) -> int:
        """Return the minutes taken off each stretch of active time of a Toniebox 1."""
        return self._presence_lag.get(box_id, DEFAULT_PRESENCE_LAG)

    async def async_set_presence_lag(self, box_id: str, minutes: int) -> None:
        """Set the minutes taken off each stretch of active time of a Toniebox 1."""
        if not PRESENCE_LAG[0] <= minutes <= PRESENCE_LAG[1]:
            raise ValueError(minutes)
        self._presence_lag[box_id] = minutes
        await self.async_save()

    def to_lock(self, tonies: list[Tonie]) -> list[Tonie]:
        """Return the new figures to lock now; the other new ones count as known at once.

        A figure to lock counts as known only once locking it worked (see
        locked), so a refused attempt is repeated with the next poll.
        """
        lockable = [t for t in tonies if t.kind in LOCKABLE]
        if not self._started:
            self._known = {t.id for t in lockable}
            self._started = True
            self._store.async_delay_save(self._data, 2)
            return []
        new = [t for t in lockable if t.id not in self._known]
        wanted = [t for t in new if self.auto_lock and not t.locked]
        settled = {t.id for t in new} - {t.id for t in wanted}
        if settled:
            self._known |= settled
            self._store.async_delay_save(self._data, 2)
        return wanted

    def locked(self, tonie_id: str) -> None:
        """Note that a new figure was locked."""
        self._known.add(tonie_id)
        self._store.async_delay_save(self._data, 2)

    async def async_save(self) -> None:
        """Write everything now."""
        await self._store.async_save(self._data())

    def _data(self) -> dict[str, Any]:
        return {
            "analytics": self.analytics,
            "auto_lock": self.auto_lock,
            "mark_read": self.mark_read,
            "analytics_days": self.analytics_days,
            "speech_engine": self.speech_engine,
            "voice": self.voice,
            "voice_language": self.voice_language,
            "fetch_max_mb": self.fetch_max_mb,
            "favourites_mode": self.favourites_mode,
            "cloud_check": self.cloud_check,
            "presence": self.presence,
            "presence_lag": self._presence_lag,
            "repeat": {
                box: {"mode": mode, "tonie": tonie} for box, (mode, tonie) in self.repeat.items()
            },
            "known": sorted(self._known),
        }
