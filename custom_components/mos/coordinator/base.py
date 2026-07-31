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
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import (
    MOSApiClientAuthenticationError,
    MOSApiClientError,
    MOSApiClientPermissionError,
    MOSApiClientRateLimitError,
)
from custom_components.mos.const import (
    ALWAYS_FETCHED_RESOURCES,
    AUTH_FAILURE_GRACE_PERIOD,
    AUTH_FAILURE_MIN_FAILURES,
    AUTH_FAILURE_STORE,
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SENSORS,
    CONF_ENABLE_SERVICES,
    CONF_ENABLE_VM,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SENSORS,
    DEFAULT_ENABLE_SERVICES,
    DEFAULT_ENABLE_VM,
    LOGGER,
    PERMISSION_RESOURCE_BY_KEY,
    READ_PERMISSION_RESOURCES,
    RESOURCE_STALE_GRACE_PERIOD,
    RESOURCE_STALE_MIN_FAILURES,
)
from custom_components.mos.entity_utils import has_read_access, has_write_access
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from collections.abc import Mapping

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
class _DegradedResource:
    """
    An unbroken run of polls in which one optional resource failed transiently.

    Mirrors ``_AuthFailureStreak``: ``started_at`` feeds the elapsed-time half of
    the staleness guard (RESOURCE_STALE_GRACE_PERIOD) and ``failures`` the
    observation-count half (RESOURCE_STALE_MIN_FAILURES). Both must be satisfied
    before the resource's entities stop reporting as available - see the
    commentary on those constants.

    Unlike the auth streak this lives on the coordinator instance rather than in
    ``hass.data``. The auth streak has to survive a failed setup being retried
    with a fresh coordinator; a degraded *optional* resource never fails setup,
    so there is no retry loop that could keep resetting the timer.
    """

    started_at: float
    failures: int = 0


@dataclass
class _UpdateOutcome:
    """One poll cycle's results, split by how the coordinator has to react."""

    payload: dict[str, Any] = field(default_factory=dict)
    auth_errors: list[BaseException] = field(default_factory=list)
    permission_errors: dict[str, BaseException] = field(default_factory=dict)
    rate_limit_errors: dict[str, BaseException] = field(default_factory=dict)
    communication_errors: dict[str, BaseException] = field(default_factory=dict)

    def transient_resource_errors(self) -> dict[str, BaseException]:
        """
        Per-resource failures that should not tear the resource down (403 / 429 / unreachable).

        All three are transient from the coordinator's point of view: the
        resource keeps its last-known-good data and is retried on the next poll.
        Merged here so the update flow has a single view of "which resources
        failed but must be preserved".

        Authentication errors are deliberately absent. A rejected token is a
        property of the connection, not of one endpoint, so a 401 anywhere fails
        the whole cycle - see ``_handle_failed_resources``.
        """
        return {**self.permission_errors, **self.rate_limit_errors, **self.communication_errors}


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


