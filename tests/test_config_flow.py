"""Tests for the mos config flow and options flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientCommunicationError
from custom_components.mos.const import (
    CONF_API_TOKEN,
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SERVICES,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

USER_INPUT = {
    CONF_NAME: "Sirius",
    CONF_HOST: "10.0.1.30",
    CONF_API_TOKEN: "test-token",
    CONF_PORT: 80,
    CONF_SSL: False,
    CONF_VERIFY_SSL: True,
}


@pytest.fixture(autouse=True)
def mock_validate_connection(mock_osinfo: dict[str, Any], mock_client: AsyncMock) -> AsyncMock:
    """Patch the connection validator and the API client used during entry setup.

    A successful config flow schedules a real ``async_setup_entry`` for the new/updated
    entry in the background, which would otherwise construct a real MOSApiClient and hit
    the network. Both need mocking, not just the validator the flow itself calls.
    """
    with (
        patch(
            "custom_components.mos.config_flow_handler.config_flow.validate_connection",
            return_value=mock_osinfo,
        ) as mock_validate,
        patch("custom_components.mos.MOSApiClient", return_value=mock_client),
    ):
        yield mock_validate


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A valid user flow creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sirius"
    assert result["data"] == USER_INPUT


async def test_user_flow_stores_port_as_int(hass: HomeAssistant) -> None:
    """The port survives the NumberSelector as an int, not a float.

    Regression test: selector.NumberSelector always coerces to float, which
    previously ended up stored verbatim in entry.data and broke the API
    client's URL construction (e.g. "http://host:8080.0/...").
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**USER_INPUT, CONF_PORT: 8080},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == 8080
    assert isinstance(result["data"][CONF_PORT], int)


async def test_user_flow_duplicate_name_aborts(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A second entry with the same name is rejected as already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_auth_error(
    hass: HomeAssistant,
    mock_validate_connection: AsyncMock,
) -> None:
    """An invalid API token surfaces as an 'auth' form error."""
    mock_validate_connection.side_effect = MOSApiClientAuthenticationError("bad token")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}


async def test_user_flow_connection_error(
    hass: HomeAssistant,
    mock_validate_connection: AsyncMock,
) -> None:
    """An unreachable host surfaces as a 'connection' form error."""
    mock_validate_connection.side_effect = MOSApiClientCommunicationError("timeout")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "connection"}


async def test_reconfigure_flow_updates_entry(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Reconfigure updates the connection details without changing identity."""
    result = await setup_integration.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_data = {**USER_INPUT, CONF_HOST: "10.0.1.99"}
    del new_data[CONF_NAME]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        new_data,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert setup_integration.data[CONF_HOST] == "10.0.1.99"


async def test_reauth_flow_updates_token(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Reauth updates the stored API token."""
    result = await setup_integration.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_TOKEN: "new-token"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert setup_integration.data[CONF_API_TOKEN] == "new-token"


async def test_reauth_flow_invalid_token(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_validate_connection: AsyncMock,
) -> None:
    """An invalid token during reauth keeps the form open with an error."""
    mock_validate_connection.side_effect = MOSApiClientAuthenticationError("bad token")

    result = await setup_integration.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_TOKEN: "still-wrong"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}


async def test_options_flow_defaults_and_update(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The options flow pre-fills current values and stores updated ones."""
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 60,
            CONF_ENABLE_DISKS: False,
            CONF_ENABLE_POOLS: True,
            CONF_ENABLE_SERVICES: True,
            CONF_ENABLE_LXC: True,
            CONF_ENABLE_DOCKER: True,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_ENABLE_DISKS] is False
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 60
