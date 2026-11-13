"""The IDs of devices and entities, each within its account.

Members of one household each sign in with their own account, and every
account sees the household's boxes. So a box's device and entities carry
the config entry in their IDs: two entries that share a box each get their
own device and entities instead of colliding. The entry ID is used rather
than the account's UUID, which is the user name of the push channel.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN


def box_unique_id(entry: ConfigEntry, box_id: str, key: str | None = None) -> str:
    """Return the unique ID of a box's entity; key None is the box's main entity."""
    base = f"{entry.entry_id}_{box_id}"
    return f"{base}_{key}" if key else base


def box_identifier(entry: ConfigEntry, box_id: str) -> tuple[str, str]:
    """Return the identifier of a box's device."""
    return (DOMAIN, f"{entry.entry_id}_{box_id}")


def account_identifier(entry: ConfigEntry) -> tuple[str, str]:
    """Return the identifier of the account's own device."""
    return (DOMAIN, entry.entry_id)


def box_of(entry: ConfigEntry, identifiers: set[tuple[str, str]]) -> str | None:
    """Return the box a device of this entry stands for; None for the account's device."""
    prefix = f"{entry.entry_id}_"
    for domain, value in identifiers:
        if domain == DOMAIN and value.startswith(prefix):
            return value.removeprefix(prefix)
    return None
