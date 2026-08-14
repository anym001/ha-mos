"""Tests for MOSDataUpdateCoordinator's conditional fetching and error mapping."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import (
    MOSApiClientAuthenticationError,
    MOSApiClientCommunicationError,
    MOSApiClientNotFoundError,
    MOSApiClientPermissionError,
    MOSApiClientRateLimitError,
)
from custom_components.mos.const import (
    AUTH_FAILURE_GRACE_PERIOD,
    AUTH_FAILURE_MIN_FAILURES,
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SERVICES,
    CONF_ENABLE_VM,
    DOCKER_LABELS_KEPT,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    RESOURCE_STALE_GRACE_PERIOD,
    RESOURCE_STALE_MIN_FAILURES,
)
from custom_components.mos.coordinator import MOSDataUpdateCoordinator
from custom_components.mos.coordinator.base import DOCKER_ENGINE_MERGED_FIELDS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed


def _make_coordinator(hass: HomeAssistant, client: AsyncMock, entry: MockConfigEntry) -> MOSDataUpdateCoordinator:
    """Build a coordinator wired to a fake config entry, without a full integration setup.

    The entry is never loaded, so the ``async_on_unload(async_shutdown)`` hook
    Home Assistant registers for a real one never fires. A test that leaves a
    timer running - by adding a listener, which starts the refresh interval, or
    by calling ``async_request_refresh()``, which arms the debouncer - has to
    ``await coordinator.async_shutdown()`` itself, or teardown fails the test
    with "Lingering timer".
    """
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
    mock_docker_engine_containers: list[dict],
    mock_sensors: dict[str, list[dict]],
) -> None:
    """With no options set, all resources are fetched; docker_containers gets the engine and template data merged in.

    ``web_ui_url`` is None for both containers because this config entry carries
    no host to point a link at - the link is left out rather than guessed at.
    """
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
            {
                **mock_docker_containers[0],
                "state": "running",
                "container_id": "abc123",
                "health": "healthy",
                "labels": {
                    label: value
                    for label, value in mock_docker_engine_containers[0]["Labels"].items()
                    if label in DOCKER_LABELS_KEPT
                },
                "ports": mock_docker_engine_containers[0]["Ports"],
                "network_mode": "bridge",
                "icon_url": "https://raw.githubusercontent.com/pushbits/logo/main/logo.png",
                "web_ui_url": None,
            },
            {
                **mock_docker_containers[1],
                "state": "exited",
                "container_id": "def456",
                "health": "none",
                "labels": {},
                "ports": [],
                "network_mode": "bridge",
                "icon_url": "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/nginx.png",
                "web_ui_url": None,
            },
        ],
        "vm_machines": mock_client.async_get_vm_machines.return_value,
        "sensors": [{**item, "category": category} for category, items in mock_sensors.items() for item in items],
        "nut": mock_client.async_get_nut_status.return_value,
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
    await coordinator.async_shutdown()


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
    await coordinator.async_shutdown()


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
    advance_clock: Callable[[float], None],
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
    advance_clock: Callable[[float], None],
) -> None:
    """The grace period is enforced across setup retries, which build a fresh coordinator.

    Home Assistant discards the coordinator when setup fails, so a streak tracked
    on the instance would reset on every retry and never escalate - the entry
    would retry setup forever instead of ever asking for a new token.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)

    # Every retry gets a fresh coordinator, so the failure count can only reach
    # the escalation threshold if it is tracked per entry rather than per instance.
    for _ in range(AUTH_FAILURE_MIN_FAILURES - 1):
        with pytest.raises(ConfigEntryNotReady):
            await _make_coordinator(hass, mock_client, entry).async_config_entry_first_refresh()

    advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)

    # A brand new coordinator for the same entry still sees the ongoing streak.
    with pytest.raises(ConfigEntryAuthFailed):
        await _make_coordinator(hass, mock_client, entry).async_config_entry_first_refresh()


