"""Tests for the per-container Docker stats collector."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.mos.api import MOSApiClientCommunicationError
from custom_components.mos.const import MAX_SCAN_INTERVAL
from custom_components.mos.coordinator import docker_stats
from custom_components.mos.coordinator.docker_stats import (
    CPU_SAMPLE_TTL,
    CpuSample,
    DockerStatsCollector,
    DockerStatsContext,
    cpu_sample,
    parse_stats,
)


class _FakeClock:
    """Stands in for the module's ``time`` so a retention window can be crossed."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the current fake reading.

        Returns:
            Seconds on the fake clock.

        """
        return self.now


def _containers() -> list[dict[str, Any]]:
    """Return two merged container payloads, one running and one stopped."""
    return [
        {"name": "PushBits", "state": "running"},
        {"name": "nginx", "state": "exited"},
    ]


def _earlier(usage: int = 1_000_000_000, system: int = 36_000_000_000, cpus: int = 2) -> CpuSample:
    """Return the reading the fixture payload is 0.5s of CPU against 4s of machine time ahead of."""
    return CpuSample(usage=usage, system=system, cpus=cpus)


def test_parses_a_full_payload(mock_docker_stats: dict[str, Any]) -> None:
    """A payload with an earlier reading to measure against yields all four figures.

    The fixture is 0.5s of CPU against 4s of machine time on 2 CPUs, and 96 MiB
    of usage minus 32 MiB of reclaimable cache against a 512 MiB limit.
    """
    assert parse_stats(mock_docker_stats, _earlier()) == {
        "stats_cpu_percent": 25.0,
        "stats_memory_bytes": 67_108_864,
        "stats_memory_limit_bytes": 536_870_912,
        "stats_memory_percent": 12.5,
    }


def test_reports_memory_but_no_cpu_on_a_first_reading(mock_docker_stats: dict[str, Any]) -> None:
    """Without an earlier reading the memory figures still stand and CPU is blank.

    Zero would be indistinguishable from a genuinely idle container, which is a
    different and knowable thing.
    """
    parsed = parse_stats(mock_docker_stats, None)

    assert parsed["stats_cpu_percent"] is None
    assert parsed["stats_memory_bytes"] == 67_108_864


def test_reports_no_cpu_when_the_machine_counter_has_not_moved(mock_docker_stats: dict[str, Any]) -> None:
    """Two readings the machine counter did not advance between support no percentage."""
    same_instant = _earlier(usage=1_000_000_000, system=40_000_000_000)

    assert parse_stats(mock_docker_stats, same_instant)["stats_cpu_percent"] is None


def test_reports_no_cpu_when_the_container_counter_reset(mock_docker_stats: dict[str, Any]) -> None:
    """A recreated container starts counting again, so the two readings span no interval."""
    before_restart = _earlier(usage=9_000_000_000)

    assert parse_stats(mock_docker_stats, before_restart)["stats_cpu_percent"] is None


def test_counts_cpus_from_the_per_cpu_breakdown(mock_docker_stats: dict[str, Any]) -> None:
    """An engine without ``online_cpus`` is counted from ``percpu_usage`` instead."""
    payload = {
        **mock_docker_stats,
        "cpu_stats": {
            "cpu_usage": {"total_usage": 1_500_000_000, "percpu_usage": [750_000_000, 750_000_000]},
            "system_cpu_usage": 40_000_000_000,
        },
    }

    assert parse_stats(payload, _earlier())["stats_cpu_percent"] == 25.0


def test_reports_no_cpu_without_any_counters() -> None:
    """An engine that reported no CPU block at all yields None rather than raising."""
    assert parse_stats({}, _earlier())["stats_cpu_percent"] is None
    assert cpu_sample({}) is None


@pytest.mark.parametrize(
    ("detail", "expected"),
    [
        pytest.param({"inactive_file": 33_554_432}, 67_108_864, id="cgroup-v2"),
        pytest.param({"total_inactive_file": 33_554_432}, 67_108_864, id="cgroup-v1-hierarchy"),
        pytest.param({"cache": 33_554_432}, 67_108_864, id="cgroup-v1-container"),
        pytest.param({}, 100_663_296, id="nothing-reclaimable"),
    ],
)
def test_subtracts_reclaimable_cache_under_either_cgroup_version(
    mock_docker_stats: dict[str, Any],
    detail: dict[str, int],
    expected: int,
) -> None:
    """The field holding reclaimable page cache was renamed across cgroup versions.

    Reporting ``usage`` raw makes every container look far hungrier than it is,
    so each spelling has to be recognized.
    """
    payload = {**mock_docker_stats, "memory_stats": {**mock_docker_stats["memory_stats"], "stats": detail}}

    assert parse_stats(payload)["stats_memory_bytes"] == expected


def test_reports_no_memory_percent_without_a_limit(mock_docker_stats: dict[str, Any]) -> None:
    """Without a limit there is nothing to take a percentage of."""
    payload = {**mock_docker_stats, "memory_stats": {**mock_docker_stats["memory_stats"], "limit": 0}}

    parsed = parse_stats(payload)

    assert parsed["stats_memory_limit_bytes"] is None
    assert parsed["stats_memory_percent"] is None


async def test_measures_only_running_and_wanted_containers(mock_client: AsyncMock) -> None:
    """Stopped containers and containers nothing is watching cost no request.

    A stopped container answers with zeroes rather than an error, so skipping it
    is what keeps the sensor blank instead of reporting a plausible-looking 0%.
    """
    collector = DockerStatsCollector(mock_client)

    collected = await collector.async_collect(_containers(), {"PushBits", "nginx"})

    assert set(collected) == {"PushBits"}
    mock_client.async_get_docker_container_stats.assert_awaited_once_with("PushBits")


async def test_measures_nothing_when_no_sensor_asks(mock_client: AsyncMock) -> None:
    """With no wanted names the collector issues no requests at all."""
    collector = DockerStatsCollector(mock_client)

    assert await collector.async_collect(_containers(), set()) == {}
    mock_client.async_get_docker_container_stats.assert_not_awaited()


async def test_cpu_fills_in_on_the_poll_after_the_first(mock_client: AsyncMock) -> None:
    """The first reading establishes the baseline; the next one derives a percentage.

    Memory needs no baseline and is reported straight away, so only the CPU
    figure is blank for that one cycle.
    """
    collector = DockerStatsCollector(mock_client)

    first = await collector.async_collect(_containers(), {"PushBits"})
    second = await collector.async_collect(_containers(), {"PushBits"})

    assert first["PushBits"]["stats_cpu_percent"] is None
    assert first["PushBits"]["stats_memory_bytes"] == 67_108_864
    assert second["PushBits"]["stats_cpu_percent"] == 25.0


async def test_each_container_is_measured_against_its_own_reading(mock_client: AsyncMock) -> None:
    """Counters are kept per container, so one container cannot skew another."""
    containers = [
        {"name": "PushBits", "state": "running"},
        {"name": "nginx", "state": "running"},
    ]
    collector = DockerStatsCollector(mock_client)

    await collector.async_collect(containers, {"PushBits"})
    both = await collector.async_collect(containers, {"PushBits", "nginx"})

    assert both["PushBits"]["stats_cpu_percent"] == 25.0
    assert both["nginx"]["stats_cpu_percent"] is None


async def test_both_measuring_paths_share_one_set_of_readings(mock_client: AsyncMock) -> None:
    """A container reached as a Compose member and as a Docker container has one baseline.

    The coordinator holds a single collector for both, so whichever path measures
    a container first is what the other measures against.
    """
    collector = DockerStatsCollector(mock_client)

    await collector.async_measure(["PushBits"])
    collected = await collector.async_collect(_containers(), {"PushBits"})

    assert collected["PushBits"]["stats_cpu_percent"] == 25.0


async def test_a_container_that_stops_being_measured_is_forgotten(
    mock_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counters are dropped once nothing has refreshed them for the retention window.

    The container then reads as if measured for the first time, which is what a
    dropped baseline means.
    """
    clock = _FakeClock()
    monkeypatch.setattr(docker_stats, "time", clock)
    collector = DockerStatsCollector(mock_client)

    await collector.async_measure(["PushBits"])
    clock.now += CPU_SAMPLE_TTL + 1
    await collector.async_measure(["nginx"])
    collected = await collector.async_measure(["PushBits"])

    assert collected["PushBits"]["stats_cpu_percent"] is None


