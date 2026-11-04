"""Config flow for Storybox Plus: a login that leaves only a token behind."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import probatio

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .cloud import Auth, CloudAuthError, CloudClient, CloudConnectionError, CloudError
from .const import CONF_ANALYTICS, CONF_REFRESH_TOKEN, CONF_USER_ID, DEFAULT_ANALYTICS, DOMAIN
from .coordinator import StoryboxConfigEntry

LOGIN_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        probatio.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
        ),
    }
)


class StoryboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a cloud account."""

    VERSION = 1

    async def _async_login(self, email: str, password: str) -> tuple[str, str, str]:
        """Log in once; return the account ID, the refresh token and a title."""
        session = async_get_clientsession(self.hass)
        auth = Auth(session)
        await auth.async_login(email, password)
        client = CloudClient(session, auth)
        user_id = await client.async_user_id()
        households = await client.async_households()
        title = households[0].name if len(households) == 1 else "Toniebox"
        assert auth.refresh_token is not None
        return user_id, auth.refresh_token, title

    async def _async_try(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> tuple[str, str, str] | None:
        try:
            return await self._async_login(
                user_input[CONF_EMAIL].strip(), user_input[CONF_PASSWORD]
            )
        except CloudAuthError:
            errors["base"] = "invalid_auth"
        except CloudConnectionError:
            errors["base"] = "cannot_connect"
        except CloudError:
            errors["base"] = "unknown"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for e-mail and password; only the resulting token is kept."""
        errors: dict[str, str] = {}
        if user_input is not None and (result := await self._async_try(user_input, errors)):
            user_id, refresh_token, title = result
            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=title, data={CONF_REFRESH_TOKEN: refresh_token, CONF_USER_ID: user_id}
            )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                LOGIN_SCHEMA, {CONF_EMAIL: (user_input or {}).get(CONF_EMAIL)}
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The cloud no longer accepts the token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the login again; it must be the same account."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None and (result := await self._async_try(user_input, errors)):
            user_id, refresh_token, _ = result
            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(
                entry, data_updates={CONF_REFRESH_TOKEN: refresh_token, CONF_USER_ID: user_id}
            )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                LOGIN_SCHEMA, {CONF_EMAIL: (user_input or {}).get(CONF_EMAIL)}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: StoryboxConfigEntry) -> OptionsFlowHandler:
        """Return the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlowWithReload):
    """Whether listening time is counted."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the options."""
        if user_input is not None:
            return self.async_create_entry(data={CONF_ANALYTICS: bool(user_input[CONF_ANALYTICS])})
        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_ANALYTICS,
                        default=self.config_entry.options.get(CONF_ANALYTICS, DEFAULT_ANALYTICS),
                    ): BooleanSelector()
                }
            ),
        )
