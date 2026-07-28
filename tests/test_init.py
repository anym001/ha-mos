"""Tests for integration setup, unload, and reload."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientCommunicationError
from custom_components.mos.const import CONF_ENABLE_DISKS, MIN_SCAN_INTERVAL
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant


async def test_setup_entry_success(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_osinfo: dict[str, Any],
) -> None:
    """The config entry loads and the coordinator holds all fetched resources."""
    assert setup_integration.state is ConfigEntryState.LOADED

    coordinator = setup_integration.runtime_data.coordinator
    assert coordinator.data["osinfo"] == mock_osinfo
    assert "services" in coordinator.data
    assert "disks" in coordinator.data
    assert "pools" in coordinator.data


async def test_setup_entry_auth_failure_triggers_reauth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """An authentication error during setup aborts setup and starts a reauth flow."""
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress_by_handler("mos")
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_setup_entry_connection_failure_retries(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A communication error during setup is retried, not treated as fatal."""
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_osinfo.side_effect = MOSApiClientCommunicationError("timeout")

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Unloading the config entry tears it down cleanly."""
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.NOT_LOADED


async def test_options_update_reloads_entry(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Changing options triggers a full reload that picks up the new options."""
    assert setup_integration.state is ConfigEntryState.LOADED

    hass.config_entries.async_update_entry(
        setup_integration,
        options={CONF_ENABLE_DISKS: False},
    )
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.LOADED
    coordinator = setup_integration.runtime_data.coordinator
    assert coordinator.data["disks"] == []


async def test_scan_interval_below_minimum_is_clamped(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """An entry stored with a scan interval below the current minimum is clamped, not honored.

    Older entries can carry a value saved before MIN_SCAN_INTERVAL was raised;
    the coordinator must not poll faster than the current minimum allows.
    """
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_SCAN_INTERVAL: 10},
    )

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator.update_interval == timedelta(seconds=MIN_SCAN_INTERVAL)
