"""Notifications of the cloud, passed on to Home Assistant once each.

The cloud keeps notifications for the account (a figure whose conversion
failed, an invitation, news) that only the app shows. The integration reads
them with every poll and fires each unread one once on an event entity; an
automation decides where it goes. Broadcasts to all users count the same.

Which ones were passed on is kept in the store, so a restart repeats none;
notifications the cloud no longer lists are forgotten there. Nothing in the
cloud changes: a notification stays unread in the app.
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.storage import Store

from .cloud import CloudNotice


class CloudNotices:
    """The notifications of one account that were passed on already."""

    def __init__(self, store: Store[dict[str, Any]]) -> None:
        """Start empty; async_load reads the store."""
        self._store = store
        self._seen: set[str] = set()

    async def async_load(self) -> None:
        """Read the IDs passed on in earlier runs."""
        raw = await self._store.async_load()
        seen = raw.get("seen") if isinstance(raw, dict) else None
        if isinstance(seen, list):
            self._seen = {s for s in seen if isinstance(s, str)}

    def new(self, notices: list[CloudNotice]) -> list[CloudNotice]:
        """Return the unread notifications not passed on yet, oldest first, and note them."""
        listed = {n.id for n in notices}
        fresh = [n for n in notices if n.id not in self._seen and not n.read]
        before = self._seen
        # Read ones count as passed on, so marking one unread in the app does not repeat it
        self._seen = (
            (self._seen & listed) | {n.id for n in notices if n.read} | {n.id for n in fresh}
        )
        if self._seen != before:
            self._store.async_delay_save(self._data, 2)
        # Oldest first; those without a time (broadcasts) after them, as listed
        fresh.sort(
            key=lambda n: (n.timestamp is None, n.timestamp.timestamp() if n.timestamp else 0)
        )
        return fresh

    async def async_save(self) -> None:
        """Write the IDs now."""
        await self._store.async_save(self._data())

    def _data(self) -> dict[str, Any]:
        return {"seen": sorted(self._seen)}
