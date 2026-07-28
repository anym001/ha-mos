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
from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientAuthenticationError, MOSApiClientError, MOSApiClientPermissionError
from custom_components.mos.const import (
    ALWAYS_FETCHED_RESOURCES,
    AUTH_FAILURE_GRACE_PERIOD,
    AUTH_FAILURE_MIN_FAILURES,
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
    READ_PERMISSION_RESOURCES,
)
from custom_components.mos.entity_utils import has_read_access, has_write_access
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry


@dataclass
class _AuthFailureStreak:
    """
    An unbroken run of polls whose authentication was rejected with a 401.

    Both halves of the escalation guard are tracked: `started_at` for the
    elapsed-time half (AUTH_FAILURE_GRACE_PERIOD) and `failures` for the
    observation-count half (AUTH_FAILURE_MIN_FAILURES). See the commentary on
    those constants for why neither is sufficient alone.
    """

    started_at: float
    failures: int = 0


@dataclass
class _UpdateOutcome:
    """One poll cycle's results, split by how the coordinator has to react."""

    payload: dict[str, Any] = field(default_factory=dict)
    auth_errors: list[BaseException] = field(default_factory=list)
    permission_errors: dict[str, BaseException] = field(default_factory=dict)
    other_errors: list[BaseException] = field(default_factory=list)


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

    # Optional resources the token may not read. Seeded at setup from the token's
    # permission scope and extended whenever a poll gets a 403, so a denied
    # resource is asked for at most once. Deliberately per-coordinator and not
    # persisted: a reload re-probes, so fixing the token's scope is picked up by
    # reloading the entry rather than needing the integration re-added.
    #
    # Rebound rather than mutated (hence frozenset) - a mutable class attribute
    # would be shared by every coordinator instance in the process.
    forbidden_resources: frozenset[str] = frozenset()

    @property
    def _auth_failure_streak(self) -> _AuthFailureStreak | None:
        """
        The current unbroken run of 401-rejected polls, if any.

        ``None`` when the last poll did not fail with a 401. Cleared on any
        successful poll and on communication errors (which are inconclusive
        about the token's validity). Only once authentication has been rejected
        for both ``AUTH_FAILURE_GRACE_PERIOD`` and ``AUTH_FAILURE_MIN_FAILURES``
        consecutive polls does the coordinator escalate to a reauth flow - see
        ``_async_update_data``.
        """
        store: dict[str, _AuthFailureStreak] = self.hass.data.get(AUTH_FAILURE_STORE, {})
        return store.get(self.config_entry.entry_id)

    def _record_auth_failure(self) -> _AuthFailureStreak:
        """
        Start or continue the auth-failure streak and return it.

        The streak is kept in ``hass.data``, keyed by config entry, rather than
        on the coordinator itself: when setup fails it is retried with a *new*
        coordinator instance, so instance state would reset the grace period on
        every retry and never escalate to reauth.
        """
        store: dict[str, _AuthFailureStreak] = self.hass.data.setdefault(AUTH_FAILURE_STORE, {})
        streak = store.setdefault(self.config_entry.entry_id, _AuthFailureStreak(started_at=time.monotonic()))
        streak.failures += 1
        return streak

    def _clear_auth_failure(self) -> None:
        """Forget the current auth-failure streak, so the grace period restarts from zero."""
        store: dict[str, _AuthFailureStreak] | None = self.hass.data.get(AUTH_FAILURE_STORE)
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
        self._seed_forbidden_resources()

    def _seed_forbidden_resources(self) -> None:
        """
        Drop resources the token's scope already says it cannot read, before the first poll.

        Purely an optimisation over discovering the same thing through a 403 on
        every reload: it saves the request and gets the warning into the log at
        setup, where a user looking for "why are my VM entities missing" will
        find it. Correctness does not depend on it - see ``has_read_access`` for
        why this only acts on an explicit denial.
        """
        scope = (self.token_permissions or {}).get("permissions")
        denied = {key for key, resource in READ_PERMISSION_RESOURCES.items() if not has_read_access(scope, resource)}
        if denied:
            LOGGER.warning(
                "API token has no read access to %s - those entities will not be created. "
                "Grant the token read access in the MOS web UI and reload the integration, "
                "or disable the categories in the integration options",
                ", ".join(sorted(denied)),
            )
        self.forbidden_resources = frozenset(denied)

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

    def _build_update_tasks(self) -> dict[str, Any]:
        """
        Build the per-resource fetch coroutines for one poll cycle.

        Resources disabled in the options flow, and those in
        ``forbidden_resources``, are left out entirely. ``osinfo`` and
        ``system_load`` are always included, so a token whose scope is later
        widened recovers on the next reload without any special handling.

        Returns:
            Coroutines keyed by the data key their result belongs under.

        """
        client = self.config_entry.runtime_data.client
        options = self.config_entry.options
        forbidden = self.forbidden_resources

        def wanted(option: str, default: bool, key: str) -> bool:
            return bool(options.get(option, default)) and key not in forbidden

        tasks: dict[str, Any] = {
            "osinfo": client.async_get_osinfo(),
            "system_load": client.async_get_system_load(),
        }
        if wanted(CONF_ENABLE_SERVICES, DEFAULT_ENABLE_SERVICES, "services"):
            tasks["services"] = client.async_get_services()
        if wanted(CONF_ENABLE_DISKS, DEFAULT_ENABLE_DISKS, "disks"):
            tasks["disks"] = client.async_get_disks()
        if wanted(CONF_ENABLE_POOLS, DEFAULT_ENABLE_POOLS, "pools"):
            tasks["pools"] = client.async_get_pools()
        if wanted(CONF_ENABLE_LXC, DEFAULT_ENABLE_LXC, "lxc_containers"):
            tasks["lxc_containers"] = client.async_get_lxc_containers()
        if wanted(CONF_ENABLE_DOCKER, DEFAULT_ENABLE_DOCKER, "docker_containers"):
            tasks["docker_containers"] = client.async_get_docker_containers()
        # Checked separately from the container list: the raw Docker Engine proxy
        # is a different endpoint and can be denied on its own, in which case the
        # containers still appear, just without live running state.
        if wanted(CONF_ENABLE_DOCKER, DEFAULT_ENABLE_DOCKER, "docker_engine_containers"):
            tasks["docker_engine_containers"] = client.async_get_docker_engine_containers()
        if wanted(CONF_ENABLE_VM, DEFAULT_ENABLE_VM, "vm_machines"):
            tasks["vm_machines"] = client.async_get_vm_machines()
        return tasks

    def _triage_results(self, tasks: dict[str, Any], results: list[Any]) -> _UpdateOutcome:
        """
        Split one cycle's gather results into successful payloads and failure classes.

        Returns:
            The results grouped by the reaction they call for.

        Raises:
            BaseException: Anything that is not an API error - notably
                ``asyncio.CancelledError``, which ``return_exceptions`` captures
                like any other and which must never be swallowed.

        """
        outcome = _UpdateOutcome()
        for key, result in zip(tasks.keys(), results, strict=True):
            if not isinstance(result, BaseException):
                outcome.payload[key] = result
            elif isinstance(result, MOSApiClientAuthenticationError):
                outcome.auth_errors.append(result)
            elif isinstance(result, MOSApiClientPermissionError):
                outcome.permission_errors[key] = result
            elif isinstance(result, MOSApiClientError):
                outcome.other_errors.append(result)
            else:
                raise result
        return outcome

    def _handle_denied_resources(self, outcome: _UpdateOutcome) -> None:
        """
        Record 403-denied resources so they are not requested again.

        Raises:
            UpdateFailed: If an always-fetched resource was denied. Deliberately
                not ``ConfigEntryAuthFailed``: the token is valid, it just lacks
                the scope, and a reauth flow would validate it successfully and
                land straight back here on the next poll.

        """
        if not outcome.permission_errors:
            return

        denied = set(outcome.permission_errors)
        newly_denied = denied - self.forbidden_resources - ALWAYS_FETCHED_RESOURCES
        if newly_denied:
            LOGGER.warning(
                "API token is not authorized to read %s - skipping %s until the integration is reloaded. "
                "This is a token permission problem, not an invalid token; grant read access in the "
                "MOS web UI under User Settings > Admin API Tokens",
                ", ".join(sorted(newly_denied)),
                "it" if len(newly_denied) == 1 else "them",
            )
            self.forbidden_resources = self.forbidden_resources | newly_denied

        denied_required = denied & ALWAYS_FETCHED_RESOURCES
        if denied_required:
            exception = outcome.permission_errors[next(iter(sorted(denied_required)))]
            LOGGER.error(
                "API token is not authorized to read %s, which the integration always needs: %s",
                ", ".join(sorted(denied_required)),
                exception,
            )
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="insufficient_read_permission",
                translation_placeholders={"resource": ", ".join(sorted(denied_required))},
            ) from exception

    def _handle_failed_resources(self, outcome: _UpdateOutcome) -> None:
        """
        Apply the auth-failure grace period and surface communication errors.

        Raises:
            ConfigEntryAuthFailed: If authentication has been rejected for longer
                than ``AUTH_FAILURE_GRACE_PERIOD`` *and* for at least
                ``AUTH_FAILURE_MIN_FAILURES`` consecutive polls.
            UpdateFailed: For communication errors, and for an authentication
                rejection that is still inside the grace period.

        """
        # Communication errors are checked first and win over a 401 in the same
        # cycle: a server answering some requests and dropping others is
        # unstable, which says nothing about the token. Resetting the streak here
        # keeps a flapping server from accumulating its way into a spurious reauth.
        if outcome.other_errors:
            exception = outcome.other_errors[0]
            self._clear_auth_failure()
            LOGGER.error("Error communicating with API: %s", exception)
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="update_failed",
            ) from exception

        if not outcome.auth_errors:
            return

        exception = outcome.auth_errors[0]
        streak = self._record_auth_failure()
        elapsed = time.monotonic() - streak.started_at
        if elapsed >= AUTH_FAILURE_GRACE_PERIOD.total_seconds() and streak.failures >= AUTH_FAILURE_MIN_FAILURES:
            LOGGER.warning(
                "Authentication rejected on %d consecutive polls over %.0fs - triggering reauth: %s",
                streak.failures,
                elapsed,
                exception,
            )
            raise ConfigEntryAuthFailed(
                translation_domain="mos",
                translation_key="authentication_failed",
            ) from exception
        # A 401 is more likely a server that is rebooting or otherwise briefly
        # unavailable than a genuinely invalid token. Keep the entry
        # authenticated and retry until both halves of the guard are satisfied,
        # so the token is not thrown away over a transient blip. During setup
        # this becomes ConfigEntryNotReady, so Home Assistant retries with
        # backoff instead of prompting for reauthentication.
        LOGGER.warning(
            "Authentication rejected (%d/%d failures, %.0fs/%.0fs before reauth) - "
            "retrying, server may be unavailable: %s",
            streak.failures,
            AUTH_FAILURE_MIN_FAILURES,
            elapsed,
            AUTH_FAILURE_GRACE_PERIOD.total_seconds(),
            exception,
        )
        raise UpdateFailed(
            translation_domain="mos",
            translation_key="authentication_failed_transient",
        ) from exception

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

        Resources are fetched concurrently and evaluated individually: a
        resource the token is not authorized to read (403) is dropped and the
        rest of the poll still succeeds, so a narrowly scoped token yields fewer
        entities rather than none.

        Raises:
            ConfigEntryAuthFailed: If the token has been rejected (401) for longer
                than ``AUTH_FAILURE_GRACE_PERIOD`` and on at least
                ``AUTH_FAILURE_MIN_FAILURES`` consecutive polls; triggers
                reauthentication.
            UpdateFailed: If data fetching fails for other reasons - a
                communication error, an authentication rejection still inside the
                grace period, or a denied always-fetched resource.
        """
        tasks = self._build_update_tasks()
        # return_exceptions so one resource cannot take the whole poll down with
        # it: a token scoped to some resources but not others would otherwise
        # make every cycle fail on the first 403, leaving the integration with no
        # data at all even though most endpoints answered fine.
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        outcome = self._triage_results(tasks, results)
        self._handle_denied_resources(outcome)
        self._handle_failed_resources(outcome)

        self._clear_auth_failure()
        data: dict[str, Any] = outcome.payload
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
