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
    MOSApiClientNotFoundError,
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
    CONF_ENABLE_NUT,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SENSORS,
    CONF_ENABLE_SERVICES,
    CONF_ENABLE_VM,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_NUT,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SENSORS,
    DEFAULT_ENABLE_SERVICES,
    DEFAULT_ENABLE_VM,
    DOCKER_LABELS_KEPT,
    LOGGER,
    PERMISSION_RESOURCE_BY_KEY,
    READ_PERMISSION_RESOURCES,
    RESOURCE_STALE_GRACE_PERIOD,
    RESOURCE_STALE_MIN_FAILURES,
)
from custom_components.mos.coordinator.docker_stats import NO_DOCKER_STATS, DockerStatsCollector, DockerStatsContext
from custom_components.mos.coordinator.docker_templates import DockerTemplateCache, resolve_icon, resolve_web_ui_url
from custom_components.mos.coordinator.guest_icons import GuestIconCache
from custom_components.mos.entity_utils import has_read_access, has_write_access
from homeassistant.const import CONF_HOST
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
    not_found_errors: dict[str, BaseException] = field(default_factory=dict)
    communication_errors: dict[str, BaseException] = field(default_factory=dict)

    def transient_resource_errors(self) -> dict[str, BaseException]:
        """
        Per-resource failures that should not tear the resource down (403 / 404 / 429 / unreachable).

        All of them are transient from the coordinator's point of view: the
        resource keeps its last-known-good data and is retried on the next poll.
        Merged here so the update flow has a single view of "which resources
        failed but must be preserved".

        404s are included, but most of them are filtered back out one step later:
        an endpoint the server has never served is not a failure to preserve
        anything for, it is a feature this MOS version does not have (see
        ``_classify_transient_resource_failures``). What stays here is a 404 on a
        resource that did answer before, which is a genuine regression and is
        treated like any other unreachable resource.

        Authentication errors are deliberately absent. A rejected token is a
        property of the connection, not of one endpoint, so a 401 anywhere fails
        the whole cycle - see ``_handle_failed_resources``.
        """
        return {
            **self.permission_errors,
            **self.rate_limit_errors,
            **self.not_found_errors,
            **self.communication_errors,
        }

    def unreachable_errors(self) -> dict[str, BaseException]:
        """
        Failures that mean "no answer from this endpoint" - a transport error or a 404.

        Used for the always-fetched resources, where the distinction does not
        matter: osinfo or system_load answering 404 is as fatal to the cycle as
        the connection dropping, since a server without them is not one this
        integration can present anything from.
        """
        return {**self.communication_errors, **self.not_found_errors}


# The fields ``_merge_docker_engine_state`` lifts out of the raw Docker Engine
# payload, named once so ``_carry_forward_docker_engine_state`` cannot fall behind
# and silently blank one of them out on a poll where the proxy is unavailable.
DOCKER_ENGINE_MERGED_FIELDS = (
    "state",
    "container_id",
    "health",
    "labels",
    "ports",
    "network_mode",
)


