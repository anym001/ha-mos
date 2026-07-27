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
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientError
from custom_components.mos.const import (
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SERVICES,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SERVICES,
    LOGGER,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry


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

    async def async_start_lxc_container(self, name: str) -> None:
        """
        Start an LXC container, then refresh so its new state is reflected immediately.

        Entities never call the API client directly (see api/__init__.py); this
        is the coordinator-side entry point for the switch platform's write action.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        client = self.config_entry.runtime_data.client
        await client.async_start_lxc_container(name)
        await self.async_request_refresh()

    async def async_stop_lxc_container(self, name: str) -> None:
        """
        Stop an LXC container, then refresh so its new state is reflected immediately.

        Raises:
            MOSApiClientAuthenticationError: If the token is rejected.
            MOSApiClientCommunicationError: If communication fails.
            MOSApiClientError: For other API errors.

        """
        client = self.config_entry.runtime_data.client
        await client.async_stop_lxc_container(name)
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
            "docker_containers": [...],  # Docker containers from /docker/mos/containers
        }

        ``osinfo`` and ``system_load`` are always fetched. The other resources
        can be disabled via the options flow (see ``CONF_ENABLE_DISKS`` and
        friends); when disabled they are not fetched at all and default to an
        empty payload, so the corresponding platforms simply create no
        entities for them.

        Returns:
            The data from the API as a dictionary keyed by resource.

        Raises:
            ConfigEntryAuthFailed: If authentication fails, triggers reauthentication.
            UpdateFailed: If data fetching fails for other reasons.
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

        try:
            results = await asyncio.gather(*tasks.values())
        except MOSApiClientAuthenticationError as exception:
            LOGGER.warning("Authentication error - %s", exception)
            raise ConfigEntryAuthFailed(
                translation_domain="mos",
                translation_key="authentication_failed",
            ) from exception
        except MOSApiClientError as exception:
            LOGGER.exception("Error communicating with API")
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="update_failed",
            ) from exception

        data: dict[str, Any] = dict(zip(tasks.keys(), results, strict=True))
        data.setdefault("services", {})
        data.setdefault("disks", [])
        data.setdefault("pools", [])
        data.setdefault("lxc_containers", [])
        data.setdefault("docker_containers", [])
        return data
