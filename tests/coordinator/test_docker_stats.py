"""Tests for the per-container Docker stats collector."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.mos.api import MOSApiClientCommunicationError
from custom_components.mos.coordinator.docker_stats import DockerStatsCollector, DockerStatsContext, parse_stats


def _containers() -> list[dict[str, Any]]:
    """Return two merged container payloads, one running and one stopped."""
    return [
        {"name": "PushBits", "state": "running"},
        {"name": "nginx", "state": "exited"},
    ]


def test_parses_a_full_payload(mock_docker_stats: dict[str, Any]) -> None:
    """A complete payload yields all four figures.

    The fixture is 0.5s of CPU against 4s of machine time on 2 CPUs, and 96 MiB
    of usage minus 32 MiB of reclaimable cache against a 512 MiB limit.
    """
    assert parse_stats(mock_docker_stats) == {
        "stats_cpu_percent": 25.0,
        "stats_memory_bytes": 67_108_864,
        "stats_memory_limit_bytes": 536_870_912,
        "stats_memory_percent": 12.5,
    }


def test_reports_no_cpu_when_both_samples_are_the_same_instant(mock_docker_stats: dict[str, Any]) -> None:
    """A container too freshly started to have moved reports None, not zero.

    Zero would be indistinguishable from a genuinely idle container, which is a
    different and knowable thing.
    """
    payload = {**mock_docker_stats, "precpu_stats": mock_docker_stats["cpu_stats"]}

    assert parse_stats(payload)["stats_cpu_percent"] is None


def test_counts_cpus_from_the_per_cpu_breakdown(mock_docker_stats: dict[str, Any]) -> None:
    """An engine without ``online_cpus`` is counted from ``percpu_usage`` instead."""
    payload = {
        **mock_docker_stats,
        "cpu_stats": {
            "cpu_usage": {"total_usage": 1_500_000_000, "percpu_usage": [750_000_000, 750_000_000]},
            "system_cpu_usage": 40_000_000_000,
        },
    }

    assert parse_stats(payload)["stats_cpu_percent"] == 25.0


def test_reports_no_cpu_without_any_counters() -> None:
    """An engine that reported no CPU block at all yields None rather than raising."""
    assert parse_stats({})["stats_cpu_percent"] is None


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
