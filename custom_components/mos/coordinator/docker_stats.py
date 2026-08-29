"""
Per-container Docker resource usage for mos.

MOS reports what a Docker container *is* - its image, its update status, its
template - but never what it currently costs. LXC containers and VMs both get
CPU and memory from a ``/usage`` endpoint; Docker has no equivalent, so the
figures have to come from the Docker Engine's own stats endpoint, which answers
for one container at a time.

That per-container shape is what drives every decision in this module:

- Only containers that are *running* and that something is actually watching are
  fetched. Docker answers for a stopped container with zeroes, and a request per
  container per poll is not worth spending on a sensor nobody enabled.
- The fetches run concurrently. Sequentially - the shape
  ``DockerTemplateCache`` gets away with, because it is a no-op on almost every
  poll - fifty containers would take about fifty seconds, since each stats call
  blocks for roughly a second while Docker takes its second sample. Through the
  client's rate limiter the same fifty take about ten, at exactly the same
  requests-per-second the limiter allows anything else.
- Nothing is cached or carried forward. A CPU reading that failed to refresh is
  not worth keeping: unlike an icon or a web link, a stale value here is
  indistinguishable from a live one and would be read as current.

Nothing in here re-raises an API failure. A container that cannot be measured
reports no figures for that poll; the rest of the poll, including that
container's state and switch, is unaffected.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientError
from custom_components.mos.const import LOGGER

if TYPE_CHECKING:
    from custom_components.mos.api import MOSApiClient


@dataclass(frozen=True)
class DockerStatsContext:
    """
    A running stats sensor's request to have its container measured.

    Passed as the coordinator context of every Docker stats sensor, which is how
    the coordinator learns which containers to spend a request on. Home Assistant
    only registers a listener for entities that are actually added, so a sensor
    the user disabled contributes no context and its container drops out of the
    poll on the next reload - which Home Assistant schedules by itself, 30
    seconds after any ``disabled_by`` change.

    A dedicated type rather than the bare container name: contexts from every
    platform land in the same ``async_contexts()`` stream, and a future
    context-aware entity elsewhere in the integration must not be mistaken for a
    request to measure a container that happens to share its name.
    """

    name: str


# The fields ``parse_stats`` contributes to a container payload, named once so
# the "no figures this poll" case can blank exactly these and nothing else.
DOCKER_STATS_FIELDS = (
    "stats_cpu_percent",
    "stats_memory_bytes",
    "stats_memory_limit_bytes",
    "stats_memory_percent",
)

# Blanks for a container that was not measured this poll. Deliberately not the
# previous values: see the module docstring on why stats are never carried
# forward.
NO_DOCKER_STATS: dict[str, Any] = dict.fromkeys(DOCKER_STATS_FIELDS)


def _cpu_percent(payload: dict[str, Any]) -> float | None:
    """
    Derive CPU usage in percent from the two samples in a stats payload.

    Docker does not report a percentage; it reports cumulative counters, and the
    figure ``docker stats`` shows is computed from how far the container's own
    counter moved against how far the whole machine's did over the same
    interval. Multiplying by the CPU count restores the familiar scale where one
    fully-busy core reads as 100% and a container using two cores reads as 200%.

    Returns:
        The percentage, or ``None`` when the payload cannot support one - a
        container so freshly started that both samples are the same instant, or
        an engine that reported no counters at all. ``None`` rather than ``0.0``
        on purpose: a zero would be indistinguishable from a genuinely idle
        container.

    """
    cpu_stats = payload.get("cpu_stats") or {}
    previous = payload.get("precpu_stats") or {}
    usage = (cpu_stats.get("cpu_usage") or {}).get("total_usage")
    previous_usage = (previous.get("cpu_usage") or {}).get("total_usage")
    system = cpu_stats.get("system_cpu_usage")
    previous_system = previous.get("system_cpu_usage")
    if usage is None or previous_usage is None or system is None or previous_system is None:
        return None

    cpu_delta = usage - previous_usage
    system_delta = system - previous_system
    if system_delta <= 0 or cpu_delta < 0:
        return None

    # ``online_cpus`` is absent on older engines, where the per-CPU breakdown is
    # the only way to count them.
    cpus = cpu_stats.get("online_cpus") or len((cpu_stats.get("cpu_usage") or {}).get("percpu_usage") or [])
    if not cpus:
        return None
    return round(cpu_delta / system_delta * cpus * 100, 2)


def _memory(payload: dict[str, Any]) -> tuple[int | None, int | None, float | None]:
    """
    Derive used bytes, the limit, and the percentage between them.

    ``memory_stats.usage`` counts page cache the kernel is holding on the
    container's behalf and would drop under pressure, so reporting it raw makes
    every container look far hungrier than it is. Subtracting the reclaimable
    part is what ``docker stats`` shows, and the field it lives in was renamed
    across cgroup versions - hence the fallback chain.

    Note that a container with no memory limit of its own is reported by Docker
    as limited to the host's entire RAM. The percentage is then "of the whole
    NAS", not "of this container's budget"; that is Docker's own convention and
    is left as-is rather than second-guessed here.

    Returns:
        ``(used_bytes, limit_bytes, percent)``, any of which may be ``None`` when
        the engine did not report the underlying field.

    """
    memory_stats = payload.get("memory_stats") or {}
    usage = memory_stats.get("usage")
    limit = memory_stats.get("limit") or None
    if usage is None:
        return None, limit, None

    detail = memory_stats.get("stats") or {}
    # cgroup v2 calls it inactive_file; cgroup v1 reports total_inactive_file for
    # the whole hierarchy and cache for the container alone.
    reclaimable = detail.get("inactive_file")
    if reclaimable is None:
        reclaimable = detail.get("total_inactive_file")
    if reclaimable is None:
        reclaimable = detail.get("cache")

    used = max(usage - (reclaimable or 0), 0)
    percent = round(used / limit * 100, 2) if limit else None
    return used, limit, percent


def parse_stats(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Reduce a raw Docker stats payload to the fields the sensors read.

    Returns:
        The ``DOCKER_STATS_FIELDS``, each either a number or ``None``.

    """
    used, limit, percent = _memory(payload)
    return {
        "stats_cpu_percent": _cpu_percent(payload),
        "stats_memory_bytes": used,
        "stats_memory_limit_bytes": limit,
        "stats_memory_percent": percent,
    }


