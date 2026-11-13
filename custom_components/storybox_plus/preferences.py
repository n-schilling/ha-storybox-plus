"""The account's preferences from the page's settings tab, and which figures were locked.

Two preferences, each per account:

- auto_lock (on by default): a bought figure or disc that is new in the
  account is locked to the household once, so it cannot be claimed into
  another one. Unlocking it on the page or in the app is final: a figure is
  looked at only the first time it shows up. Switched off, new figures are
  noted without being locked, so switching it on later touches only figures
  that come after.
- mark_read (off by default): a notification of the cloud is marked as read
  there once it was passed on, so the app shows it no more.

The figures that were already in the account when the integration first ran
count as known: whether they are locked stays as it was.
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.storage import Store

from .cloud import Tonie, TonieKind

DEFAULT_AUTO_LOCK = True
DEFAULT_MARK_READ = False
LOCKABLE = frozenset({TonieKind.CONTENT, TonieKind.DISC})


class Preferences:
    """The preferences of one account and the figures looked at for locking."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start with the defaults; async_load reads the store."""
        self._store = store
        self.auto_lock = DEFAULT_AUTO_LOCK
        self.mark_read = DEFAULT_MARK_READ
        self._known: set[str] = set()
        # None until the figures of the first run were taken as known
        self._started = False

    async def async_load(self) -> None:
        """Read the store."""
        raw = await self._store.async_load()
        if not isinstance(raw, dict):
            return
        if isinstance(raw.get("auto_lock"), bool):
            self.auto_lock = raw["auto_lock"]
        if isinstance(raw.get("mark_read"), bool):
            self.mark_read = raw["mark_read"]
        known = raw.get("known")
        if isinstance(known, list):
            self._known = {k for k in known if isinstance(k, str)}
            self._started = True

    def as_dict(self) -> dict[str, Any]:
        """For the page."""
        return {"auto_lock": self.auto_lock, "mark_read": self.mark_read}

    async def async_set(self, auto_lock: bool | None, mark_read: bool | None) -> None:
        """Change the given preferences."""
        if auto_lock is not None:
            self.auto_lock = auto_lock
        if mark_read is not None:
            self.mark_read = mark_read
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
            "auto_lock": self.auto_lock,
            "mark_read": self.mark_read,
            "known": sorted(self._known),
        }