def _merge_docker_engine_state(
    containers: list[dict[str, Any]],
    engine_containers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge live Docker Engine state into MOS's docker container list.

    ``/docker/mos/containers`` has no running-state field; the raw Docker
    Engine proxy's ``/containers/json`` does, keyed by name (with a leading
    slash, per Docker's own ``Names`` convention). The same payload also carries
    everything else the engine knows and MOS's own container list does not - the
    ``mos.webui`` label, the live port mapping, health, and the container id -
    so it is harvested here rather than fetched a second time.

    Only the labels in ``DOCKER_LABELS_KEPT`` are carried over. The rest is
    free-form text from the image author or the user, and this payload reaches
    the diagnostics download.

    ``container_id`` matters beyond identification: MOS recreates a container
    when its template is edited, so a changed id is the signal that any cached
    template for that container is out of date.

    ``health`` is flattened to Docker's status string. Note that MOS answers with
    ``"none"`` rather than omitting the field when a container defines no
    healthcheck, and that the status of a stopped container is whatever it was
    left at - neither is a health verdict, and both are handled where the value
    is consumed.
    """
    engine_by_name: dict[str, dict[str, Any]] = {}
    for engine_container in engine_containers:
        for raw_name in engine_container.get("Names") or []:
            engine_by_name[raw_name.lstrip("/")] = engine_container

    merged: list[dict[str, Any]] = []
    for container in containers:
        name: str = container.get("name") or ""
        engine_container = engine_by_name.get(name) or {}
        merged.append(
            {
                **container,
                "state": engine_container.get("State"),
                "container_id": engine_container.get("Id"),
                "health": (engine_container.get("Health") or {}).get("Status"),
                "labels": {
                    label: value
                    for label, value in (engine_container.get("Labels") or {}).items()
                    if label in DOCKER_LABELS_KEPT
                },
                "ports": engine_container.get("Ports") or [],
                "network_mode": (engine_container.get("HostConfig") or {}).get("NetworkMode"),
            }
        )
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
    Preserve the last-known engine-derived fields when the proxy is absent.

    ``docker_engine_containers`` is merged into ``docker_containers`` and then
    dropped every poll, so it never lands in ``self.data`` where
    ``_retain_last_known_good`` could carry it forward. When the raw Docker
    Engine proxy is transiently unavailable (403/429) while the MOS container
    list itself still answers, re-attach everything ``_merge_docker_engine_state``
    contributes from the previously merged data (keyed by name) instead of
    letting every container's running state and web link blank out for a cycle.
    Containers unknown last poll (or on the first poll) get ``None``, so no stale
    value is invented.
    """
    previous_by_name: dict[str, dict[str, Any]] = {
        name: container for container in previous_containers if (name := container.get("name"))
    }
    return [
        {
            **container,
            **{
                field: previous_by_name.get(container.get("name") or "", {}).get(field)
                for field in DOCKER_ENGINE_MERGED_FIELDS
            },
        }
        for container in containers
    ]


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

    # Per-container MOS templates, backing the Docker icons and web links. Bound
    # lazily on first use rather than in ``_async_setup``, so a coordinator that
    # only ever polls still gets one; the class default is None and is never
    # mutated, so instances cannot share a cache (same reasoning as
    # ``forbidden_resources`` below).
    _docker_templates: DockerTemplateCache | None = None

    # Fetches per-container CPU and memory. Bound lazily on first use for the
    # same reason as ``_docker_templates`` above, and left unbound entirely on a
    # setup where no stats sensor is enabled - which is the default.
    _docker_stats: DockerStatsCollector | None = None

    # Resolves the icons MOS serves off its own web root for Docker containers,
    # LXC containers and VMs. Bound lazily for the same reason as the two caches
    # above.
    _guest_icons: GuestIconCache | None = None

    # Optional resources the token's scope denies reading. Filled from two
    # sources, because the token's own permission block is not complete: seeded
    # at setup from what the scope lists (see ``_seed_forbidden_resources``), and
    # extended at runtime whenever the server itself refuses a resource by name
    # (see ``_absorb_scope_denials``).
    #
    # The second source exists because MOS omits resources from that block that
    # it nonetheless enforces - ``nut`` is absent from a custom-mode scope on MOS
    # 0.5.x while ``/nut/status`` is still refused - so seeding alone leaves the
    # integration asking forever for something it will never be given.
    #
    # Fixing the token's scope is picked up by reloading the entry, for both
    # halves alike.
    #
    # Rebound rather than mutated (hence frozenset) - a mutable class attribute
    # would be shared by every coordinator instance in the process.
    forbidden_resources: frozenset[str] = frozenset()

    # Resources whose last poll failed transiently (a 429 rate limit or a
    # communication error) and are currently
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

    # Optional resources this server answered 404 for without ever having served
    # them: endpoints its MOS version does not have yet. Kept apart from every
    # failure category above because it is not a failure - there is no data to
    # retain, nothing to mark stale, and no entities to make unavailable. They
    # are still requested every poll, so an update that adds the endpoint is
    # picked up without a reload.
    _unsupported_resources: frozenset[str] = frozenset()

    # Resources that have returned data at least once since this coordinator was
    # created. This is what makes the distinction above possible: a data key
    # alone cannot tell "never served" from "served, then stopped", because every
    # optional resource is defaulted to an empty payload at the end of each cycle
    # and is therefore present either way.
    _answered_resources: frozenset[str] = frozenset()

    # The last ``error`` /nut/status reported for a UPS it could not read, so the
    # explanation is logged once instead of every poll. ``None`` means there is
    # currently nothing to report - see ``_log_unreadable_ups``.
    _nut_error: str | None = None

    @property
    def unsupported_resources(self) -> frozenset[str]:
        """
        Resources this MOS version has no endpoint for.

        Empty against a server new enough for every endpoint the integration
        knows about. Entities are simply not created for what is listed here.
        """
        return self._unsupported_resources

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
    def guest_icon_sources(self) -> dict[str, list[str]]:
        """
        Which guest configuration endpoints the icon lookup has given up on, and why.

        Kept out of ``forbidden_resources`` and ``unsupported_resources`` on
        purpose: those drive which resources are polled and whether entities go
        unavailable, and no entity is backed by these endpoints - losing one
        costs a picture, nothing more. This exists so a dump still says so,
        rather than leaving "my guests have no icons" to be guessed at.

        Empty on a server that answers both, and before the first poll.
        """
        cache = self._guest_icons
        if cache is None:
            return {"denied": [], "unsupported": []}
        return {
            "denied": sorted(cache.denied_sources),
            "unsupported": sorted(cache.unsupported_sources),
        }

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
        if wanted(CONF_ENABLE_NUT, DEFAULT_ENABLE_NUT, "nut"):
            tasks["nut"] = client.async_get_nut_status()
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
            elif isinstance(result, MOSApiClientNotFoundError):
                # Before the communication-error branch below, which it is a
                # subclass of - the point of the class is to be told apart here.
                outcome.not_found_errors[key] = result
            elif isinstance(result, MOSApiClientError):
                outcome.communication_errors[key] = result
            else:
                raise result
        return outcome

    def _classify_transient_resource_failures(self, outcome: _UpdateOutcome) -> set[str]:
        """
        Decide how to react to per-resource failures, and return the ones to preserve.

        A 429 or a communication error (timeout, dropped connection, 5xx) is
        transient by nature. Rather than dropping such a resource - which would
        empty it and make the dynamic-entity sync tear down its devices until a
        reload - the coordinator keeps that resource's last-known-good data (see
        ``_retain_last_known_good``) and retries it on the next poll.

        A scope denial is not transient and is taken out of this set first, in
        ``_absorb_scope_denials``: the server named a resource this token may not
        read, which no amount of retrying changes.

        The one exception is an always-fetched resource (osinfo, system_load):
        there is nothing meaningful to show without it, so the whole cycle fails
        (retryable) instead. Communication errors on those are caught earlier,
        in ``_handle_failed_resources``.

        A 404 is the exception to all of that, and only for a resource that has
        never returned data: the server does not have the endpoint, which is
        what a MOS version older than the endpoint answers. There is nothing to
        preserve, nothing to mark stale, and no entities to make unavailable -
        so it is recorded as unsupported, logged once, and left out of the
        degraded bookkeeping entirely. It is still requested on every poll, so a
        server that gains the endpoint in an update is picked up without a
        reload.

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
        denied = self._absorb_scope_denials(outcome)

        transient = set(outcome.transient_resource_errors()) - ALWAYS_FETCHED_RESOURCES - denied
        unsupported = self._classify_unsupported_resources(outcome)
        self._track_degraded_resources(outcome, transient - unsupported)
        return transient - unsupported

    def _absorb_scope_denials(self, outcome: _UpdateOutcome) -> set[str]:
        """
        Record resources the server refused by name, and stop asking for them.

        A permission error only reaches the coordinator when the server spelled
        out which resource the token may not read (see ``_raise_for_forbidden``
        in the API client), so this is a fact about the token's scope, not a
        server hiccup. Retrying it every 30 seconds for the lifetime of the entry
        can only produce the same refusal.

        This is the half of the scope that ``_seed_forbidden_resources`` cannot
        see. MOS enforces permissions it does not list: on 0.5.x a custom-mode
        token's ``resources`` block has no ``nut`` key at all, yet
        ``/nut/status`` is refused all the same. ``has_read_access`` reads a
        missing key as permitted - deliberately, so an unknown name never
        silently removes entities - which left exactly one gap: a resource the
        server enforces and the scope never mentions. Before this, that gap meant
        the UPS entities never appeared, the endpoint was re-requested on every
        poll forever, and nothing in the log said why.

        Newly denied resources are *not* dropped from ``data``. Their entities
        keep their registry entries, their history and their names, and go
        unavailable instead (``_update_stale_resources`` counts anything
        forbidden as stale) - the same treatment a resource gets when it has been
        failing too long to still be believed. Deleting them would take the
        recorder history with it over what may well be a scope the user is about
        to widen again.

        Returns:
            The resource keys denied for the first time this cycle.

        """
        denied = set(outcome.permission_errors) - ALWAYS_FETCHED_RESOURCES - self.forbidden_resources
        if not denied:
            return set()

        # A MOS scope covers a whole first path segment, so one refusal settles
        # every resource governed by the same name: /docker/mos/containers being
        # denied means the raw Engine proxy is too, whether or not it happened to
        # fail in this same cycle.
        scopes = {PERMISSION_RESOURCE_BY_KEY[key] for key in denied if key in PERMISSION_RESOURCE_BY_KEY}
        denied |= {key for key, resource in READ_PERMISSION_RESOURCES.items() if resource in scopes}

        LOGGER.warning(
            "API token has no read access to %s - the server refused it, even though the token's own "
            "permission list does not say so. No entities are created for it, and it will not be requested "
            "again. Grant the token read access to %s in the MOS web UI and reload the integration, "
            "or switch the category off in the integration options",
            ", ".join(sorted(denied)),
            ", ".join(sorted(scopes)) or "it",
        )
        self.forbidden_resources |= frozenset(denied)
        return denied

    def _classify_unsupported_resources(self, outcome: _UpdateOutcome) -> set[str]:
        """
        Record which optional resources this server simply does not have, and say so once.

        A 404 counts as "not supported" only for a resource that has never
        answered in this coordinator's lifetime. One that answered before and
        404s now is a regression on the server's side, not a missing feature, so
        it is left in the transient set and handled like any other endpoint that
        stopped responding.

        The message is deliberately informational: on a MOS version older than
        an endpoint this is the expected, harmless outcome, and the user has
        nothing to fix - so it explains what is missing and what makes it appear,
        rather than reporting a problem.

        Returns:
            The optional resource keys this server has no endpoint for.

        """
        self._answered_resources |= outcome.payload.keys()
        unsupported = {
            key
            for key in outcome.not_found_errors
            if key not in self._answered_resources and key not in ALWAYS_FETCHED_RESOURCES
        }

        newly_unsupported = sorted(unsupported - self._unsupported_resources)
        if newly_unsupported:
            LOGGER.info(
                "This MOS server has no endpoint for %s (HTTP 404) - its MOS version predates it. "
                "No entities are created for it; update MOS and they appear on their own, no reload needed. "
                "You can also switch the category off in the integration options to stop asking for it",
                ", ".join(newly_unsupported),
            )
        now_supported = sorted(self._unsupported_resources - unsupported)
        if now_supported:
            LOGGER.info("This MOS server now provides %s - creating its entities", ", ".join(now_supported))

        self._unsupported_resources = frozenset(unsupported)
        return unsupported

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

        Only resources that have satisfied *both* halves of the guard qualify,
        plus anything the token's scope forbids: a resource that will not be
        requested again has stopped updating for good, which is the stronger form
        of the same statement. For a scope denied since setup that changes
        nothing - there are no entities to mark - but a resource denied while
        running keeps its entities and its history and reports itself
        unavailable, rather than showing the values it happened to have when the
        permission went away.

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
            | self.forbidden_resources
        ) - ALWAYS_FETCHED_RESOURCES
        if stale == self._stale_resources:
            return

        # Scope denials are excluded from this message, not from the set: they
        # are unavailable for a different reason than "stopped answering", they
        # do not recover on their own, and ``_absorb_scope_denials`` has already
        # said so in terms the user can act on.
        newly_stale = sorted(stale - self._stale_resources - self.forbidden_resources)
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
        newly_missing = sorted(newly & set(outcome.not_found_errors))
        newly_unreachable = sorted(newly & set(outcome.communication_errors))
        if newly_missing:
            # Only a resource that used to answer reaches this: one the server
            # never had is reported as unsupported instead and never enters the
            # transient set (see _classify_unsupported_resources).
            LOGGER.warning(
                "Server returned 404 for %s although it answered before - keeping last-known state and "
                "retrying on the next poll. If this persists, the endpoint was removed or renamed on the "
                "server: %s",
                ", ".join(newly_missing),
                outcome.not_found_errors[newly_missing[0]],
            )
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

    def _log_unreadable_ups(self, payload: dict[str, Any]) -> None:
        """
        Say once when the server knows a UPS but cannot read it.

        ``/nut/status`` carries an ``error`` in exactly one situation: NUT is
        configured on the server and querying it failed - a driver that is not
        running, or a UPS whose USB cable is on a different machine than the one
        MOS runs on. A server with NUT switched off answers ``reachable: false``
        and no error, and a working one has nothing to report either, so keying
        on the field's presence stays silent for everyone without a UPS and
        speaks up only for the person who configured one.

        A log line is the only place this can go. The UPS entities are created on
        the first reachable poll and never before (see
        ``async_setup_ups_entities``), so in this exact case there is no entity
        to carry the message - which is also why it is worth logging at all:
        without it the symptom is silence, and nothing anywhere says why. The
        raw payload including the error is in the diagnostics dump for the
        follow-up.

        Repeats only when the error text changes, and rearms once it clears, so
        a UPS that fails again later is reported again rather than suppressed by
        a stale note from hours ago.
        """
        error = payload.get("error") if not payload.get("reachable") else None
        if error == self._nut_error:
            return
        if error:
            LOGGER.warning(
                "MOS knows a UPS but cannot read it, so no UPS entities are created - "
                "check the NUT configuration on the server: %s",
                # The server passes the failed command's output through verbatim,
                # newlines and all, and a log record is one line.
                " ".join(str(error).split()),
            )
        self._nut_error = error

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

        A 404 counts here too: a server that does not have /osinfo at all is not
        a MOS server this integration can read anything from, so it fails the
        cycle rather than being reported as an unsupported endpoint.

        Raises:
            UpdateFailed: If osinfo or system_load hit a communication error.

        """
        unreachable = outcome.unreachable_errors()
        unreachable_required = set(unreachable) & ALWAYS_FETCHED_RESOURCES
        if not unreachable_required:
            return

        exception = unreachable[min(unreachable_required)]
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
                                          # with the engine-derived fields merged in from
                                          # the raw Docker Engine proxy
                                          # (/docker/containers/json), plus "icon_url" and
                                          # "web_ui_url" from the cached MOS template
            "vm_machines": [...],      # VMs from /vm/machines/usage
            "sensors": [...],       # Hardware readings from /sensors, flattened
                                     # from their per-category grouping into one
                                     # list, each item tagged with "category"
            "nut": {...},           # UPS status from /nut/status; {"reachable": False}
                                     # when no UPS is attached, which is a normal
                                     # answer rather than a failure
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
        server hiccup. An endpoint the server does not have at all (404, i.e. a
        MOS version older than that endpoint) is not treated as a failure: it is
        reported once and left out, and starts working on its own if a MOS update
        adds it. Only a rejected token (401, which is a property of the
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
        # removing them over an empty list. Scope-denied resources are carried
        # forward for the same reason - their entities are marked unavailable
        # rather than deleted - and cost nothing when the denial predates the
        # first poll, since there is no previous data to carry.
        self._retain_last_known_good(data, transient | self.forbidden_resources)
        data.setdefault("services", {})
        data.setdefault("disks", [])
        data.setdefault("pools", [])
        data.setdefault("lxc_containers", [])
        data.setdefault("docker_containers", [])
        data.setdefault("vm_machines", [])
        data.setdefault("sensors", [])
        # Defaults to an empty payload rather than {"reachable": False}: "not
        # fetched" and "fetched, no UPS" must stay distinguishable, and an empty
        # dict reads as unreachable everywhere it is consumed anyway.
        data.setdefault("nut", {})
        self._log_unreadable_ups(data["nut"])
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
        data["docker_containers"] = await self._async_add_docker_template_data(data["docker_containers"])
        data["docker_containers"] = await self._async_add_docker_stats(data["docker_containers"])
        data["lxc_containers"] = await self._guest_icon_cache.async_add_lxc_icons(data["lxc_containers"])
        data["vm_machines"] = await self._guest_icon_cache.async_add_vm_icons(data["vm_machines"])
        return data

    @property
    def _guest_icon_cache(self) -> GuestIconCache:
        """
        Return the shared guest icon cache, creating it on first use.

        Returns:
            The cache bound to this entry's API client.

        """
        if self._guest_icons is None:
            self._guest_icons = GuestIconCache(self.config_entry.runtime_data.client)
        return self._guest_icons

    async def _async_add_docker_stats(self, containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Stamp each Docker container with its live CPU and memory figures.

        Which containers are measured is decided by the sensors themselves rather
        than by an option: every Docker stats sensor registers a
        ``DockerStatsContext`` when it is added, so this asks the engine only
        about containers something is currently displaying. A user who disabled
        the sensors for a container - or who never switched the category on, in
        which case the sensors do not exist - costs no requests at all. This is
        the "only fetch data for active entities" this coordinator has always
        claimed to do, finally with a caller that needs it.

        Runs last, after the engine merge and the template pass, because it needs
        the merged ``state`` to skip stopped containers.

        Note that the very first poll of a config entry measures nothing: it runs
        inside ``async_config_entry_first_refresh()``, before any entity has been
        added, so no context exists yet. The sensors therefore read unknown for
        one cycle after a start or reload, and fill in on the next.

        Returns:
            The containers, each with the ``DOCKER_STATS_FIELDS`` added (all
            ``None`` for a container that was not measured).

        """
        if not containers:
            return containers

        wanted = {context.name for context in self.async_contexts() if isinstance(context, DockerStatsContext)}
        if not wanted:
            return [{**container, **NO_DOCKER_STATS} for container in containers]

        if self._docker_stats is None:
            self._docker_stats = DockerStatsCollector(self.config_entry.runtime_data.client)
        collected = await self._docker_stats.async_collect(containers, wanted)
        # Unmeasured containers are blanked rather than left at their previous
        # values: a frozen CPU reading is indistinguishable from a live one.
        return [
            {**container, **collected.get(container.get("name") or "", NO_DOCKER_STATS)} for container in containers
        ]

    async def _async_add_docker_template_data(self, containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Stamp each Docker container with its icon URL and resolved web link.

        Both come from the container's MOS template, which is cached and only
        re-fetched when a container is new or has been recreated - so this
        normally issues no requests at all. Runs after the engine merge because
        the cache keys on the container id that merge provides, and because the
        live port mapping decides the web link for a running container.

        The icon prefers the copy MOS serves itself (``/docker_icons/<name>.png``)
        and falls back to the template's URL, which normally points at a public
        CDN. Same picture either way, but the local one also loads on a dashboard
        whose browser has no internet access.

        Returns:
            The containers, each with ``icon_url`` and ``web_ui_url`` added
            (either may be ``None``).

        """
        if not containers:
            return containers

        if self._docker_templates is None:
            self._docker_templates = DockerTemplateCache(self.config_entry.runtime_data.client)
        await self._docker_templates.async_refresh(containers)

        host = self.config_entry.data.get(CONF_HOST)
        decorated: list[dict[str, Any]] = []
        for container in containers:
            name = container.get("name") or ""
            template = self._docker_templates.get(name)
            decorated.append(
                {
                    **container,
                    "icon_url": await self._guest_icon_cache.async_docker_icon_url(name) or resolve_icon(template),
                    "web_ui_url": resolve_web_ui_url(container, template, host),
                }
            )
        return decorated
