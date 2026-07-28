"""Tests for integration setup, unload, and reload."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientCommunicationError
from custom_components.mos.const import (
    AUTH_FAILURE_GRACE_PERIOD,
    AUTH_FAILURE_MIN_FAILURES,
    CONF_ENABLE_DISKS,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL, STATE_UNAVAILABLE
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


async def test_setup_entry_auth_failure_retries_before_asking_for_reauth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """A rejected token during setup is retried first, then escalated to reauth.

    Setting up while the server is rebooting (Home Assistant restart, entry
    reload) must not cost the user a valid token - but a token that stays
    rejected past the grace period has to reach the reauth prompt, even though
    every setup retry builds a fresh coordinator.
    """
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
        assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)

        for _ in range(AUTH_FAILURE_MIN_FAILURES - 2):
            await hass.config_entries.async_reload(mock_config_entry.entry_id)
            await hass.async_block_till_done()
            assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)

        advance_auth_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)
        await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
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


async def test_scan_interval_above_maximum_is_clamped(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A stored scan interval above the allowed maximum is clamped down to it."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_SCAN_INTERVAL: MAX_SCAN_INTERVAL * 10},
    )

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator.update_interval == timedelta(seconds=MAX_SCAN_INTERVAL)


async def test_runtime_auth_failure_keeps_entry_loaded_and_recovers(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """End-to-end: a transient 401 makes entities unavailable but starts no reauth flow.

    This is the user-visible shape of the fix - a rebooting server that briefly
    rejects a still-valid token must not tear the user into a reauth prompt, and
    entities must come back on their own once the server answers again.
    """
    coordinator = setup_integration.runtime_data.coordinator
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.LOADED
    assert coordinator.last_update_success is False
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert hass.states.get("sensor.sirius_disk_vda_power_status").state == STATE_UNAVAILABLE

    # Server is back: no reauth ever happened and the entities repopulate.
    mock_client.async_get_osinfo.side_effect = None
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is True
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert hass.states.get("sensor.sirius_disk_vda_power_status").state == "active"


async def test_runtime_auth_failure_starts_reauth_after_grace_period(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """End-to-end: a token that stays rejected past the grace period does start reauth.

    Guards the other half of the fix - deferring reauth must not mean never
    asking for a genuinely revoked or expired token.
    """
    coordinator = setup_integration.runtime_data.coordinator
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")

    for _ in range(AUTH_FAILURE_MIN_FAILURES - 1):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)

    advance_auth_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)
