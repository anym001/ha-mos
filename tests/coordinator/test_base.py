"""Tests for MOSDataUpdateCoordinator's conditional fetching and error mapping."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientCommunicationError
from custom_components.mos.const import (
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SERVICES,
    DOMAIN,
    LOGGER,
)
from custom_components.mos.coordinator import MOSDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady


def _make_coordinator(hass: HomeAssistant, client: AsyncMock, entry: MockConfigEntry) -> MOSDataUpdateCoordinator:
    """Build a coordinator wired to a fake config entry, without a full integration setup."""
    entry.runtime_data = SimpleNamespace(client=client)
    return MOSDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        config_entry=entry,
        update_interval=timedelta(seconds=30),
        always_update=False,
    )


async def test_fetches_all_resources_by_default(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """With no options set, all resources are fetched."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data == {
        "osinfo": mock_client.async_get_osinfo.return_value,
        "system_load": mock_client.async_get_system_load.return_value,
        "services": mock_client.async_get_services.return_value,
        "disks": mock_client.async_get_disks.return_value,
        "pools": mock_client.async_get_pools.return_value,
        "lxc_containers": mock_client.async_get_lxc_containers.return_value,
        "docker_containers": mock_client.async_get_docker_containers.return_value,
    }


async def test_system_load_is_always_fetched(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """system_load has no options-flow toggle - it is fetched unconditionally, like osinfo."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        state=ConfigEntryState.SETUP_IN_PROGRESS,
        options={
            CONF_ENABLE_DISKS: False,
            CONF_ENABLE_POOLS: False,
            CONF_ENABLE_SERVICES: False,
            CONF_ENABLE_LXC: False,
            CONF_ENABLE_DOCKER: False,
        },
    )
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_system_load.assert_called_once()
    assert coordinator.data["system_load"] == mock_client.async_get_system_load.return_value


async def test_disabled_categories_are_not_fetched(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """Disabled categories are skipped entirely and default to empty payloads."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        state=ConfigEntryState.SETUP_IN_PROGRESS,
        options={
            CONF_ENABLE_DISKS: False,
            CONF_ENABLE_POOLS: False,
            CONF_ENABLE_SERVICES: False,
            CONF_ENABLE_LXC: False,
            CONF_ENABLE_DOCKER: False,
        },
    )
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_services.assert_not_called()
    mock_client.async_get_disks.assert_not_called()
    mock_client.async_get_pools.assert_not_called()
    mock_client.async_get_lxc_containers.assert_not_called()
    mock_client.async_get_docker_containers.assert_not_called()
    mock_client.async_get_osinfo.assert_called_once()

    assert coordinator.data["services"] == {}
    assert coordinator.data["disks"] == []
    assert coordinator.data["pools"] == []
    assert coordinator.data["lxc_containers"] == []
    assert coordinator.data["docker_containers"] == []


async def test_async_start_lxc_container_calls_client_and_refreshes(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Starting a container calls the client's start endpoint and refreshes coordinator data."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_lxc_containers.reset_mock()

    await coordinator.async_start_lxc_container("webserver")

    mock_client.async_start_lxc_container.assert_called_once_with("webserver")
    mock_client.async_get_lxc_containers.assert_called_once()


async def test_async_stop_lxc_container_calls_client_and_refreshes(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Stopping a container calls the client's stop endpoint and refreshes coordinator data."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_lxc_containers.reset_mock()

    await coordinator.async_stop_lxc_container("database")

    mock_client.async_stop_lxc_container.assert_called_once_with("database")
    mock_client.async_get_lxc_containers.assert_called_once()


async def test_token_permissions_are_fetched_once_at_setup(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_token_permissions: dict,
) -> None:
    """Token permissions are introspected once during setup, not on every refresh."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_refresh()

    assert coordinator.token_permissions == mock_token_permissions
    mock_client.async_get_token_permissions.assert_called_once()


async def test_token_permissions_lookup_failure_does_not_block_setup(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A server that doesn't support token introspection yet (404) must not fail setup."""
    mock_client.async_get_token_permissions.side_effect = MOSApiClientCommunicationError("not found")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.token_permissions is None
    assert coordinator.last_update_success is True
    assert coordinator.data["osinfo"] == mock_client.async_get_osinfo.return_value


async def test_authentication_error_raises_config_entry_auth_failed(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """An authentication error is mapped to ConfigEntryAuthFailed to trigger reauth."""
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_config_entry_first_refresh()


async def test_communication_error_is_retryable(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """A communication error is mapped to UpdateFailed, which is retryable, not fatal."""
    mock_client.async_get_services.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(ConfigEntryNotReady):
        await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is False
