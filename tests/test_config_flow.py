"""The config flow: a login that leaves only a token behind, reauth and options."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType

from custom_components.storybox_plus.cloud.auth import CLIENT_ID
from custom_components.storybox_plus.const import CONF_REFRESH_TOKEN, CONF_USER_ID, DOMAIN

from .conftest import EMAIL, HOUSEHOLD_NAME, PASSWORD, USER_ID, FakeCloud, PushChannels


async def _start(hass: HomeAssistant) -> FlowResult:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    return result


async def _login(
    hass: HomeAssistant, result: FlowResult, email: str = EMAIL, password: str = PASSWORD
) -> FlowResult:
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: email, CONF_PASSWORD: password}
    )


def _suggested_email(result: FlowResult) -> Any:
    marker = next(key for key in result["data_schema"].schema if key == CONF_EMAIL)
    return marker.description["suggested_value"]


async def test_user_creates_entry(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels
) -> None:
    """A login keeps the refresh token and the account ID, never the password."""
    result = await _login(hass, await _start(hass), email=f" {EMAIL} ")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == HOUSEHOLD_NAME
    assert result["data"] == {CONF_REFRESH_TOKEN: "refresh-main-1", CONF_USER_ID: USER_ID}
    assert CONF_PASSWORD not in result["data"]
    assert PASSWORD not in str(result["data"])
    assert result["result"].unique_id == USER_ID
    assert cloud.token_calls[0] == {
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": EMAIL,
        "password": PASSWORD,
        "scope": "openid offline_access",
    }
    await hass.async_block_till_done()
    assert result["result"].state is ConfigEntryState.LOADED


async def test_user_falls_back_to_session_token(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels
) -> None:
    """An account without offline tokens is logged in with the plain scope."""
    cloud.main.offline_tokens = False
    result = await _login(hass, await _start(hass))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [c["scope"] for c in cloud.token_calls[:2]] == ["openid offline_access", "openid"]


@pytest.mark.parametrize(
    "households",
    [[], [{"id": "hh1", "name": "Eins"}, {"id": "hh2", "name": "Zwei"}]],
)
async def test_title_without_a_single_household(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, households: list[dict[str, str]]
) -> None:
    """Only exactly one household names the entry; otherwise it is called Toniebox."""
    cloud.main.households = households
    result = await _login(hass, await _start(hass))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Toniebox"


async def test_user_already_configured(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, config_entry: MockConfigEntry
) -> None:
    """The same account cannot be added twice."""
    config_entry.add_to_hass(hass)
    result = await _login(hass, await _start(hass))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("trouble", "error"),
    [
        ("wrong_password", "invalid_auth"),
        ("unreachable", "cannot_connect"),
        ("api_error", "unknown"),
    ],
)
async def test_user_errors_and_recovery(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, trouble: str, error: str
) -> None:
    """Errors are shown on the form, which keeps the e-mail; the next try can succeed."""
    password = PASSWORD
    if trouble == "wrong_password":
        password = "wrong"
    elif trouble == "unreachable":
        cloud.unreachable = True
    else:
        cloud.main.rest_status = 500
    result = await _login(hass, await _start(hass), password=password)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert _suggested_email(result) == EMAIL

    cloud.unreachable = False
    cloud.main.rest_status = None
    result = await _login(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_reauth(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """A new login stores the new token and reloads the entry."""
    cloud.main.refresh_refused = True
    result = await setup_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await _login(hass, result, password="wrong")
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert _suggested_email(result) == EMAIL

    cloud.main.refresh_refused = False
    result = await _login(hass, result)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.LOADED
    assert setup_entry.data == {
        CONF_REFRESH_TOKEN: cloud.main.refresh_token,
        CONF_USER_ID: USER_ID,
    }
    assert "refresh-main-0" not in str(setup_entry.data)


async def test_reauth_with_another_account(
    hass: HomeAssistant, cloud: FakeCloud, push: PushChannels, setup_entry: MockConfigEntry
) -> None:
    """Signing in with a different account is refused; the entry keeps its own."""
    other = cloud.add_account("other", households=[{"id": "hh9", "name": "Andere"}])
    before = dict(setup_entry.data)
    result = await setup_entry.start_reauth_flow(hass)
    result = await _login(hass, result, email=other.email, password=other.password)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert setup_entry.data == before
    assert setup_entry.unique_id == USER_ID
