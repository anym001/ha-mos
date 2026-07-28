"""Tests for MOSDataUpdateCoordinator's conditional fetching and error mapping."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientCommunicationError
from custom_components.mos.const import (
    AUTH_FAILURE_GRACE_PERIOD,
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
from homeassistant.helpers.update_coordinator import UpdateFailed


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


async def test_authentication_error_during_setup_is_retryable_within_grace_period(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """Setup gets the same grace period as a running entry.

    A Home Assistant restart or an entry reload can land in exactly the window
    where a rebooting server rejects a still-valid token; escalating there would
    reintroduce the spurious reauth prompt the grace period exists to prevent.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # async_config_entry_first_refresh turns UpdateFailed into ConfigEntryNotReady,
    # so Home Assistant retries setup with backoff instead of asking for a token.
    with pytest.raises(ConfigEntryNotReady):
        await coordinator.async_config_entry_first_refresh()


async def test_auth_failure_streak_survives_a_new_coordinator(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """The grace period is enforced across setup retries, which build a fresh coordinator.

    Home Assistant discards the coordinator when setup fails, so a streak tracked
    on the instance would reset on every retry and never escalate - the entry
    would retry setup forever instead of ever asking for a new token.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)

    with pytest.raises(ConfigEntryNotReady):
        await _make_coordinator(hass, mock_client, entry).async_config_entry_first_refresh()

    advance_auth_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)

    # A brand new coordinator for the same entry still sees the ongoing streak.
    with pytest.raises(ConfigEntryAuthFailed):
        await _make_coordinator(hass, mock_client, entry).async_config_entry_first_refresh()


async def test_authentication_error_stays_retryable_within_grace_period(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """At runtime, auth failures keep retrying for the whole grace period, not reauth.

    Uses a controllable clock so the test is independent of the scan interval and
    of AUTH_FAILURE_GRACE_PERIOD's exact value: even many failures spanning almost
    the entire grace period must not escalate to reauth.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    grace = AUTH_FAILURE_GRACE_PERIOD.total_seconds()
    # Poll repeatedly, advancing time up to just before the grace period elapses.
    for _ in range(10):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        advance_auth_clock(grace / 20)  # stays strictly below `grace` across 10 steps


async def test_authentication_error_triggers_reauth_after_grace_period(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """At runtime, auth rejection sustained past the grace period escalates to reauth."""
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # First failure starts the clock - still retryable.
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Jump past the grace period; the next failure now escalates.
    advance_auth_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_auth_failure_timer_resets_after_success(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """A successful poll clears the streak, so the grace period restarts from zero."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # Fail, then recover well before the grace period would elapse.
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._auth_failure_since is not None

    mock_client.async_get_osinfo.side_effect = None
    await coordinator._async_update_data()
    assert coordinator._auth_failure_since is None

    # A later failure - even past the original grace window - starts a fresh timer.
    advance_auth_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_communication_error_resets_auth_failure_timer(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_auth_clock: Callable[[float], None],
) -> None:
    """A flapping server (auth errors interleaved with unreachability) never reauths."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # Well over the grace period elapses in total, but each auth failure is
    # interrupted by a connection error that resets the timer.
    for _ in range(10):
        mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._auth_failure_since is not None

        mock_client.async_get_osinfo.side_effect = MOSApiClientCommunicationError("down")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._auth_failure_since is None

        advance_auth_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds())


async def test_communication_error_is_retryable(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """A communication error is mapped to UpdateFailed, which is retryable, not fatal."""
    mock_client.async_get_services.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(ConfigEntryNotReady):
        await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is False
