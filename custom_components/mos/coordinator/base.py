"""
Core DataUpdateCoordinator implementation for mos.

This module contains the main coordinator class that manages data fetching
and updates for all entities in the integration. It handles refresh cycles,
error handling, and triggers reauthentication when needed.

For more information on coordinators:
https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientError
from custom_components.mos.const import (
    AUTH_FAILURE_GRACE_PERIOD,
    AUTH_FAILURE_STORE,
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SERVICES,
    CONF_ENABLE_VM,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SERVICES,
    DEFAULT_ENABLE_VM,
    LOGGER,
)
from custom_components.mos.entity_utils import has_write_access
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry


def _merge_docker_engine_state(
    containers: list[dict[str, Any]],
    engine_containers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge live Docker Engine state into MOS's docker container list.

    ``/docker/mos/containers`` has no running-state field; the raw Docker
    Engine proxy's ``/containers/json`` does, keyed by name (with a leading
    slash, per Docker's own ``Names`` convention).
    """
    engine_by_name: dict[str, dict[str, Any]] = {}
    for engine_container in engine_containers:
        for raw_name in engine_container.get("Names") or []:
            engine_by_name[raw_name.lstrip("/")] = engine_container

    merged: list[dict[str, Any]] = []
    for container in containers:
        name: str = container.get("name") or ""
        engine_container = engine_by_name.get(name) or {}
        merged.append({**container, "state": engine_container.get("State")})
    return merged