class DockerStatsCollector:
    """
    Fetches live usage for the running containers something is watching.

    Holds no state between polls - there is nothing worth caching, since every
    figure it produces is stale the moment the next poll starts.
    """

    def __init__(self, client: MOSApiClient) -> None:
        """Initialize the collector bound to an API client."""
        self._client = client

    async def async_collect(self, containers: list[dict[str, Any]], wanted: set[str]) -> dict[str, dict[str, Any]]:
        """
        Measure every wanted container that is currently running.

        Returns:
            Parsed stats keyed by container name. Containers that were skipped or
            whose request failed are simply absent, which the caller renders as
            "no figures this poll" rather than as an error.

        """
        targets = [
            name
            for container in containers
            if container.get("state") == "running" and (name := container.get("name")) and name in wanted
        ]
        return await self.async_measure(targets)

    async def async_measure(self, names: Iterable[str]) -> dict[str, dict[str, Any]]:
        """
        Measure each named container, whether or not MOS knows the name.

        Split out of ``async_collect`` for the Compose stacks, whose members are
        generated containers that appear only in the raw engine list: they have
        no MOS payload to carry a ``state``, so their caller is the one that
        knows which of them are running.

        Returns:
            Parsed stats keyed by container name, with any whose request failed
            simply absent.

        """
        targets = list(names)
        if not targets:
            return {}

        # Concurrently, and paced by the client's own rate limiter rather than by
        # anything here: the limiter is per token, so stats queue behind - and
        # never outrun - the regular poll and any switch the user just toggled.
        results = await asyncio.gather(
            *(self._client.async_get_docker_container_stats(name) for name in targets),
            return_exceptions=True,
        )

        collected: dict[str, dict[str, Any]] = {}
        for name, result in zip(targets, results, strict=True):
            if isinstance(result, MOSApiClientError):
                LOGGER.debug("Could not fetch Docker stats for %s: %s", name, result)
            elif isinstance(result, BaseException):
                # Not an API failure, so not this module's to swallow - notably
                # asyncio.CancelledError, which return_exceptions captures like
                # anything else.
                raise result
            elif isinstance(result, dict):
                collected[name] = parse_stats(result)
        return collected