async def test_authentication_error_stays_retryable_within_grace_period(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
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
        advance_clock(grace / 20)  # stays strictly below `grace` across 10 steps


async def test_authentication_error_triggers_reauth_after_grace_period(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """At runtime, auth rejection sustained past the grace period escalates to reauth."""
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # Escalation needs both halves of the guard, so poll until one short of the
    # failure threshold - all still retryable.
    for _ in range(AUTH_FAILURE_MIN_FAILURES - 1):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    # Jump past the grace period; the next failure satisfies both and escalates.
    advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_long_scan_interval_does_not_collapse_the_grace_period(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """Two failed polls never trigger reauth, however far apart they are.

    The grace period is only checked when a poll fails, so on its own it shrinks
    to nothing at a long scan interval: at 600s the second failed poll is already
    ten minutes into the streak. That let two unlucky polls - a rate limiter, a
    proxy hiccup - produce a reauth prompt, which is exactly what users hit.
    AUTH_FAILURE_MIN_FAILURES is what keeps that from happening.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(2):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        # An interval far longer than the grace period, as a user polling every
        # 10 minutes (or the 3600s maximum) would have.
        advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() * 2)


async def test_auth_failure_timer_resets_after_success(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A successful poll clears the streak, so the grace period restarts from zero."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # Fail, then recover well before the grace period would elapse.
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._auth_failure_streak is not None

    mock_client.async_get_osinfo.side_effect = None
    await coordinator._async_update_data()
    assert coordinator._auth_failure_streak is None

    # A later failure - even past the original grace window - starts a fresh timer.
    advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_communication_error_resets_auth_failure_timer(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
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
        assert coordinator._auth_failure_streak is not None

        mock_client.async_get_osinfo.side_effect = MOSApiClientCommunicationError("down")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._auth_failure_streak is None

        advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds())


async def test_communication_error_on_required_resource_is_retryable(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A communication error on an always-fetched resource maps to UpdateFailed, not a fatal error."""
    mock_client.async_get_osinfo.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(ConfigEntryNotReady):
        await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is False


async def test_unreachable_server_still_fails_the_whole_poll(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """When every endpoint fails, the entry must go unavailable rather than serve stale data.

    Per-resource isolation of communication errors must not extend to a server
    that is simply down: the always-fetched resources fail along with everything
    else, and that is what still takes the cycle down.
    """
    for method in (
        mock_client.async_get_osinfo,
        mock_client.async_get_system_load,
        mock_client.async_get_services,
        mock_client.async_get_disks,
        mock_client.async_get_pools,
        mock_client.async_get_lxc_containers,
        mock_client.async_get_docker_containers,
        mock_client.async_get_docker_engine_containers,
        mock_client.async_get_vm_machines,
        mock_client.async_get_sensors,
    ):
        method.side_effect = MOSApiClientCommunicationError("host unreachable")

    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_communication_error_on_optional_resource_does_not_fail_the_poll(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """One flaky endpoint costs that resource, not the other nine.

    Before, the first communication error aborted the whole cycle, so a single
    slow or briefly broken endpoint left the integration with no data at all
    even though every other endpoint had answered fine.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data["osinfo"] == mock_client.async_get_osinfo.return_value
    assert coordinator.data["vm_machines"] == []


async def test_communication_error_retains_last_known_good_data(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_vm_machines: list[dict],
) -> None:
    """A resource that becomes unreachable keeps its previous data instead of emptying out.

    An empty list makes the dynamic-entity sync remove every device backed by
    that resource, so a passing timeout would otherwise make VMs and containers
    disappear and come back a poll later.
    """
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data["vm_machines"] == mock_vm_machines

    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    await coordinator._async_update_data()

    assert coordinator.last_update_success is True
    assert coordinator.data["vm_machines"] == mock_vm_machines
    assert coordinator.data["osinfo"] == mock_client.async_get_osinfo.return_value


async def test_unreachable_resource_is_reprobed_and_recovers(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A resource dropped by a communication error is retried, never permanently disabled."""
    mock_client.async_get_sensors.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data["sensors"] == []
    assert "sensors" not in coordinator.forbidden_resources

    await coordinator.async_refresh()
    assert mock_client.async_get_sensors.call_count == 2

    mock_client.async_get_sensors.side_effect = None
    await coordinator.async_refresh()
    assert coordinator.data["sensors"] != []


async def test_communication_error_on_optional_resource_never_triggers_reauth(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A permanently broken optional endpoint must never escalate to a reauth prompt."""
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(AUTH_FAILURE_MIN_FAILURES + 2):
        await coordinator._async_update_data()
        advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)

    assert coordinator._auth_failure_streak is None


async def test_denied_resource_is_dropped_without_failing_the_poll(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A 403 on one resource costs that resource, not the whole update.

    Before, gather() propagated the first exception, so a token scoped to
    everything-but-VMs produced no data at all - every poll died on the VM
    endpoint even though the other eight answered fine.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientPermissionError("no vm scope")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data["osinfo"] == mock_client.async_get_osinfo.return_value
    assert coordinator.data["vm_machines"] == []


async def test_scope_denial_stops_the_resource_being_requested_again(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A resource the server refuses by name is never asked for again.

    The client only raises a permission error when the server spelled out which
    resource the token may not read, so this is the token's scope talking, not a
    hiccup - retrying it every 30 seconds can only produce the same refusal.

    Seeding from the token's own permission list does not cover this: MOS
    enforces names it does not list. A custom-mode token on 0.5.x has no ``nut``
    key at all while ``/nut/status`` is still refused, and the resource was
    re-probed forever with nothing in the log to explain the missing entities.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientPermissionError("no permission for vm")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()
    assert mock_client.async_get_vm_machines.call_count == 1
    assert "vm_machines" in coordinator.forbidden_resources
    # The rest of the poll is unaffected - one denied resource is not an outage.
    assert coordinator.last_update_success is True

    await coordinator.async_refresh()
    assert mock_client.async_get_vm_machines.call_count == 1


async def test_scope_denial_settles_every_resource_under_the_same_scope(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """One refusal covers every resource MOS governs under that scope name.

    A MOS permission covers a whole first path segment, so "docker" denied means
    both the MOS container list and the raw Engine proxy are gone. Waiting for
    each to fail on its own would spend an extra request and an extra warning on
    an answer already known.
    """
    mock_client.async_get_docker_containers.side_effect = MOSApiClientPermissionError("no permission for docker")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert "docker_containers" in coordinator.forbidden_resources
    assert "docker_engine_containers" in coordinator.forbidden_resources
    # Resources under a different scope are untouched.
    assert "lxc_containers" not in coordinator.forbidden_resources


async def test_scope_denial_keeps_its_data_but_reports_it_unavailable(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_vm_machines: list[dict],
) -> None:
    """A resource denied while running keeps its entities and marks them unavailable.

    Dropping it would empty the list, and the dynamic-entity sync deletes a
    device the moment its resource list is empty - taking the recorder history,
    custom names and every automation referencing the entity_id with it, over a
    permission the user may well be about to grant back.

    Keeping the data without saying anything would be the other failure: values
    frozen at the moment the permission went away, still rendering as if they
    were current. So the data stays and the resource counts as stale.
    """
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # A good first poll establishes the last-known-good VM list.
    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data["vm_machines"] == mock_vm_machines

    mock_client.async_get_vm_machines.side_effect = MOSApiClientPermissionError("no permission for vm")
    await coordinator._async_update_data()

    assert coordinator.last_update_success is True
    assert coordinator.data["vm_machines"] == mock_vm_machines
    assert "vm_machines" in coordinator.stale_resources
    # Other resources keep updating normally.
    assert coordinator.data["osinfo"] == mock_client.async_get_osinfo.return_value


async def test_rate_limited_resource_is_transient_and_retained(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_lxc_containers: list[dict],
) -> None:
    """A 429 on one resource keeps its last-known data and never fails the whole poll."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data["lxc_containers"] == mock_lxc_containers

    mock_client.async_get_lxc_containers.side_effect = MOSApiClientRateLimitError("429")
    await coordinator._async_update_data()

    assert coordinator.last_update_success is True
    assert coordinator.data["lxc_containers"] == mock_lxc_containers
    assert "lxc_containers" not in coordinator.forbidden_resources


async def test_rate_limited_required_resource_fails_the_poll(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A 429 on an always-fetched resource fails the cycle (retryable), not a partial update."""
    mock_client.async_get_osinfo.side_effect = MOSApiClientRateLimitError("429")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_denied_resource_never_triggers_reauth(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A permanently denied resource must never escalate to a reauth prompt.

    This is the reported bug: 403 was treated as "invalid token", so a scoped
    token produced a reauth prompt, the user entered the same valid token, the
    flow validated it against /osinfo (which it *can* read) and succeeded - and
    the next poll asked again. Forever.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientPermissionError("no vm scope")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(AUTH_FAILURE_MIN_FAILURES + 2):
        await coordinator._async_update_data()
        advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)

    assert coordinator._auth_failure_streak is None


async def test_denied_required_resource_fails_the_update_without_reauth(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A 403 on an always-fetched resource is fatal for the poll, but still not a token problem."""
    mock_client.async_get_osinfo.side_effect = MOSApiClientPermissionError("no read scope")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(AUTH_FAILURE_MIN_FAILURES + 2):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)

    # Always-fetched resources keep being probed, so widening the token's scope
    # and reloading is enough to recover.
    assert mock_client.async_get_osinfo.call_count == AUTH_FAILURE_MIN_FAILURES + 2
    assert "osinfo" not in coordinator.forbidden_resources


async def test_denied_required_resource_names_the_mos_scope_not_the_data_key(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """The error tells the user to grant "mos", which is what the MOS web UI calls it.

    A custom token can set "mos" to "none", and osinfo is then refused on every
    poll. Naming the internal data key would send the user looking for an
    "osinfo" permission that does not exist.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientPermissionError("no read scope")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with pytest.raises(UpdateFailed) as error:
        await coordinator._async_update_data()

    assert error.value.translation_key == "insufficient_read_permission"
    assert error.value.translation_placeholders == {"resource": "mos"}


async def test_introspection_denied_by_scope_leaves_every_resource_probed(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A token denied "auth" cannot read its own scope, and must still set up.

    Losing introspection costs the pre-poll skip, nothing else: without a scope
    to consult every resource is treated as readable and the server decides,
    exactly as it does on a server too old to offer introspection at all.
    """
    mock_client.async_get_token_permissions.side_effect = MOSApiClientPermissionError("no auth scope")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.token_permissions is None
    assert coordinator.forbidden_resources == frozenset()
    assert coordinator.last_update_success is True
    mock_client.async_get_vm_machines.assert_called_once()


async def test_read_scope_is_honoured_before_the_first_poll(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A scope that explicitly denies a resource skips it without a doomed request."""
    mock_client.async_get_token_permissions.return_value = {
        "id": "1",
        "permissions": {"mode": "custom", "resources": {"vm": "none", "lxc": "read"}},
    }
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_vm_machines.assert_not_called()
    mock_client.async_get_lxc_containers.assert_called_once()
    assert coordinator.data["vm_machines"] == []


async def test_unknown_resource_names_in_scope_are_not_pre_denied(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A custom scope that simply omits a resource is still probed.

    A custom scope only lists what was configured, and a future MOS could rename
    a resource, so treating "absent" as "denied" would silently disable entities.
    Absent means "ask the server", and a 403 handles it from there.
    """
    mock_client.async_get_token_permissions.return_value = {
        "id": "1",
        "permissions": {"mode": "custom", "resources": {"lxc": "write"}},
    }
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_vm_machines.assert_called_once()
    mock_client.async_get_disks.assert_called_once()
    assert coordinator.forbidden_resources == frozenset()


async def test_denied_docker_engine_proxy_keeps_the_container_list(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict],
) -> None:
    """The Docker Engine proxy and the MOS container list are denied independently.

    Losing live running state should not cost the containers themselves. With no
    prior poll to carry a state from, the running-state is simply unknown (None).
    """
    mock_client.async_get_docker_engine_containers.side_effect = MOSApiClientPermissionError("no proxy scope")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is True
    containers = coordinator.data["docker_containers"]
    assert [container["name"] for container in containers] == [
        mock_docker_containers[0]["name"],
        mock_docker_containers[1]["name"],
    ]
    # Everything the proxy would have supplied is unknown, not invented - checked
    # against the merge's own field list so a newly merged field cannot quietly
    # skip this.
    assert all(container[field] is None for container in containers for field in DOCKER_ENGINE_MERGED_FIELDS)


async def test_only_known_container_labels_are_kept(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_docker_engine_containers: list[dict],
) -> None:
    """Docker labels are free-form, and this payload reaches the diagnostics download.

    Whatever an image author or a user puts on a container must not be carried
    into coordinator data just because it happened to ride along in the poll.
    """
    noisy = {
        **mock_docker_engine_containers[0],
        "Labels": {**mock_docker_engine_containers[0]["Labels"], "com.example.secret": "hunter2"},
    }
    mock_client.async_get_docker_engine_containers.return_value = [noisy, mock_docker_engine_containers[1]]
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    labels = coordinator.data["docker_containers"][0]["labels"]
    assert "com.example.secret" not in labels
    assert "mos.backend" not in labels
    assert labels["mos.webui"] == "http://[ADDRESS]:[PORT:8080]/"
    assert labels["org.opencontainers.image.title"] == "server"


async def test_denied_docker_engine_proxy_retains_last_known_state(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict],
) -> None:
    """A transient Engine-proxy 403 keeps the last-known running state per container.

    The engine payload is merged into ``docker_containers`` and then dropped
    every poll, so it never reaches the generic last-known-good retention. When
    the proxy briefly 403s while the container list still answers, each
    container must keep the ``state`` it had last poll instead of blanking to
    None and flapping the running binary sensors for a cycle.
    """
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    # A good first poll establishes the live running/exited state.
    await coordinator.async_config_entry_first_refresh()
    established = coordinator.data["docker_containers"]
    assert [container["state"] for container in established] == ["running", "exited"]

    # The next poll loses only the engine proxy; the container list still answers.
    mock_client.async_get_docker_engine_containers.side_effect = MOSApiClientPermissionError("transient 403")
    data = await coordinator._async_update_data()

    # Every engine-derived field is carried over, not just the running state:
    # blanking the health or the port mapping would flap those entities too.
    assert data["docker_containers"] == established


async def test_communication_error_wins_over_a_concurrent_auth_error(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A server answering some requests and dropping others is unstable, not unauthenticated.

    Treating the 401 as authoritative here would let a half-down server
    accumulate its way to a reauth prompt, which is the failure mode the grace
    period exists to prevent.
    """
    mock_client.async_get_osinfo.side_effect = MOSApiClientAuthenticationError("bad token")
    mock_client.async_get_disks.side_effect = MOSApiClientCommunicationError("down")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(AUTH_FAILURE_MIN_FAILURES + 2):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        advance_clock(AUTH_FAILURE_GRACE_PERIOD.total_seconds() + 1)

    assert coordinator._auth_failure_streak is None


async def test_resource_goes_stale_only_after_both_guards(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """Retained data stops counting as current only once duration *and* failure count are satisfied.

    Either half alone would misbehave across the 30 s - 3600 s interval range;
    see the commentary on RESOURCE_STALE_GRACE_PERIOD.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator._async_update_data()
    assert coordinator.stale_resources == frozenset()

    # Grace period has now elapsed, but only two polls have observed the failure.
    advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds() + 1)
    await coordinator._async_update_data()
    assert coordinator.stale_resources == frozenset()

    await coordinator._async_update_data()
    assert coordinator.stale_resources == frozenset({"vm_machines"})


async def test_failure_count_alone_does_not_mark_stale(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """Many failures in quick succession are a flaky endpoint, not a dead one.

    The clock fixture is requested but never advanced: without it the real
    monotonic clock would make this test depend on wall time.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(RESOURCE_STALE_MIN_FAILURES * 4):
        await coordinator._async_update_data()

    assert coordinator.stale_resources == frozenset()


async def test_long_scan_interval_is_bound_by_the_failure_count(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """At the 3600 s maximum interval the failure count decides, not the grace period.

    The second failed poll is already an hour into the streak, so the 15 minute
    grace period is long satisfied; requiring three observations is what stops
    two unlucky polls from taking a resource down. The threshold stretching to
    two hours here is intended - at that interval the data is never fresher than
    an hour anyway.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator._async_update_data()
    advance_clock(MAX_SCAN_INTERVAL)
    await coordinator._async_update_data()
    assert coordinator.stale_resources == frozenset()

    advance_clock(MAX_SCAN_INTERVAL)
    await coordinator._async_update_data()
    assert coordinator.stale_resources == frozenset({"vm_machines"})


async def test_healthy_polls_never_mark_anything_stale(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """The common case: however long the integration runs, a healthy server stales nothing.

    Guards the direction that matters most - a bug here would take entities
    unavailable on a perfectly working server.
    """
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(5):
        await coordinator._async_update_data()
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds() * 2)

    assert coordinator.stale_resources == frozenset()
    assert coordinator._degraded_resources == {}


async def test_recovery_clears_staleness_without_a_reload(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A resource that answers again drops both halves of the guard immediately."""
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(RESOURCE_STALE_MIN_FAILURES):
        await coordinator._async_update_data()
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds())
    assert coordinator.stale_resources == frozenset({"vm_machines"})

    mock_client.async_get_vm_machines.side_effect = None
    await coordinator._async_update_data()

    assert coordinator.stale_resources == frozenset()
    assert coordinator._degraded_resources == {}


async def test_server_outage_does_not_age_a_resource_into_staleness(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A whole-server outage must not silently push a resource past the threshold.

    While every endpoint is failing the poll aborts before per-resource
    bookkeeping is reached, so the elapsed timer would keep running against
    failures nobody counted. Requiring observed failures means the streak has to
    be rebuilt once the server answers again.
    """
    everything = (
        mock_client.async_get_osinfo,
        mock_client.async_get_system_load,
        mock_client.async_get_services,
        mock_client.async_get_disks,
        mock_client.async_get_pools,
        mock_client.async_get_lxc_containers,
        mock_client.async_get_docker_containers,
        mock_client.async_get_docker_engine_containers,
        mock_client.async_get_vm_machines,
        mock_client.async_get_sensors,
    )
    for method in everything:
        method.side_effect = MOSApiClientCommunicationError("host unreachable")

    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    for _ in range(RESOURCE_STALE_MIN_FAILURES + 2):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds())

    # Server is back, except for the one endpoint that is genuinely broken.
    for method in everything:
        method.side_effect = None
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")

    await coordinator._async_update_data()

    assert coordinator.stale_resources == frozenset()


async def test_stale_resource_keeps_serving_its_last_known_data(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_vm_machines: list[dict],
    advance_clock: Callable[[float], None],
) -> None:
    """Going stale changes availability only - the data is still carried forward.

    Dropping the resource instead would empty its list, and the dynamic-entity
    sync would delete the entities along with their registry entries, history
    and any automation referencing them.
    """
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_refresh()

    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    for _ in range(RESOURCE_STALE_MIN_FAILURES):
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds())
        await coordinator.async_refresh()

    assert coordinator.stale_resources == frozenset({"vm_machines"})
    assert coordinator.data["vm_machines"] == mock_vm_machines


async def test_listeners_are_notified_when_staleness_changes_without_data_changing(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """The transition to stale must reach entities even when the payload is byte-identical.

    The coordinator runs with ``always_update=False``, so Home Assistant only
    notifies listeners when ``previous_data != self.data``. A stale resource's
    data is retained *unchanged* by definition, so on a poll where nothing else
    happened to change, the built-in comparison suppresses the notification and
    entities would go on rendering as available with values that stopped
    updating - precisely the failure this mechanism exists to prevent.
    """
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_refresh()
    advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds() + 1)
    await coordinator.async_refresh()
    assert coordinator.stale_resources == frozenset()

    notifications: list[None] = []
    coordinator.async_add_listener(lambda: notifications.append(None))
    notifications.clear()
    payload_before = coordinator.data

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Premise of the test: this poll changed nothing but the staleness verdict.
    assert coordinator.data == payload_before
    assert coordinator.stale_resources == frozenset({"vm_machines"})
    assert notifications, "entities were never told the resource had gone stale"
    await coordinator.async_shutdown()


async def test_endpoint_the_server_does_not_have_is_reported_once_and_costs_nothing(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A 404 on a resource that never answered means "this MOS is older", not "something broke".

    The poll succeeds, the resource is simply left out, and the explanation is
    logged once rather than every poll - there is nothing for the user to fix.
    """
    mock_client.async_get_nut_status.side_effect = MOSApiClientNotFoundError("no such endpoint: /api/v1/nut/status")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with caplog.at_level(logging.INFO):
        await coordinator.async_config_entry_first_refresh()
        first_poll_messages = [record.message for record in caplog.records]
        caplog.clear()
        await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.unsupported_resources == frozenset({"nut"})
    assert coordinator.data["nut"] == {}
    # Not a failing resource: no staleness countdown, no degraded bookkeeping.
    assert coordinator.stale_resources == frozenset()
    assert coordinator._degraded_resources == {}

    assert any("has no endpoint for nut" in message for message in first_poll_messages)
    assert not [record for record in caplog.records if "has no endpoint" in record.message]


async def test_endpoint_added_by_a_server_update_starts_being_used(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_nut: dict[str, Any],
) -> None:
    """Once the server answers an endpoint it previously 404'd, its data is used again.

    This is what makes a MOS update bring the matching entities in on its own,
    without a reload.
    """
    mock_client.async_get_nut_status.side_effect = MOSApiClientNotFoundError("no such endpoint")
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()
    assert coordinator.unsupported_resources == frozenset({"nut"})

    mock_client.async_get_nut_status.side_effect = None
    await coordinator.async_refresh()

    assert coordinator.unsupported_resources == frozenset()
    assert coordinator.data["nut"] == mock_nut


async def test_endpoint_that_answered_before_is_treated_as_a_failure_not_as_missing(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_nut: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A 404 on a resource that used to answer is a regression, and warned about.

    Silently classifying it as unsupported would hide a removed or renamed
    endpoint and quietly freeze the entities' values instead.
    """
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_nut_status.side_effect = MOSApiClientNotFoundError("gone")
    with caplog.at_level(logging.WARNING):
        await coordinator.async_refresh()

    assert coordinator.unsupported_resources == frozenset()
    assert coordinator.data["nut"] == mock_nut
    assert any("although it answered before" in record.message for record in caplog.records)


# What MOS answers once NUT is switched on but the driver is not attached - the
# UPS is on a different machine, or usbhid-ups is not running. Kept verbatim,
# newlines included, because collapsing them is part of what is under test.
UPS_DRIVER_DOWN: dict[str, Any] = {
    "reachable": False,
    "name": "ups",
    "error": "Command failed: upsc ups@127.0.0.1:3493\nInit SSL without certificate database\nError: Driver not connected\n",
}

# What it answers with NUT switched off entirely: no UPS, and nothing to say
# about it.
UPS_NOT_CONFIGURED: dict[str, Any] = {"reachable": False, "name": None, "status": None}


async def test_a_ups_the_server_cannot_read_is_explained_once(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A configured-but-unreadable UPS is the one case with no entity to show it, so it is logged.

    Once, not every poll - and on a single line, since the server passes the
    failed command's multi-line output straight through.
    """
    mock_client.async_get_nut_status.return_value = UPS_DRIVER_DOWN
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with caplog.at_level(logging.WARNING):
        await coordinator.async_config_entry_first_refresh()
        first_poll = [record.getMessage() for record in caplog.records]
        caplog.clear()
        await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    reported = [message for message in first_poll if "cannot read it" in message]
    assert len(reported) == 1
    assert "Error: Driver not connected" in reported[0]
    assert "\n" not in reported[0]
    assert not [record for record in caplog.records if "cannot read it" in record.message]


async def test_a_server_without_a_ups_says_nothing(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No UPS configured is the normal case for most users, and must not produce a warning.

    The endpoint answers, it simply reports nothing attached and no error - the
    absence of ``error`` is what separates "nothing set up" from "set up and
    broken".
    """
    mock_client.async_get_nut_status.return_value = UPS_NOT_CONFIGURED
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    with caplog.at_level(logging.WARNING):
        await coordinator.async_config_entry_first_refresh()

    assert coordinator.data["nut"] == UPS_NOT_CONFIGURED
    assert not [record for record in caplog.records if "cannot read it" in record.message]


async def test_a_ups_that_breaks_again_is_reported_again(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_nut: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Recovering rearms the message, so a later failure is not swallowed by an old one."""
    mock_client.async_get_nut_status.return_value = UPS_DRIVER_DOWN
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)
    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_nut_status.return_value = mock_nut
    await coordinator.async_refresh()

    mock_client.async_get_nut_status.return_value = UPS_DRIVER_DOWN
    with caplog.at_level(logging.WARNING):
        await coordinator.async_refresh()

    assert [record for record in caplog.records if "cannot read it" in record.message]


async def test_nut_scope_denied_skips_the_endpoint(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """A custom token denying the "nut" scope skips the UPS endpoint before the first poll."""
    mock_client.async_get_token_permissions.return_value = {
        "id": "1",
        "permissions": {"mode": "custom", "resources": {"nut": "none"}},
    }
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.SETUP_IN_PROGRESS)
    coordinator = _make_coordinator(hass, mock_client, entry)

    await coordinator.async_config_entry_first_refresh()

    mock_client.async_get_nut_status.assert_not_called()
    assert "nut" in coordinator.forbidden_resources
    assert coordinator.data["nut"] == {}
