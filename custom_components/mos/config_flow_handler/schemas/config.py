"""
Config flow schemas.

Schemas for the main configuration flow steps:
- User setup
- Reconfiguration
- Reauthentication
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.mos.const import CONF_API_TOKEN, DEFAULT_SSL, DEFAULT_VERIFY_SSL
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.helpers import selector


def _host_fields(defaults: Mapping[str, Any]) -> dict[Any, Any]:
    """Return the connection fields shared across setup and reconfigure."""
    return {
        vol.Required(
            CONF_HOST,
            default=defaults.get(CONF_HOST, vol.UNDEFINED),
        ): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT,
            ),
        ),
        vol.Required(CONF_API_TOKEN): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.PASSWORD,
            ),
        ),
        vol.Optional(
            CONF_PORT,
            default=defaults.get(CONF_PORT, vol.UNDEFINED),
        ): vol.All(
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=65535,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Coerce(int),
        ),
        vol.Optional(
            CONF_SSL,
            default=defaults.get(CONF_SSL, DEFAULT_SSL),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_VERIFY_SSL,
            default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        ): selector.BooleanSelector(),
    }


def get_user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for user step (initial setup).

    Includes a required friendly name that becomes the entry's stable identity
    (unique id and title), independent of the host. It is only offered here, not
    on reconfigure, so the identity never drifts.

    Args:
        defaults: Optional dictionary of default values to pre-populate the form.

    Returns:
        Voluptuous schema for the connection details.

    """
    defaults = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_NAME,
            default=defaults.get(CONF_NAME, vol.UNDEFINED),
        ): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT,
            ),
        ),
    }
    fields.update(_host_fields(defaults))
    return vol.Schema(fields)


def get_reconfigure_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """
    Get schema for reconfigure step.

    Args:
        defaults: Current values to pre-fill in the form.

    Returns:
        Voluptuous schema for reconfiguration.

    """
    return vol.Schema(_host_fields(defaults or {}))


def get_reauth_schema() -> vol.Schema:
    """
    Get schema for reauthentication step (token only).

    Returns:
        Voluptuous schema for reauthentication.

    """
    return vol.Schema(
        {
            vol.Required(CONF_API_TOKEN): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                ),
            ),
        },
    )


__all__ = [
    "get_reauth_schema",
    "get_reconfigure_schema",
    "get_user_schema",
]
