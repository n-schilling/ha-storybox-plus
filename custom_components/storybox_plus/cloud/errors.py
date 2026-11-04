"""Errors of the cloud client.

Messages never carry credentials, tokens or response bodies: they end up in
Home Assistant's log and in issues.
"""

from __future__ import annotations


class CloudError(Exception):
    """The cloud did not do what was asked."""


class CloudAuthError(CloudError):
    """The login was refused or the token is no longer valid."""


class CloudConnectionError(CloudError):
    """The cloud could not be reached."""


class CloudResponseError(CloudError):
    """The cloud answered with an error or with an unexpected body."""

    def __init__(self, message: str, status: int | None = None) -> None:
        """Keep the HTTP status, the message names it."""
        super().__init__(message)
        self.status = status
