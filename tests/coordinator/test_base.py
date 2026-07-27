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
    CONF_ENABLE_VM,
    DOMAIN,
    LOGGER,
)
from custom_components.mos.coordinator import MOSDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError


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


async def test_fetches_all_resources_by_default(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict],
) -> None:
    """With no options set, all resources are fetched; docker_containers gets a merged "state"."""
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
        "docker_containers": [
            {**mock_docker_containers[0], "state": "running"},
            {**mock_docker_containers[1], "state": "exited"},
        ],
        "vm_machines": mock_client.async_get_vm_machines.return_value,
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
            CONF_ENABLE_VM: False,
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
            CONF_ENABLE_VM: False,
        },
    )
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_services.assert_not_called()
    mock_client.async_get_disks.assert_not_called()
    mock_client.async_get_pools.assert_not_called()
    mock_client.async_get_lxc_containers.assert_not_called()
    mock_client.async_get_docker_containers.assert_not_called()
    mock_client.async_get_docker_engine_containers.assert_not_called()
    mock_client.async_get_vm_machines.assert_not_called()
    mock_client.async_get_osinfo.assert_called_once()

    assert coordinator.data["services"] == {}
    assert coordinator.data["disks"] == []
    assert coordinator.data["pools"] == []
    assert coordinator.data["lxc_containers"] == []
    assert coordinator.data["docker_containers"] == []
    assert coordinator.data["vm_machines"] == []


async def test_async_start_lxc_container_calls_client_and_updates_state_optimistically(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Starting a container calls the client's start endpoint and flips its local state, without polling."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_lxc_containers.reset_mock()

    await coordinator.async_start_lxc_container("webserver")

    mock_client.async_start_lxc_container.assert_called_once_with("webserver")
    mock_client.async_get_lxc_containers.assert_not_called()
    containers = {c["name"]: c["state"] for c in coordinator.data["lxc_containers"]}
    assert containers == {"database": "running", "webserver": "running"}


async def test_async_stop_lxc_container_calls_client_and_updates_state_optimistically(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Stopping a container calls the client's stop endpoint and flips its local state, without polling."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_lxc_containers.reset_mock()

    await coordinator.async_stop_lxc_container("database")

    mock_client.async_stop_lxc_container.assert_called_once_with("database")
    mock_client.async_get_lxc_containers.assert_not_called()
    containers = {c["name"]: c["state"] for c in coordinator.data["lxc_containers"]}
    assert containers == {"database": "stopped", "webserver": "stopped"}


async def test_async_start_docker_container_calls_client_and_updates_state_optimistically(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Starting a Docker container calls the client's start endpoint and flips its local state, without polling."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_docker_containers.reset_mock()

    await coordinator.async_start_docker_container("nginx")

    mock_client.async_start_docker_container.assert_called_once_with("nginx")
    mock_client.async_get_docker_containers.assert_not_called()
    containers = {c["name"]: c["state"] for c in coordinator.data["docker_containers"]}
    assert containers == {"PushBits": "running", "nginx": "running"}


async def test_async_stop_docker_container_calls_client_and_updates_state_optimistically(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Stopping a Docker container calls the client's stop endpoint and flips its local state, without polling."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_docker_containers.reset_mock()

    await coordinator.async_stop_docker_container("PushBits")

    mock_client.async_stop_docker_container.assert_called_once_with("PushBits")
    mock_client.async_get_docker_containers.assert_not_called()
    containers = {c["name"]: c["state"] for c in coordinator.data["docker_containers"]}
    assert containers == {"PushBits": "exited", "nginx": "exited"}


async def test_async_start_vm_machine_calls_client_and_refreshes(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Starting a VM calls the client's start endpoint and refreshes coordinator data."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_vm_machines.reset_mock()

    await coordinator.async_start_vm_machine("Test")

    mock_client.async_start_vm_machine.assert_called_once_with("Test")
    mock_client.async_get_vm_machines.assert_called_once()


async def test_async_stop_vm_machine_calls_client_and_refreshes(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Stopping a VM calls the client's stop endpoint and refreshes coordinator data."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    mock_client.async_get_vm_machines.reset_mock()

    await coordinator.async_stop_vm_machine("Test")

    mock_client.async_stop_vm_machine.assert_called_once_with("Test")
    mock_client.async_get_vm_machines.assert_called_once()


@pytest.mark.parametrize(
    ("permissions_scope", "resource"),
    [
        ({"mode": "readonly"}, "lxc"),
        ({"mode": "readonly"}, "docker"),
        ({"mode": "readonly"}, "vm"),
        ({"mode": "custom", "resources": {"lxc": "read"}}, "lxc"),
        ({"mode": "custom", "resources": {}}, "docker"),
        ({"mode": "custom", "resources": {"vm": "read"}}, "vm"),
    ],
)
async def test_write_actions_blocked_without_write_access(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    permissions_scope: dict,
    resource: str,
) -> None:
    """A token without write access to the resource is rejected before any API call."""
    mock_client.async_get_token_permissions.return_value = {"id": "1", "permissions": permissions_scope}
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()

    method = {
        "lxc": coordinator.async_start_lxc_container,
        "docker": coordinator.async_start_docker_container,
        "vm": coordinator.async_start_vm_machine,
    }[resource]

    with pytest.raises(HomeAssistantError):
        await method("some-item")

    mock_client.async_start_lxc_container.assert_not_called()
    mock_client.async_start_docker_container.assert_not_called()
    mock_client.async_start_vm_machine.assert_not_called()


async def test_write_action_allowed_with_custom_write_access(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A "custom" token with explicit write access to the resource is allowed through."""
    mock_client.async_get_token_permissions.return_value = {
        "id": "1",
        "permissions": {"mode": "custom", "resources": {"lxc": "write"}},
    }
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()

    await coordinator.async_start_lxc_container("webserver")

    mock_client.async_start_lxc_container.assert_called_once_with("webserver")


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
