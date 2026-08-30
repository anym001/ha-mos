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
- The fetches run concurrently, paced by the client's rate limiter rather than
  by anything here. Sequentially - the shape ``DockerTemplateCache`` gets away
  with, because it is a no-op on almost every poll - the pacing would apply
  twice over and a poll would spend as long again waiting between requests as it
  does issuing them.
- The CPU percentage is a delta across polls, so the previous poll's counters
  are the only state this module keeps. Docker reports cumulative counters
  rather than a percentage, and the client asks for them one-shot instead of
  having Docker take its own second sample per request (see
  ``async_get_docker_container_stats``). The figure is therefore averaged over
  the scan interval rather than over one second, which is both cheaper and
  steadier.
- No derived figure is cached or carried forward. A CPU reading that failed to
  refresh is not worth keeping: unlike an icon or a web link, a stale value here
  is indistinguishable from a live one and would be read as current.

Nothing in here re-raises an API failure. A container that cannot be measured
reports no figures for that poll; the rest of the poll, including that
container's state and switch, is unaffected.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
import time
from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientError
from custom_components.mos.const import LOGGER, MAX_SCAN_INTERVAL

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

# How long an unmeasured container keeps its CPU counters, in seconds. Two full
# scan intervals at the slowest polling the options flow allows, so a container
# that is still being measured can never lose them; see
# ``DockerStatsCollector._prune_cpu_samples``.
CPU_SAMPLE_TTL = 2 * MAX_SCAN_INTERVAL


@dataclass(frozen=True)
class CpuSample:
    """
    One reading of the cumulative CPU counters a percentage is derived from.

    Attributes:
        usage: Nanoseconds of CPU time the container has consumed in total.
        system: Nanoseconds of CPU time the whole machine has consumed in total.
        cpus: How many cores were online when the reading was taken.

    """

    usage: int
    system: int
    cpus: int


def cpu_sample(payload: dict[str, Any]) -> CpuSample | None:
    """
    Extract the cumulative CPU counters from a raw stats payload.

    Returns:
        The sample, or ``None`` when the engine reported no counters or no core
        count - neither of which a percentage can be derived without.

    """
    cpu_stats = payload.get("cpu_stats") or {}
    usage = (cpu_stats.get("cpu_usage") or {}).get("total_usage")
    system = cpu_stats.get("system_cpu_usage")
    # ``online_cpus`` is absent on older engines, where the per-CPU breakdown is
    # the only way to count them.
    cpus = cpu_stats.get("online_cpus") or len((cpu_stats.get("cpu_usage") or {}).get("percpu_usage") or [])
    if usage is None or system is None or not cpus:
        return None
    return CpuSample(usage=usage, system=system, cpus=cpus)


def _cpu_percent(current: CpuSample | None, previous: CpuSample | None) -> float | None:
    """
    Derive CPU usage in percent from two readings of the cumulative counters.

    Docker does not report a percentage; it reports counters, and the figure
    ``docker stats`` shows is computed from how far the container's own counter
    moved against how far the whole machine's did over the same interval.
    Multiplying by the CPU count restores the familiar scale where one fully-busy
    core reads as 100% and a container using two cores reads as 200%.

    A counter that moved backwards means the container was recreated and started
    counting again, so the two readings do not span one interval and no figure
    can be derived from them.

    Returns:
        The percentage, or ``None`` when the two readings cannot support one - a
        container measured for the first time, one whose counters reset, or two
        readings the machine counter did not advance between. ``None`` rather
        than ``0.0`` on purpose: a zero would be indistinguishable from a
        genuinely idle container.

    """
    if current is None or previous is None:
        return None

    cpu_delta = current.usage - previous.usage
    system_delta = current.system - previous.system
    if system_delta <= 0 or cpu_delta < 0:
        return None
    return round(cpu_delta / system_delta * current.cpus * 100, 2)


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


def parse_stats(payload: dict[str, Any], previous: CpuSample | None = None) -> dict[str, Any]:
    """
    Reduce a raw Docker stats payload to the fields the sensors read.

    Args:
        payload: The raw stats payload for one container.
        previous: The same container's counters as of the previous poll, against
            which the CPU percentage is measured. Without one the memory figures
            are still reported and the CPU percentage is ``None``.

    Returns:
        The ``DOCKER_STATS_FIELDS``, each either a number or ``None``.

    """
    used, limit, percent = _memory(payload)
    return {
        "stats_cpu_percent": _cpu_percent(cpu_sample(payload), previous),
        "stats_memory_bytes": used,
        "stats_memory_limit_bytes": limit,
        "stats_memory_percent": percent,
    }


class DockerStatsCollector:
    """
    Fetches live usage for the running containers something is watching.

    The one thing it keeps between polls is each container's CPU counters, which
    the next poll measures its own against. One collector serves both the Docker
    containers and the Compose stack members, so a container reached from either
    side is measured against its own previous reading.

    Attributes:
        _client: The API client the stats are fetched through.
        _cpu_samples: Each measured container's last counters and when they were
            taken, keyed by container name.

    """

    def __init__(self, client: MOSApiClient) -> None:
        """Initialize the collector bound to an API client."""
        self._client = client
        self._cpu_samples: dict[str, tuple[CpuSample, float]] = {}

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

        A container measured for the first time reports its memory but no CPU
        percentage, since there is no earlier reading to measure against. It
        fills in on the next poll.

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

        now = time.monotonic()
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
                stored = self._cpu_samples.get(name)
                collected[name] = parse_stats(result, stored[0] if stored else None)
                if (sample := cpu_sample(result)) is not None:
                    self._cpu_samples[name] = (sample, now)
        self._prune_cpu_samples(now)
        return collected

    def _prune_cpu_samples(self, now: float) -> None:
        """
        Drop the counters of containers that have stopped being measured.

        Purely a bound on memory: a container that is deleted, renamed or simply
        switched off would otherwise keep its entry for as long as Home Assistant
        runs. Nothing about the figures depends on this, because a delta stays
        correct however far apart its two readings are - it just describes a
        longer interval.

        The window is two full scan intervals at the longest interval the options
        flow allows, so a container that is still being polled can never lose its
        counters no matter how the user has configured the integration.
        """
        cutoff = now - CPU_SAMPLE_TTL
        self._cpu_samples = {name: entry for name, entry in self._cpu_samples.items() if entry[1] >= cutoff}