class MOSDataUpdateCoordinator(DataUpdateCoordinator):
    """
    Class to manage fetching data from the API.

    This coordinator handles all data fetching for the integration and distributes
    updates to all entities. It manages:
    - Periodic data updates based on update_interval
    - Error handling and recovery
    - Authentication failure detection and reauthentication triggers
    - Data distribution to all entities
    - Context-based data fetching (only fetch data for active entities)

    For more information:
    https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities

    Attributes:
        config_entry: The config entry for this integration instance.
        token_permissions: The token's permission scope from
            ``/auth/admin-tokens/me``, fetched once at setup (not on every
            poll cycle, since permissions don't change at runtime). ``None``
            if the MOS server doesn't support this endpoint yet, or the
            lookup otherwise failed - callers should treat that as "unknown,
            assume full access" rather than blocking on it.
    """

    config_entry: MOSConfigEntry
    token_permissions: dict[str, Any] | None = None

    @property
    def _auth_failure_since(self) -> float | None:
        """
        Monotonic timestamp of the first failure in the current auth-failure streak.

        ``None`` when the last poll did not fail with an auth error. Cleared on
        any successful poll and on communication errors (which are inconclusive
        about the token's validity). Only once auth has been rejected
        continuously for ``AUTH_FAILURE_GRACE_PERIOD`` does the coordinator
        escalate to a reauth flow - see ``_async_update_data``.
        """
        store: dict[str, float] = self.hass.data.get(AUTH_FAILURE_STORE, {})
        return store.get(self.config_entry.entry_id)

    def _record_auth_failure(self) -> float:
        """
        Start or continue the auth-failure streak and return its duration in seconds.

        The streak is kept in ``hass.data``, keyed by config entry, rather than
        on the coordinator itself: when setup fails it is retried with a *new*
        coordinator instance, so instance state would reset the grace period on
        every retry and never escalate to reauth.
        """
        store: dict[str, float] = self.hass.data.setdefault(AUTH_FAILURE_STORE, {})
        now = time.monotonic()
        return now - store.setdefault(self.config_entry.entry_id, now)

    def _clear_auth_failure(self) -> None:
        """Forget the current auth-failure streak, so the grace period restarts from zero."""
        store: dict[str, float] | None = self.hass.data.get(AUTH_FAILURE_STORE)
        if store is not None:
            store.pop(self.config_entry.entry_id, None)

    async def _async_setup(self) -> None:
        """
        Set up the coordinator.

        This method is called automatically during async_config_entry_first_refresh()
        and is the ideal place for one-time initialization tasks such as:
        - Loading device information
        - Setting up event listeners
        - Initializing caches

        This runs before the first data fetch, ensuring any required setup
        is complete before entities start requesting data.

        Token permission introspection happens here rather than in
        ``_async_update_data`` because the token's permission scope doesn't
        change at runtime - one lookup per config entry lifetime is enough. A
        genuinely invalid token is still caught properly: the first
        ``_async_update_data`` call (via ``async_get_osinfo``) runs right
        after this and maps auth failures to ``ConfigEntryAuthFailed`` as
        usual, so failures here are not re-raised.
        """
        client = self.config_entry.runtime_data.client
        try:
            self.token_permissions = await client.async_get_token_permissions()
        except MOSApiClientError as exception:
            LOGGER.debug("Token permission introspection unavailable - %s", exception)
            self.token_permissions = None

    def _optimistically_set_container_state(self, resource_key: str, name: str, state: str) -> None:
        """
        Patch a single container's ``state`` in ``self.data`` and notify listeners, without polling.

        Used after a successful start/stop so the switch flips immediately,
        instead of waiting on (or triggering) a full ``_async_update_data``
        round trip. That round trip previously ran via ``async_request_refresh()``
        right after a start/stop call that can itself take up to
        ``CONTAINER_ACTION_TIMEOUT`` - on a short ``update_interval`` that
        collides with the *next* regularly scheduled poll, doubling up
        concurrent requests against the MOS server right when it's already
        slow. ``async_set_updated_data`` also reschedules the periodic timer,
        so this doesn't cause an extra poll on top of the regular cadence.

        If `name` isn't present in the current data (e.g. it raced a resource
        being disabled), this is a no-op - the next scheduled poll will pick
        up the real state regardless.
        """
        containers: list[dict[str, Any]] = self.data.get(resource_key) or []
        if not any(container.get("name") == name for container in containers):
            return
        patched = [
            {**container, "state": state} if container.get("name") == name else container for container in containers
        ]
        self.async_set_updated_data({**self.data, resource_key: patched})

    def _check_write_access(self, resource: str) -> None:
        """
        Raise if the configured token cannot write to `resource`.

        Checked before every write action (LXC/Docker start/stop) so an
        insufficiently-scoped token fails with a clear, translated error
        instead of a generic 401/403 from the server.

        ``token_permissions`` is the full ``/auth/admin-tokens/me`` payload
        (``{id, name, role, isBootToken, permissions}``); the actual
        mode/resources live one level down, under its ``permissions`` key.

        Raises:
            HomeAssistantError: If the token lacks write access to `resource`.

        """
        scope = (self.token_permissions or {}).get("permissions")
        if not has_write_access(scope, resource):
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="insufficient_write_permission",
                translation_placeholders={"resource": resource},
            )

    async def async_start_lxc_container(self, name: str) -> None:
        """
        Start an LXC container, then optimistically flip its local state to "running".

        Entities never call the API client directly (see api/__init__.py); this
        is the coordinator-side entry point for the switch platform's write action.

        Raises:
            HomeAssistantError: If the token lacks write access to "lxc".
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        self._check_write_access("lxc")
        client = self.config_entry.runtime_data.client
        await client.async_start_lxc_container(name)
        self._optimistically_set_container_state("lxc_containers", name, "running")

    async def async_stop_lxc_container(self, name: str) -> None:
        """
        Stop an LXC container, then optimistically flip its local state to "stopped".

        Raises:
            HomeAssistantError: If the token lacks write access to "lxc".
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        self._check_write_access("lxc")
        client = self.config_entry.runtime_data.client
        await client.async_stop_lxc_container(name)
        self._optimistically_set_container_state("lxc_containers", name, "stopped")

    async def async_start_docker_container(self, name: str) -> None:
        """
        Start a Docker container, then optimistically flip its local state to "running".

        Raises:
            HomeAssistantError: If the token lacks write access to "docker".
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        self._check_write_access("docker")
        client = self.config_entry.runtime_data.client
        await client.async_start_docker_container(name)
        self._optimistically_set_container_state("docker_containers", name, "running")

    async def async_stop_docker_container(self, name: str) -> None:
        """
        Stop a Docker container, then optimistically flip its local state to "exited".

        Raises:
            HomeAssistantError: If the token lacks write access to "docker".
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        self._check_write_access("docker")
        client = self.config_entry.runtime_data.client
        await client.async_stop_docker_container(name)
        self._optimistically_set_container_state("docker_containers", name, "exited")

    async def async_start_vm_machine(self, name: str) -> None:
        """
        Start a VM, then refresh so its new state is reflected immediately.

        Raises:
            HomeAssistantError: If the token lacks write access to "vm".
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        self._check_write_access("vm")
        client = self.config_entry.runtime_data.client
        await client.async_start_vm_machine(name)
        await self.async_request_refresh()

    async def async_stop_vm_machine(self, name: str) -> None:
        """
        Stop a VM, then refresh so its new state is reflected immediately.

        Raises:
            HomeAssistantError: If the token lacks write access to "vm".
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        self._check_write_access("vm")
        client = self.config_entry.runtime_data.client
        await client.async_stop_vm_machine(name)
        await self.async_request_refresh()

    async def _async_update_data(self) -> Any:
        """
        Fetch data from the MOS API.

        This is the only method that should be implemented in a DataUpdateCoordinator.
        It is called automatically based on the update_interval.

        The returned data is keyed by resource so that additional endpoints
        can be added as further keys in later phases without breaking existing
        entities:

        {
            "osinfo": {...},       # System / hardware information from /osinfo
            "system_load": {...},  # Live CPU/memory/swap telemetry from /system/load
            "services": {...},     # Service enabled/running flags from /services
            "disks": [...],        # Physical disks from /disks
            "pools": [...],        # Storage pools from /pools
            "lxc_containers": [...],   # LXC containers from /lxc/containers/usage
            "docker_containers": [...],  # Docker containers from /docker/mos/containers,
                                          # with "state" merged in from the raw Docker
                                          # Engine proxy (/docker/containers/json)
            "vm_machines": [...],      # VMs from /vm/machines/usage
        }

        ``osinfo`` and ``system_load`` are always fetched. The other resources
        can be disabled via the options flow (see ``CONF_ENABLE_DISKS`` and
        friends); when disabled they are not fetched at all and default to an
        empty payload, so the corresponding platforms simply create no
        entities for them.

        Returns:
            The data from the API as a dictionary keyed by resource.

        Raises:
            ConfigEntryAuthFailed: If authentication has been rejected continuously
                for longer than ``AUTH_FAILURE_GRACE_PERIOD``; triggers reauthentication.
            UpdateFailed: If data fetching fails for other reasons, including an
                authentication rejection that is still inside the grace period.
        """
        client = self.config_entry.runtime_data.client
        options = self.config_entry.options

        tasks: dict[str, Any] = {
            "osinfo": client.async_get_osinfo(),
            "system_load": client.async_get_system_load(),
        }
        if options.get(CONF_ENABLE_SERVICES, DEFAULT_ENABLE_SERVICES):
            tasks["services"] = client.async_get_services()
        if options.get(CONF_ENABLE_DISKS, DEFAULT_ENABLE_DISKS):
            tasks["disks"] = client.async_get_disks()
        if options.get(CONF_ENABLE_POOLS, DEFAULT_ENABLE_POOLS):
            tasks["pools"] = client.async_get_pools()
        if options.get(CONF_ENABLE_LXC, DEFAULT_ENABLE_LXC):
            tasks["lxc_containers"] = client.async_get_lxc_containers()
        if options.get(CONF_ENABLE_DOCKER, DEFAULT_ENABLE_DOCKER):
            tasks["docker_containers"] = client.async_get_docker_containers()
            tasks["docker_engine_containers"] = client.async_get_docker_engine_containers()
        if options.get(CONF_ENABLE_VM, DEFAULT_ENABLE_VM):
            tasks["vm_machines"] = client.async_get_vm_machines()

        try:
            results = await asyncio.gather(*tasks.values())
        except MOSApiClientAuthenticationError as exception:
            elapsed = self._record_auth_failure()
            if elapsed >= AUTH_FAILURE_GRACE_PERIOD.total_seconds():
                LOGGER.warning(
                    "Authentication rejected continuously for %.0fs - triggering reauth: %s",
                    elapsed,
                    exception,
                )
                raise ConfigEntryAuthFailed(
                    translation_domain="mos",
                    translation_key="authentication_failed",
                ) from exception
            # A 401/403 is more likely a server that is rebooting or otherwise
            # briefly unavailable than a genuinely invalid token. Keep the entry
            # authenticated and retry until the grace period elapses, so the token
            # is not thrown away over a transient blip. During setup this becomes
            # ConfigEntryNotReady, so Home Assistant retries with backoff instead
            # of prompting for reauthentication.
            LOGGER.warning(
                "Authentication rejected (%.0fs/%.0fs before reauth) - retrying, server may be unavailable: %s",
                elapsed,
                AUTH_FAILURE_GRACE_PERIOD.total_seconds(),
                exception,
            )
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="authentication_failed_transient",
            ) from exception
        except MOSApiClientError as exception:
            # Communication error: we could not reach the server at all, so this
            # says nothing about the token's validity. Reset the auth streak so a
            # flapping server never accumulates its way into a spurious reauth.
            self._clear_auth_failure()
            LOGGER.exception("Error communicating with API")
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="update_failed",
            ) from exception

        self._clear_auth_failure()
        data: dict[str, Any] = dict(zip(tasks.keys(), results, strict=True))
        data.setdefault("services", {})
        data.setdefault("disks", [])
        data.setdefault("pools", [])
        data.setdefault("lxc_containers", [])
        data.setdefault("docker_containers", [])
        data.setdefault("vm_machines", [])
        if "docker_engine_containers" in data:
            data["docker_containers"] = _merge_docker_engine_state(
                data["docker_containers"],
                data.pop("docker_engine_containers"),
            )
        return data
