"""Login and token renewal against the login server, without Home Assistant's integration."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import Mock

import aiohttp
import pytest
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker, AiohttpClientMockResponse
from yarl import URL

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.storybox_plus.cloud import (
    Auth,
    CloudAuthError,
    CloudConnectionError,
    CloudResponseError,
    TokenSet,
)
from custom_components.storybox_plus.cloud.auth import CLIENT_ID, EXPIRY_MARGIN, TOKEN_URL

from .conftest import EMAIL, JSON_HEADERS, PASSWORD


def token_body(
    access: str = "access-1", refresh: str | None = "refresh-1", **extra: Any
) -> dict[str, Any]:
    """Return the login server's answer."""
    body: dict[str, Any] = {
        "access_token": access,
        "expires_in": 300,
        "refresh_expires_in": 0,
        "token_type": "Bearer",
        "scope": "openid offline_access",
        **extra,
    }
    if refresh is not None:
        body["refresh_token"] = refresh
    return body


def forms(aioclient_mock: AiohttpClientMocker) -> list[dict[str, str]]:
    """Return the forms posted to the login server so far."""
    return [call[2] for call in aioclient_mock.mock_calls if call[1] == URL(TOKEN_URL)]


def _answer(status: int, body: Any, json: bool = True) -> AiohttpClientMockResponse:
    return AiohttpClientMockResponse(
        method="post",
        url=URL(TOKEN_URL),
        status=status,
        json=body if json else None,
        text=None if json else body,
        headers=JSON_HEADERS if json else {},
    )


