"""
Config flow for mos.

This module implements the main configuration flow including:
- Initial user setup
- Reconfiguration of existing entries
- Reauthentication flow

For more information:
https://developers.home-assistant.io/docs/config_entries_config_flow_handler
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from slugify import slugify

from custom_components.mos.config_flow_handler.schemas import get_reauth_schema, get_reconfigure_schema, get_user_schema
from custom_components.mos.config_flow_handler.validators import validate_connection
from custom_components.mos.const import CONF_API_TOKEN, DEFAULT_SSL, DEFAULT_VERIFY_SSL, DOMAIN, LOGGER
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.loader import async_get_loaded_integration

if TYPE_CHECKING:
    from custom_components.mos.config_flow_handler.options_flow import MOSOptionsFlow

# Map exception types to error keys for user-facing messages
ERROR_MAP = {
    "MOSApiClientAuthenticationError": "auth",
    "MOSApiClientCommunicationError": "connection",
}


class MOSConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for mos.

    Supported flows:
    - user: Initial setup via UI
    - reconfigure: Update connection details
    - reauth: Handle an invalid API token

    For more details:
    https://developers.home-assistant.io/docs/config_entries_config_flow_handler
    """

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MOSOptionsFlow:
        """
        Get the options flow for this handler.

        Returns:
            The options flow instance for modifying integration options.

        """
        from custom_components.mos.config_flow_handler.options_flow import MOSOptionsFlow  # noqa: PLC0415

        return MOSOptionsFlow()

    async def _validate(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate connection details and return the osinfo payload."""
        return await validate_connection(
            self.hass,
            host=user_input[CONF_HOST],
            token=user_input[CONF_API_TOKEN],
            use_ssl=user_input.get(CONF_SSL, DEFAULT_SSL),
            verify_ssl=user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            port=user_input.get(CONF_PORT),
        )

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle a flow initialized by the user.

        Args:
            user_input: The user input from the config flow form, or None for initial display.

        Returns:
            The config flow result, either showing a form or creating an entry.

        """
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                osinfo = await self._validate(user_input)
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                await self.async_set_unique_id(slugify(user_input[CONF_HOST]))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=osinfo.get("hostname") or user_input[CONF_HOST],
                    data=user_input,
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, "Integration documentation URL is not set in manifest.json"

        return self.async_show_form(
            step_id="user",
            data_schema=get_user_schema(user_input),
            errors=errors,
            description_placeholders={
                "documentation_url": integration.documentation,
            },
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reconfiguration of the integration.

        Allows users to update the connection details without removing and re-adding
        the integration.

        Args:
            user_input: The user input from the reconfigure form, or None for initial display.

        Returns:
            The config flow result, either showing a form or updating the entry.

        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._validate(user_input)
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_reconfigure_schema(entry.data),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reauthentication when the API token is invalid.

        This flow is automatically triggered when the coordinator catches
        an authentication error (ConfigEntryAuthFailed).

        Args:
            entry_data: The existing entry data (unused, per convention).

        Returns:
            The result of the reauth_confirm step.

        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """
        Handle reauthentication confirmation.

        Shows the reauthentication form and processes the updated API token.

        Args:
            user_input: The user input with the new token, or None for initial display.

        Returns:
            The config flow result, either showing a form or updating the entry.

        """
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            merged = {**entry.data, **user_input}
            try:
                await self._validate(merged)
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data=merged,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=get_reauth_schema(),
            errors=errors,
            description_placeholders={
                "host": entry.data.get(CONF_HOST, ""),
            },
        )

    def _map_exception_to_error(self, exception: Exception) -> str:
        """
        Map API exceptions to user-facing error keys.

        Args:
            exception: The exception that was raised.

        Returns:
            The error key for display in the config flow form.

        """
        LOGGER.warning("Error in config flow: %s", exception)
        exception_name = type(exception).__name__
        return ERROR_MAP.get(exception_name, "unknown")


__all__ = ["MOSConfigFlowHandler"]
