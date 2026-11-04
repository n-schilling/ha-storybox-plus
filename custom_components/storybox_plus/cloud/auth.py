"""Login and tokens.

The cloud uses Keycloak. A login with e-mail and password returns an access
token (valid a few minutes) and a refresh token. Only the refresh token is
kept: it renews the access token and is itself renewed with every refresh,
so the password is never needed again.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
import time
from typing import Any

import aiohttp

from .errors import CloudAuthError, CloudConnectionError, CloudResponseError

_LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://login.tonies.com/auth/realms/tonies/protocol/openid-connect/token"
CLIENT_ID = "meine-tonies"
# An offline token (scope offline_access) does not expire while unused; the
# login tries it first and falls back to a plain session if it is refused.
SCOPE_OFFLINE = "openid offline_access"
SCOPE_ONLINE = "openid"
# Seconds before expiry at which an access token counts as expired
EXPIRY_MARGIN = 30
TIMEOUT = aiohttp.ClientTimeout(total=30)

_AUTH_ERRORS = frozenset(
    {"invalid_grant", "invalid_client", "unauthorized_client", "invalid_token"}
)


@dataclass(frozen=True, slots=True)
class TokenSet:
    """The tokens of one session; times are Unix seconds."""

    access_token: str
    refresh_token: str
    expires_at: float
    # None: the refresh token does not expire while unused (offline token)
    refresh_expires_at: float | None
    scope: str | None = None

    def access_expires_in(self, now: float | None = None) -> float:
        """Return the seconds until the access token expires."""
        return self.expires_at - (time.time() if now is None else now)

    def access_valid(self, now: float | None = None) -> bool:
        """Return whether the access token is good for a request now."""
        return self.access_expires_in(now) > EXPIRY_MARGIN


class Auth:
    """Holds the tokens of one account and renews them."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        refresh_token: str | None = None,
        *,
        on_tokens: Callable[[TokenSet], None] | None = None,
        token_url: str = TOKEN_URL,
    ) -> None:
        """Start with a stored refresh token, or without tokens before a login."""
        self._session = session
        self._refresh_token = refresh_token
        self._tokens: TokenSet | None = None
        self._on_tokens = on_tokens
        self._token_url = token_url
        self._lock = asyncio.Lock()

    @property
    def tokens(self) -> TokenSet | None:
        """Return the current tokens, if any."""
        return self._tokens

    @property
    def refresh_token(self) -> str | None:
        """Return the newest refresh token."""
        return self._refresh_token

    async def async_login(self, email: str, password: str) -> TokenSet:
        """Log in with the password once; the result holds the refresh token to keep."""
        base = {"client_id": CLIENT_ID, "grant_type": "password"}
        try:
            tokens = await self._async_token_request(
                {**base, "username": email, "password": password, "scope": SCOPE_OFFLINE}
            )
        except CloudResponseError as err:
            if err.status not in (400, 401):
                raise
            # A client that is not allowed offline tokens answers "invalid_scope"
            _LOGGER.debug("Offline token refused (%s), logging in without it", err)
            tokens = await self._async_token_request(
                {**base, "username": email, "password": password, "scope": SCOPE_ONLINE}
            )
        return tokens

    async def async_refresh(self) -> TokenSet:
        """Get a new access token with the refresh token."""
        async with self._lock:
            return await self._async_refresh_locked()

    async def async_access_token(self) -> str:
        """Return a valid access token, refreshing when needed."""
        async with self._lock:
            if self._tokens is not None and self._tokens.access_valid():
                return self._tokens.access_token
            return (await self._async_refresh_locked()).access_token

    async def _async_refresh_locked(self) -> TokenSet:
        if not self._refresh_token:
            raise CloudAuthError("No refresh token, a new login is needed")
        return await self._async_token_request(
            {
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            }
        )

    async def _async_token_request(self, form: dict[str, str]) -> TokenSet:
        try:
            async with self._session.post(self._token_url, data=form, timeout=TIMEOUT) as resp:
                body: Any = None
                if resp.content_type == "application/json":
                    body = await resp.json()
                if resp.status != 200:
                    error = body.get("error") if isinstance(body, dict) else None
                    if resp.status in (400, 401) and error in _AUTH_ERRORS:
                        raise CloudAuthError(f"Login refused ({error})")
                    raise CloudResponseError(
                        f"Token endpoint answered {resp.status}" + (f" ({error})" if error else ""),
                        resp.status,
                    )
        except TimeoutError as err:
            raise CloudConnectionError("Timeout while talking to the login server") from err
        except aiohttp.ClientError as err:
            raise CloudConnectionError(
                f"Cannot reach the login server: {type(err).__name__}"
            ) from err
        if not isinstance(body, dict) or not isinstance(body.get("access_token"), str):
            raise CloudResponseError("Token endpoint answered without a token", 200)
        now = time.time()
        refresh_token = body.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            refresh_token = self._refresh_token
        if not refresh_token:
            raise CloudResponseError("Token endpoint answered without a refresh token", 200)
        refresh_expires_in = body.get("refresh_expires_in")
        tokens = TokenSet(
            access_token=body["access_token"],
            refresh_token=refresh_token,
            expires_at=now + _seconds(body.get("expires_in"), 300),
            refresh_expires_at=(
                None
                if isinstance(refresh_expires_in, bool)
                or not isinstance(refresh_expires_in, int | float)
                or refresh_expires_in <= 0
                else now + float(refresh_expires_in)
            ),
            scope=body.get("scope") if isinstance(body.get("scope"), str) else None,
        )
        changed = tokens.refresh_token != self._refresh_token
        self._tokens = tokens
        self._refresh_token = tokens.refresh_token
        if changed and self._on_tokens is not None:
            self._on_tokens(tokens)
        return tokens


def _seconds(value: Any, default: float) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool) and value > 0:
        return float(value)
    return default