@pytest.fixture
def session(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> aiohttp.ClientSession:
    """A client session whose requests the mocker answers."""
    return async_get_clientsession(hass)


async def test_login_offline_token(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """The login asks for an offline token; one request, no expiry of the refresh token."""
    aioclient_mock.post(TOKEN_URL, json=token_body(), headers=JSON_HEADERS)
    on_tokens = Mock()
    auth = Auth(session, on_tokens=on_tokens)
    before = time.time()
    tokens = await auth.async_login(EMAIL, PASSWORD)
    assert forms(aioclient_mock) == [
        {
            "client_id": CLIENT_ID,
            "grant_type": "password",
            "username": EMAIL,
            "password": PASSWORD,
            "scope": "openid offline_access",
        }
    ]
    assert tokens.access_token == "access-1"
    assert tokens.refresh_token == "refresh-1"
    assert tokens.refresh_expires_at is None
    assert tokens.scope == "openid offline_access"
    assert before + 300 <= tokens.expires_at <= time.time() + 300
    assert tokens.access_valid()
    assert auth.tokens is tokens
    assert auth.refresh_token == "refresh-1"
    on_tokens.assert_called_once_with(tokens)


async def test_login_falls_back_to_session_token(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """When offline tokens are refused the login is repeated with the plain scope."""

    async def answer(method: str, url: URL, data: dict[str, str]) -> AiohttpClientMockResponse:
        if "offline_access" in data["scope"]:
            return _answer(400, {"error": "invalid_scope"})
        return _answer(200, token_body(refresh_expires_in=1800, scope="openid"))

    aioclient_mock.post(TOKEN_URL, side_effect=answer)
    auth = Auth(session)
    tokens = await auth.async_login(EMAIL, PASSWORD)
    assert [f["scope"] for f in forms(aioclient_mock)] == ["openid offline_access", "openid"]
    assert tokens.refresh_expires_at is not None
    assert time.time() + 1700 < tokens.refresh_expires_at <= time.time() + 1800
    assert tokens.scope == "openid"


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (401, {"error": "invalid_grant", "error_description": "Invalid user credentials"}),
        (400, {"error": "invalid_grant"}),
        (401, {"error": "invalid_client"}),
    ],
)
async def test_login_refused(
    aioclient_mock: AiohttpClientMocker,
    session: aiohttp.ClientSession,
    status: int,
    body: dict[str, str],
) -> None:
    """Wrong credentials are an auth error; the password is never retried."""
    aioclient_mock.post(TOKEN_URL, status=status, json=body, headers=JSON_HEADERS)
    auth = Auth(session)
    with pytest.raises(CloudAuthError):
        await auth.async_login(EMAIL, "wrong")
    assert aioclient_mock.call_count == 1
    assert auth.tokens is None


async def test_login_other_client_error_is_retried_once(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """Any 400 that is no auth error counts as refused offline scope, then the error stands."""
    aioclient_mock.post(
        TOKEN_URL, status=400, json={"error": "invalid_request"}, headers=JSON_HEADERS
    )
    with pytest.raises(CloudResponseError) as err:
        await Auth(session).async_login(EMAIL, PASSWORD)
    assert err.value.status == 400
    assert "invalid_request" in str(err.value)
    assert aioclient_mock.call_count == 2


async def test_login_server_error_is_not_retried(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """A 500 from the login server is passed on at once."""
    aioclient_mock.post(TOKEN_URL, status=500, text="oops")
    with pytest.raises(CloudResponseError) as err:
        await Auth(session).async_login(EMAIL, PASSWORD)
    assert err.value.status == 500
    assert aioclient_mock.call_count == 1


async def test_refresh_rotates_and_reports_changes(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """A refresh keeps the newest refresh token; the callback runs only when it changes."""
    answers = iter(
        [
            token_body("access-1", "refresh-1"),
            token_body("access-2", "refresh-1"),
            token_body("access-3", None),
            token_body("access-4", "refresh-4"),
        ]
    )

    async def answer(method: str, url: URL, data: dict[str, str]) -> AiohttpClientMockResponse:
        return _answer(200, next(answers))

    aioclient_mock.post(TOKEN_URL, side_effect=answer)
    on_tokens = Mock()
    auth = Auth(session, "refresh-0", on_tokens=on_tokens)
    assert auth.refresh_token == "refresh-0"
    assert auth.tokens is None

    first = await auth.async_refresh()
    assert forms(aioclient_mock)[-1] == {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": "refresh-0",
    }
    assert first.refresh_token == "refresh-1"
    on_tokens.assert_called_once_with(first)

    second = await auth.async_refresh()
    assert forms(aioclient_mock)[-1]["refresh_token"] == "refresh-1"
    assert second.access_token == "access-2"
    assert on_tokens.call_count == 1

    third = await auth.async_refresh()
    assert third.refresh_token == "refresh-1"
    assert on_tokens.call_count == 1

    fourth = await auth.async_refresh()
    assert fourth.refresh_token == "refresh-4"
    assert auth.refresh_token == "refresh-4"
    assert on_tokens.call_count == 2


async def test_refresh_without_token_needs_login(session: aiohttp.ClientSession) -> None:
    """Without a refresh token nothing is asked of the server."""
    with pytest.raises(CloudAuthError):
        await Auth(session).async_refresh()
    with pytest.raises(CloudAuthError):
        await Auth(session, "").async_access_token()


async def test_refresh_refused(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """An expired or revoked refresh token is an auth error."""
    aioclient_mock.post(
        TOKEN_URL, status=400, json={"error": "invalid_grant"}, headers=JSON_HEADERS
    )
    auth = Auth(session, "refresh-old")
    with pytest.raises(CloudAuthError):
        await auth.async_refresh()
    assert auth.refresh_token == "refresh-old"


@pytest.mark.parametrize("exc", [TimeoutError(), aiohttp.ClientConnectionError("down")])
async def test_connection_errors(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession, exc: Exception
) -> None:
    """Timeouts and network errors become connection errors, never auth errors."""
    aioclient_mock.post(TOKEN_URL, exc=exc)
    with pytest.raises(CloudConnectionError):
        await Auth(session, "refresh-0").async_refresh()


@pytest.mark.parametrize(
    ("status", "body", "json"),
    [
        (200, "<html>maintenance</html>", False),
        (200, {"token_type": "Bearer"}, True),
        (200, {"access_token": 5}, True),
        (200, ["access_token"], True),
        (502, "<html>bad gateway</html>", False),
    ],
)
async def test_unusable_answers(
    aioclient_mock: AiohttpClientMocker,
    session: aiohttp.ClientSession,
    status: int,
    body: Any,
    json: bool,
) -> None:
    """Answers without a token are response errors that name the status."""
    if json:
        aioclient_mock.post(TOKEN_URL, status=status, json=body, headers=JSON_HEADERS)
    else:
        aioclient_mock.post(TOKEN_URL, status=status, text=body)
    with pytest.raises(CloudResponseError) as err:
        await Auth(session, "refresh-0").async_refresh()
    assert err.value.status == status


async def test_login_answer_without_refresh_token(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """A login that yields no refresh token is useless, as nothing could be kept."""
    aioclient_mock.post(TOKEN_URL, json=token_body(refresh=None), headers=JSON_HEADERS)
    with pytest.raises(CloudResponseError, match="without a refresh token"):
        await Auth(session).async_login(EMAIL, PASSWORD)


async def test_refresh_answer_without_refresh_token_keeps_the_old(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """A refresh that returns no new refresh token leaves the stored one in place."""
    aioclient_mock.post(TOKEN_URL, json=token_body(refresh=None), headers=JSON_HEADERS)
    on_tokens = Mock()
    auth = Auth(session, "refresh-0", on_tokens=on_tokens)
    tokens = await auth.async_refresh()
    assert tokens.refresh_token == "refresh-0"
    on_tokens.assert_not_called()


async def test_access_token_is_refreshed_only_when_needed(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """A valid access token is reused; one about to expire is renewed."""
    answers = iter([token_body("access-1", expires_in=EXPIRY_MARGIN), token_body("access-2")])

    async def answer(method: str, url: URL, data: dict[str, str]) -> AiohttpClientMockResponse:
        return _answer(200, next(answers))

    aioclient_mock.post(TOKEN_URL, side_effect=answer)
    auth = Auth(session, "refresh-0")
    assert await auth.async_access_token() == "access-1"
    # Within the margin the token counts as expired already
    assert await auth.async_access_token() == "access-2"
    assert await auth.async_access_token() == "access-2"
    assert aioclient_mock.call_count == 2


@pytest.mark.parametrize(
    ("expires_in", "refresh_expires_in", "expiry", "refresh_expiry"),
    [
        (300, 0, 300, None),
        (120, 1800, 120, 1800),
        (None, None, 300, None),
        ("600", "600", 300, None),
        (0, -1, 300, None),
        (True, 0, 300, None),
    ],
)
async def test_expiry_fields(
    aioclient_mock: AiohttpClientMocker,
    session: aiohttp.ClientSession,
    expires_in: Any,
    refresh_expires_in: Any,
    expiry: float,
    refresh_expiry: float | None,
) -> None:
    """Expiry fields are numbers of seconds; anything else means the default or no expiry."""
    body = token_body(expires_in=expires_in, refresh_expires_in=refresh_expires_in)
    aioclient_mock.post(TOKEN_URL, json=body, headers=JSON_HEADERS)
    now = time.time()
    tokens = await Auth(session, "refresh-0").async_refresh()
    assert tokens.expires_at == pytest.approx(now + expiry, abs=2)
    if refresh_expiry is None:
        assert tokens.refresh_expires_at is None
    else:
        assert tokens.refresh_expires_at == pytest.approx(now + refresh_expiry, abs=2)


async def test_scope_field(
    aioclient_mock: AiohttpClientMocker, session: aiohttp.ClientSession
) -> None:
    """A scope that is no text is dropped."""
    aioclient_mock.post(TOKEN_URL, json=token_body(scope=["openid"]), headers=JSON_HEADERS)
    tokens = await Auth(session, "refresh-0").async_refresh()
    assert tokens.scope is None


def test_token_set_validity() -> None:
    """An access token is good until the margin before its expiry."""
    tokens = TokenSet("a", "r", expires_at=1000.0, refresh_expires_at=None)
    assert tokens.access_expires_in(now=900.0) == 100.0
    assert tokens.access_valid(now=1000.0 - EXPIRY_MARGIN - 1)
    assert not tokens.access_valid(now=1000.0 - EXPIRY_MARGIN)
    assert not tokens.access_valid(now=2000.0)
    assert tokens.access_expires_in() < 0