def _flatten_sensors(raw_sensors: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """
    Flatten the ``/sensors`` payload's per-category dict into one flat list.

    ``/sensors`` groups readings by category (``fan``, ``temperature``, ...);
    each reading is tagged with its category here so downstream consumers
    (naming, unique_id) don't need the original grouping to know it.
    """
    return [{**item, "category": category} for category, items in raw_sensors.items() for item in items]


def _carry_forward_docker_engine_state(
    containers: list[dict[str, Any]],
    previous_containers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Preserve the last-known Docker ``state`` when the engine proxy is absent.

    ``docker_engine_containers`` is merged into ``docker_containers`` and then
    dropped every poll, so it never lands in ``self.data`` where
    ``_retain_last_known_good`` could carry it forward. When the raw Docker
    Engine proxy is transiently unavailable (403/429) while the MOS container
    list itself still answers, re-attach each container's ``state`` from the
    previously merged data (keyed by name) instead of letting every container's
    running-state blank out to ``None`` for a cycle. Containers unknown last
    poll (or on the first poll) get ``None``, so no stale value is invented.
    """
    state_by_name: dict[str, Any] = {
        name: container.get("state") for container in previous_containers if (name := container.get("name"))
    }
    return [{**container, "state": state_by_name.get(container.get("name") or "")} for container in containers]


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

    # Optional resources the token's scope explicitly denies reading. Seeded once
    # at setup from the token's permission scope (see ``_seed_forbidden_resources``)
    # and never extended at runtime: a 403 that still reaches a poll is, by
    # construction, on a resource the scope did *not* explicitly deny, so it is
    # treated as transient rather than a permanent denial (see
    # ``_classify_transient_resource_failures``). Fixing the token's scope is
    # picked up by reloading the entry.
    #
    # Rebound rather than mutated (hence frozenset) - a mutable class attribute
    # would be shared by every coordinator instance in the process.
    forbidden_resources: frozenset[str] = frozenset()

    # Resources whose last poll failed transiently (403 on a scope-allowed
    # resource, a 429 rate limit, or a communication error) and are currently
    # being served from last-known-good data, mapped to how long and how often
    # they have been failing.
    #
    # Serves two purposes. It throttles logging - warn once when a resource
    # starts failing, stay quiet while it keeps failing, note when it recovers -
    # so a persistently flaky server does not flood the log every poll. And it
    # feeds ``stale_resources``, which caps how long last-known-good data may go
    # on being presented as current.
    #
    # The class default is a read-only mapping so the shared-mutable-class-
    # attribute mistake cannot happen: it is rebound with a fresh dict on every
    # poll, never mutated in place (same reasoning as ``forbidden_resources``
    # above, which uses frozenset for it).
    _degraded_resources: Mapping[str, _DegradedResource] = MappingProxyType({})

    # Resources that have been failing long enough to count as stale, recomputed
    # once per poll from ``_degraded_resources``. Entities backed by one of these
    # report themselves unavailable rather than serving frozen values as if they
    # were current (see ``MOSEntity.available``).
    #
    # Deliberately a stored snapshot rather than a property that re-evaluates the
    # clock on every read: entity availability must only ever change as a result
    # of a poll, so that a transition is always paired with a listener
    # notification. A time-based property could flip silently between two polls
    # and leave entities rendering the opposite of what the coordinator thinks.
    _stale_resources: frozenset[str] = frozenset()

    @property
    def stale_resources(self) -> frozenset[str]:
        """
        Resources whose retained data has gone stale and must not be shown as current.

        Empty on a healthy server. Never contains an always-fetched resource: a
        failure on those takes the whole poll down (``UpdateFailed``) long before
        any per-resource bookkeeping happens.
        """
        return self._stale_resources

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
                "Grant the token read access to %s in the MOS web UI and reload the integration, "
                "or disable the categories in the integration options",
                ", ".join(sorted(denied)),
                ", ".join(sorted({READ_PERMISSION_RESOURCES[key] for key in denied})),
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
        if wanted(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS, "sensors"):
            tasks["sensors"] = client.async_get_sensors()
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
            elif isinstance(result, MOSApiClientRateLimitError):
                outcome.rate_limit_errors[key] = result
            elif isinstance(result, MOSApiClientError):
                outcome.communication_errors[key] = result
            else:
                raise result
        return outcome

    def _classify_transient_resource_failures(self, outcome: _UpdateOutcome) -> set[str]:
        """
        Decide how to react to per-resource failures, and return the ones to preserve.

        A 403 or 429 that reaches here is transient: the token's *explicit* scope
        denials are seeded into ``forbidden_resources`` before the first poll and
        never requested, so anything the server refuses at runtime is on a
        resource the scope allowed (or was silent about). A communication error
        (timeout, dropped connection, 5xx) is transient by nature. Rather than
        dropping such a resource - which would empty it and make the
        dynamic-entity sync tear down its devices until a reload - the
        coordinator keeps that resource's last-known-good data (see
        ``_retain_last_known_good``) and retries it on the next poll.

        The one exception is an always-fetched resource (osinfo, system_load):
        there is nothing meaningful to show without it, so the whole cycle fails
        (retryable) instead. Communication errors on those are caught earlier,
        in ``_handle_failed_resources``.

        Returns:
            The optional resource keys that failed transiently this cycle and
            whose previous data must be carried forward.

        Raises:
            UpdateFailed: If an always-fetched resource was denied (403) or rate
                limited (429). Deliberately not ``ConfigEntryAuthFailed``: the
                token is valid, so a reauth flow would validate it successfully
                and land straight back here on the next poll.

        """
        self._raise_if_required_resource_failed(outcome)

        transient = set(outcome.transient_resource_errors()) - ALWAYS_FETCHED_RESOURCES
        self._track_degraded_resources(outcome, transient)
        return transient

    def _raise_if_required_resource_failed(self, outcome: _UpdateOutcome) -> None:
        """
        Fail the whole cycle if an always-fetched resource was denied or rate limited.

        Raises:
            UpdateFailed: If osinfo or system_load returned 403 or 429.

        """
        denied_required = set(outcome.permission_errors) & ALWAYS_FETCHED_RESOURCES
        if denied_required:
            exception = outcome.permission_errors[min(denied_required)]
            # The message tells the user what to grant, so it has to name the
            # resource as the MOS web UI spells it - "mos", not "osinfo".
            scopes = ", ".join(sorted({PERMISSION_RESOURCE_BY_KEY.get(key, key) for key in denied_required}))
            LOGGER.error(
                "API token is not authorized to read %s, which the integration always needs - "
                "grant it read access to %s in the MOS web UI: %s",
                ", ".join(sorted(denied_required)),
                scopes,
                exception,
            )
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="insufficient_read_permission",
                translation_placeholders={"resource": scopes},
            ) from exception

        limited_required = set(outcome.rate_limit_errors) & ALWAYS_FETCHED_RESOURCES
        if limited_required:
            exception = outcome.rate_limit_errors[min(limited_required)]
            LOGGER.warning(
                "Rate limited (HTTP 429) on %s, which the integration always needs - retrying: %s",
                ", ".join(sorted(limited_required)),
                exception,
            )
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="update_failed",
            ) from exception

    def _track_degraded_resources(self, outcome: _UpdateOutcome, transient: set[str]) -> None:
        """
        Update the per-resource failure streaks for this poll, then log and re-evaluate staleness.

        A resource that failed again keeps its existing ``started_at`` and has its
        failure count incremented; one that failed for the first time starts a
        fresh streak; one that answered again is dropped entirely, so recovery
        resets both halves of the guard. The mapping is rebuilt rather than
        mutated - see the note on ``_degraded_resources``.
        """
        previous = self._degraded_resources
        now = time.monotonic()
        current: dict[str, _DegradedResource] = {}
        for key in transient:
            streak = previous.get(key)
            current[key] = _DegradedResource(
                started_at=streak.started_at if streak else now,
                failures=(streak.failures if streak else 0) + 1,
            )

        self._log_transient_resource_failures(outcome, transient, frozenset(previous))
        self._degraded_resources = current
        self._update_stale_resources(now)

    def _update_stale_resources(self, now: float) -> None:
        """
        Recompute which resources have been failing long enough to stop counting as current.

        Only resources that have satisfied *both* halves of the guard qualify.
        Always-fetched resources are subtracted as a fail-safe: they can never
        get this far (a failure on one raises ``UpdateFailed`` before any
        per-resource bookkeeping), and the integration must never end up with
        every entity unavailable because of a bookkeeping bug here.

        When the set changes, listeners are notified explicitly. This is not
        redundant with Home Assistant's own notification: the coordinator runs
        with ``always_update=False``, so ``DataUpdateCoordinator._async_refresh``
        only notifies when ``previous_data != self.data`` - and a stale resource's
        data is retained *unchanged* by definition. A poll in which nothing else
        happened to change would therefore leave entities rendering the old
        availability, which is exactly the frozen-but-looks-live state this whole
        mechanism exists to prevent. ``call_soon`` defers the notification past
        the running refresh, which assigns ``self.data`` only after
        ``_async_update_data`` returns.
        """
        grace_period = RESOURCE_STALE_GRACE_PERIOD.total_seconds()
        stale = (
            frozenset(
                key
                for key, degraded in self._degraded_resources.items()
                if degraded.failures >= RESOURCE_STALE_MIN_FAILURES and now - degraded.started_at >= grace_period
            )
            - ALWAYS_FETCHED_RESOURCES
        )
        if stale == self._stale_resources:
            return

        newly_stale = sorted(stale - self._stale_resources)
        if newly_stale:
            LOGGER.error(
                "%s has been failing for over %d minutes - its entities are now marked unavailable rather than "
                "continuing to report data that stopped updating then. They recover automatically as soon as the "
                "server answers again; no reload needed",
                ", ".join(newly_stale),
                RESOURCE_STALE_GRACE_PERIOD.total_seconds() // 60,
            )

        self._stale_resources = stale
        self.hass.loop.call_soon(self.async_update_listeners)

    def _log_transient_resource_failures(
        self,
        outcome: _UpdateOutcome,
        transient: set[str],
        degraded: frozenset[str],
    ) -> None:
        """
        Log transient per-resource failures once, without flooding on a persistently flaky server.

        Warns the first time a resource starts failing, stays quiet (debug) while
        it keeps failing, and notes when a previously failing resource recovers.

        Args:
            outcome: This poll's results, for the per-category error details.
            transient: Resources that failed transiently this poll.
            degraded: Resources that were already failing before this poll, used
                to tell a new failure from a continuing one.

        """
        newly = transient - degraded
        newly_denied = sorted(newly & set(outcome.permission_errors))
        newly_limited = sorted(newly & set(outcome.rate_limit_errors))
        newly_unreachable = sorted(newly & set(outcome.communication_errors))
        if newly_unreachable:
            LOGGER.warning(
                "Error communicating with API for %s (%s) - keeping last-known state and retrying "
                "on the next poll; the rest of this update was applied normally",
                ", ".join(newly_unreachable),
                outcome.communication_errors[newly_unreachable[0]],
            )
        if newly_denied:
            LOGGER.warning(
                "Server returned 403 for %s although the token has read access - treating as transient "
                "(e.g. the MOS server reloading) and retrying on the next poll; entities keep their "
                "last-known state meanwhile. If this persists, check the token's read scope in the "
                "MOS web UI",
                ", ".join(newly_denied),
            )
        if newly_limited:
            LOGGER.warning(
                "Rate limited (HTTP 429) on %s - keeping last-known state and retrying on the next poll. "
                "If this persists, increase the polling interval in the integration options",
                ", ".join(newly_limited),
            )

        still_failing = sorted(transient & degraded)
        if still_failing:
            LOGGER.debug("Still serving last-known state for %s (transient failure)", ", ".join(still_failing))

        recovered = sorted(degraded - transient)
        if recovered:
            LOGGER.info("%s recovered after a transient failure - fresh data again", ", ".join(recovered))

    def _retain_last_known_good(self, data: dict[str, Any], transient: set[str]) -> None:
        """
        Carry a transiently-failed resource's previous data forward into this cycle's payload.

        A resource that returned 403/429 this cycle is absent from ``data``.
        Leaving it absent would default it to empty, and the dynamic-entity sync
        would then remove every device backed by it. Copying the last successful
        value keeps those entities present and unchanged until the resource
        answers again. A resource that never succeeded (e.g. a 403 on the very
        first poll) has no previous value and is left to default to empty - there
        are no entities to preserve yet.
        """
        previous = self.data or {}
        for key in transient:
            if key in previous:
                data[key] = previous[key]

    def _raise_if_required_resource_unreachable(self, outcome: _UpdateOutcome) -> None:
        """
        Fail the whole cycle if an always-fetched resource hit a communication error.

        A communication error on an *optional* resource costs only that resource:
        it keeps its last-known-good data and is retried next poll, so a single
        slow or flaky endpoint no longer takes the other nine down with it. On
        osinfo or system_load there is nothing meaningful left to show, so the
        cycle fails instead.

        That distinction is also what keeps a genuinely unreachable server
        honest: when the host is down *every* request fails, the always-fetched
        ones among them, so the entry goes unavailable as before rather than
        quietly serving stale data forever.

        Raises:
            UpdateFailed: If osinfo or system_load hit a communication error.

        """
        unreachable_required = set(outcome.communication_errors) & ALWAYS_FETCHED_RESOURCES
        if not unreachable_required:
            return

        exception = outcome.communication_errors[min(unreachable_required)]
        LOGGER.error(
            "Error communicating with API for %s, which the integration always needs: %s",
            ", ".join(sorted(unreachable_required)),
            exception,
        )
        raise UpdateFailed(
            translation_domain="mos",
            translation_key="update_failed",
        ) from exception

    def _handle_failed_resources(self, outcome: _UpdateOutcome) -> None:
        """
        Apply the auth-failure grace period and surface a cycle-fatal communication error.

        Raises:
            ConfigEntryAuthFailed: If authentication has been rejected for longer
                than ``AUTH_FAILURE_GRACE_PERIOD`` *and* for at least
                ``AUTH_FAILURE_MIN_FAILURES`` consecutive polls.
            UpdateFailed: If an always-fetched resource could not be reached, or
                for an authentication rejection that is still inside the grace
                period.

        """
        # Communication errors are evaluated first and win over a 401 in the same
        # cycle: a server answering some requests and dropping others is
        # unstable, which says nothing about the token. Resetting the streak here
        # keeps a flapping server from accumulating its way into a spurious
        # reauth. It applies even when the failure is confined to an optional
        # resource and the cycle itself survives - the server is no less unstable
        # for it.
        if outcome.communication_errors:
            self._clear_auth_failure()
        self._raise_if_required_resource_unreachable(outcome)

        if not outcome.auth_errors:
            return

        exception = outcome.auth_errors[0]
        if outcome.communication_errors:
            # A 401 next to a dropped connection elsewhere. The token was
            # rejected, so the cycle still fails rather than publishing a payload
            # with that resource silently missing - but the streak stays cleared,
            # so this cycle cannot count toward a reauth prompt.
            LOGGER.warning(
                "Authentication rejected while the server was also failing on %s - treating as "
                "instability rather than an invalid token, and retrying: %s",
                ", ".join(sorted(outcome.communication_errors)),
                exception,
            )
            raise UpdateFailed(
                translation_domain="mos",
                translation_key="authentication_failed_transient",
            ) from exception

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
            "sensors": [...],       # Hardware readings from /sensors, flattened
                                     # from their per-category grouping into one
                                     # list, each item tagged with "category"
        }

        ``osinfo`` and ``system_load`` are always fetched. The other resources
        can be disabled via the options flow (see ``CONF_ENABLE_DISKS`` and
        friends); when disabled they are not fetched at all and default to an
        empty payload, so the corresponding platforms simply create no
        entities for them.

        Returns:
            The data from the API as a dictionary keyed by resource.

        Resources are fetched concurrently and evaluated individually: a
        resource that transiently fails - a 403 on a scope-allowed resource, a
        429 rate limit, or a communication error such as a timeout or 5xx -
        keeps its last-known-good data and is retried next poll, so the rest of
        the poll still succeeds and no entities are torn down over a passing
        server hiccup. Only a rejected token (401, which is a property of the
        connection rather than of one endpoint) or a failure on an always-fetched
        resource takes the whole cycle down.

        Raises:
            ConfigEntryAuthFailed: If the token has been rejected (401) for longer
                than ``AUTH_FAILURE_GRACE_PERIOD`` and on at least
                ``AUTH_FAILURE_MIN_FAILURES`` consecutive polls; triggers
                reauthentication.
            UpdateFailed: If data fetching fails for other reasons - an
                authentication rejection still inside the grace period, or an
                always-fetched resource that was denied, rate limited or
                unreachable.
        """
        tasks = self._build_update_tasks()
        # return_exceptions so one resource cannot take the whole poll down with
        # it: a token scoped to some resources but not others would otherwise
        # make every cycle fail on the first 403, leaving the integration with no
        # data at all even though most endpoints answered fine.
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        outcome = self._triage_results(tasks, results)
        if "sensors" in outcome.payload:
            outcome.payload["sensors"] = _flatten_sensors(outcome.payload["sensors"])
        # Cycle-fatal conditions first - a rejected token, an always-fetched
        # resource that could not be reached - then the per-resource bookkeeping
        # for what merely degraded. Deciding the fatal cases up front means a
        # server that is dropping connections reports exactly that, instead of a
        # misleading "insufficient read permission" from a 403 in the same cycle.
        self._handle_failed_resources(outcome)
        transient = self._classify_transient_resource_failures(outcome)

        self._clear_auth_failure()
        data: dict[str, Any] = outcome.payload
        # Carry transiently-failed resources forward before defaulting, so their
        # entities keep their last state instead of the dynamic-entity sync
        # removing them over an empty list.
        self._retain_last_known_good(data, transient)
        data.setdefault("services", {})
        data.setdefault("disks", [])
        data.setdefault("pools", [])
        data.setdefault("lxc_containers", [])
        data.setdefault("docker_containers", [])
        data.setdefault("vm_machines", [])
        data.setdefault("sensors", [])
        if "docker_engine_containers" in data:
            data["docker_containers"] = _merge_docker_engine_state(
                data["docker_containers"],
                data.pop("docker_engine_containers"),
            )
        elif data["docker_containers"]:
            # Engine proxy was transiently unavailable this poll; keep the
            # last-known running state instead of blanking every container.
            data["docker_containers"] = _carry_forward_docker_engine_state(
                data["docker_containers"],
                (self.data or {}).get("docker_containers") or [],
            )
        return data