async def test_a_container_still_being_measured_keeps_its_counters(
    mock_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Polling at the slowest interval the options flow allows never loses a baseline."""
    clock = _FakeClock()
    monkeypatch.setattr(docker_stats, "time", clock)
    collector = DockerStatsCollector(mock_client)

    await collector.async_measure(["PushBits"])
    clock.now += MAX_SCAN_INTERVAL
    collected = await collector.async_measure(["PushBits"])

    assert collected["PushBits"]["stats_cpu_percent"] == 25.0


async def test_one_failing_container_does_not_take_the_others_down(mock_client: AsyncMock) -> None:
    """A container that cannot be measured is simply absent from the result."""
    containers = [
        {"name": "PushBits", "state": "running"},
        {"name": "nginx", "state": "running"},
    ]

    async def _stats(name: str) -> dict[str, Any]:
        if name == "PushBits":
            raise MOSApiClientCommunicationError("boom")
        return {"memory_stats": {"usage": 1024, "limit": 2048}}

    mock_client.async_get_docker_container_stats.side_effect = _stats
    collector = DockerStatsCollector(mock_client)

    collected = await collector.async_collect(containers, {"PushBits", "nginx"})

    assert set(collected) == {"nginx"}


async def test_cancellation_is_not_swallowed(mock_client: AsyncMock) -> None:
    """Only API errors are absorbed; a cancelled poll must still cancel.

    ``asyncio.gather(return_exceptions=True)`` captures CancelledError like any
    other exception, so it has to be re-raised explicitly.
    """
    mock_client.async_get_docker_container_stats.side_effect = asyncio.CancelledError
    collector = DockerStatsCollector(mock_client)

    with pytest.raises(asyncio.CancelledError):
        await collector.async_collect(_containers(), {"PushBits"})


def test_context_distinguishes_containers_by_type() -> None:
    """The context is a dedicated type, so a bare name cannot be mistaken for one."""
    assert DockerStatsContext("PushBits") == DockerStatsContext("PushBits")
    assert DockerStatsContext("PushBits") != DockerStatsContext("nginx")
    assert DockerStatsContext("PushBits") != "PushBits"
