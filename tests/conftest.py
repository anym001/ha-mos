"""Shared fixtures for mos tests."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClient
from custom_components.mos.const import CONF_API_TOKEN, DOMAIN
import custom_components.mos.coordinator.base as coordinator_base
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for every test in this suite."""


class _FakeClock:
    """Stand-in for the ``time`` module, exposing a ``monotonic()`` the test drives."""

    def __init__(self, start: float = 1000.0) -> None:
        """Start the clock at an arbitrary but stable monotonic value."""
        self._now = start

    def monotonic(self) -> float:
        """Return the current fake monotonic time."""
        return self._now

    def advance(self, seconds: float) -> None:
        """Move the clock forward by `seconds`."""
        self._now += seconds


@pytest.fixture
def advance_clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], None]:
    """Give the coordinator a controllable clock and return a way to move it forward.

    Replaces the ``time`` reference inside the coordinator module rather than
    ``time.monotonic`` itself, so the fake clock cannot leak into Home
    Assistant's own timers - which matters for tests that run a fully set up
    integration.

    Drives both of the coordinator's time-based guards - the auth-failure grace
    period and the per-resource staleness threshold - so those tests stay
    independent of the scan interval and of the constants' exact values. A
    callable is handed back (rather than the clock object) so test modules need
    no cross-module import.
    """
    clock = _FakeClock()
    monkeypatch.setattr(coordinator_base, "time", clock)
    return clock.advance


@pytest.fixture
def mock_osinfo() -> dict[str, Any]:
    """Return a realistic ``/osinfo`` payload."""
    return {
        "hostname": "sirius",
        "mos": {
            "version": "0.5.0-stable",
            "channel": "stable",
            "build": "20260705-1111",
            "api": "1.4.0",
            "frontend": "1.4.0",
            "running_kernel": "6.1.0-mos",
            "recommended_kernel": "6.1.0-mos",
            "arch": "x86_64",
        },
        "cpu": {"brand": "Intel Xeon E-2288G"},
        "base": [{"os_name": "Debian", "os_version": "12"}],
        "uptime": {"since": "2026-07-24 20:13:48"},
    }


@pytest.fixture
def mock_services() -> dict[str, Any]:
    """Return a realistic ``/services`` payload."""
    return {
        "docker": {"running": False},
        "vm": {"running": True},
        "ssh": {"enabled": True},
        "samba": {"enabled": True},
        "nfs": {"enabled": False},
        "tailscale": {"online": True},
        "netbird": {"online": False},
    }


@pytest.fixture
def mock_disks() -> list[dict[str, Any]]:
    """Return a realistic ``/disks`` payload."""
    return [
        {
            "serial": "S1",
            "name": "vda",
            "model": "Samsung SSD 970",
            "size": 2147483648,
            "type": "ssd",
            "powerStatus": "active",
            "temperature": 32,
            "smartWarning": False,
            "preclearRunning": False,
        },
        {
            "serial": "S2",
            "name": "vdb",
            "model": "Seagate ST4000",
            "size": 21474836480,
            "type": "hdd",
            "powerStatus": "standby",
            "temperature": 41,
            "smartWarning": True,
            "preclearRunning": True,
        },
    ]


@pytest.fixture
def mock_pools() -> list[dict[str, Any]]:
    """Return a realistic ``/pools`` payload."""
    return [
        {
            "id": 1,
            "name": "Test1",
            "type": "xfs",
            "status": {
                "usagePercent": 42,
                "totalSpace": 987654321,
                "usedSpace": 864197532,
                "freeSpace": 123456789,
                "health": "healthy",
                "scrub_operation": False,
                "balance_operation": False,
            },
        },
        {
            "id": 2,
            "name": "Test2",
            "type": "btrfs",
            "status": {
                "usagePercent": 10,
                "totalSpace": 1111111111,
                "usedSpace": 123456790,
                "freeSpace": 987654321,
                "health": "degraded",
                "parity_operation": False,
            },
        },
    ]


@pytest.fixture
def mock_system_load() -> dict[str, Any]:
    """Return a realistic ``/system/load`` payload."""
    return {
        "cpu": {"load": 42.35},
        "temperature": {"main": 55.0, "max": 61.0, "min": 48.0},
        "memory": {
            "used": 1899659264,
            "total": 8589934592,
            "free": 6690275328,
            "installed": 8724152320,
            "reserved": 134217728,
            "breakdown": {
                "docker": {"bytes": 1073741824, "percentage": 12},
                "system": {"bytes": 536870912, "percentage": 6},
                "lxc": {"bytes": 289046528, "percentage": 3},
                "vms": {"bytes": 0, "percentage": 0},
                "zram": {"bytes": 0, "percentage": 0},
            },
            # MOS's "dirty" view counts reclaimable cache as used:
            # dirty.used == used + dirtyCaches, dirty.free == total - dirty.used.
            "dirty": {"free": 5616533504, "used": 2973401088, "dirtyCaches": 1073741824},
            "percentage": {"used": 35, "actuallyUsed": 18, "dirtyCaches": 12},
        },
        "swap": {
            "total": 8589934592,
            "available": 8160437863,
            "used": 429496729,
            "percentage": 5,
        },
    }


@pytest.fixture
def mock_lxc_containers() -> list[dict[str, Any]]:
    """Return a realistic ``/lxc/containers/usage`` payload."""
    return [
        {
            "name": "database",
            "state": "running",
            "autostart": True,
            "unprivileged": False,
            "cpu": {"usage": 25.5, "unit": "%"},
            "memory": {"bytes": 1073741824, "formatted": "1.00 GiB"},
            "network": {"ipv4": ["192.168.1.100"], "ipv6": [], "docker": [], "all": ["192.168.1.100"]},
        },
        {
            "name": "webserver",
            "state": "stopped",
            "autostart": False,
            "unprivileged": True,
            "cpu": {"usage": 0, "unit": "%"},
            "memory": {"bytes": 0, "formatted": "0 Bytes"},
            "network": {"ipv4": [], "ipv6": [], "docker": [], "all": []},
        },
    ]


@pytest.fixture
def mock_docker_containers() -> list[dict[str, Any]]:
    """Return a realistic ``/docker/mos/containers`` payload."""
    return [
        {
            "index": 1,
            "name": "PushBits",
            "autostart": True,
            "repo": "ghcr.io/pushbits/server",
            "local": "1.20.2",
            "remote": "1.21.0",
            "update_available": True,
        },
        {
            "index": 2,
            "name": "nginx",
            "autostart": False,
            "repo": "library/nginx",
            "local": "1.25.3",
            "remote": "1.25.3",
            "update_available": False,
        },
    ]


@pytest.fixture
def mock_docker_engine_containers() -> list[dict[str, Any]]:
    """Return a realistic raw Docker Engine ``/containers/json`` payload."""
    return [
        {"Id": "abc123", "Names": ["/PushBits"], "State": "running"},
        {"Id": "def456", "Names": ["/nginx"], "State": "exited"},
    ]


@pytest.fixture
def mock_vm_machines() -> list[dict[str, Any]]:
    """Return a realistic ``/vm/machines/usage`` payload."""
    return [
        {
            "name": "Test",
            "state": "running",
            "autostart": True,
            "cpu": {"usage": 12.5, "unit": "%"},
            "memory": {"bytes": 2147483648, "formatted": "2.00 GiB"},
            "vncPort": 5900,
        },
        {
            "name": "Legacy",
            "state": "stopped",
            "autostart": False,
            "cpu": {"usage": 0, "unit": "%"},
            "memory": {"bytes": 0, "formatted": "0 GiB"},
            "vncPort": None,
        },
    ]


@pytest.fixture
def mock_sensors() -> dict[str, list[dict[str, Any]]]:
    """Return a realistic ``/sensors`` payload."""
    return {
        "fan": [
            {
                "id": "1767081453997",
                "index": 0,
                "name": "CPU",
                "manufacturer": "Noctua",
                "model": "NH-U14S",
                "subtype": "speed",
                "value": 593,
                "unit": "rpm",
            },
            {
                "id": "1767081531271",
                "index": 1,
                "name": "CPU",
                "manufacturer": "Noctua",
                "model": "NH-U14S",
                "subtype": "percentage",
                "value": 76.5,
                "unit": "%",
            },
        ],
        "temperature": [
            {
                "id": "1767081945017",
                "index": 0,
                "name": "CPU Env.",
                "manufacturer": "Intel",
                "model": "i9-10900",
                "subtype": "temperature",
                "value": 30.5,
                "unit": "°C",
            },
        ],
        "power": [],
        "voltage": [
            {
                "id": "1767082414584",
                "index": 0,
                "name": "CPU Vcore",
                "manufacturer": "Intel",
                "model": "i9-10900",
                "subtype": "voltage",
                "value": 0.78,
                "unit": "V",
            },
        ],
        "psu": [],
        "other": [],
    }


@pytest.fixture
def mock_token_permissions() -> dict[str, Any]:
    """Return a realistic ``/auth/admin-tokens/me`` payload for a full-access token."""
    return {
        "id": "1784927822204",
        "name": "ha-mos",
        "role": "admin",
        "isBootToken": False,
        "permissions": {"mode": "full"},
    }


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry with realistic connection details."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Sirius",
        unique_id="sirius",
        data={
            CONF_NAME: "Sirius",
            CONF_HOST: "10.0.1.30",
            CONF_API_TOKEN: "test-token",
            CONF_PORT: 80,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
        },
    )


@pytest.fixture
def mock_client(
    *,
    mock_osinfo: dict[str, Any],
    mock_services: dict[str, Any],
    mock_disks: list[dict[str, Any]],
    mock_pools: list[dict[str, Any]],
    mock_system_load: dict[str, Any],
    mock_lxc_containers: list[dict[str, Any]],
    mock_docker_containers: list[dict[str, Any]],
    mock_docker_engine_containers: list[dict[str, Any]],
    mock_vm_machines: list[dict[str, Any]],
    mock_sensors: dict[str, list[dict[str, Any]]],
    mock_token_permissions: dict[str, Any],
) -> AsyncMock:
    """Return an AsyncMock standing in for MOSApiClient."""
    client = AsyncMock(spec=MOSApiClient)
    client.async_get_osinfo.return_value = mock_osinfo
    client.async_get_services.return_value = mock_services
    client.async_get_disks.return_value = mock_disks
    client.async_get_pools.return_value = mock_pools
    client.async_get_system_load.return_value = mock_system_load
    client.async_get_lxc_containers.return_value = mock_lxc_containers
    client.async_get_docker_containers.return_value = mock_docker_containers
    client.async_get_docker_engine_containers.return_value = mock_docker_engine_containers
    client.async_get_vm_machines.return_value = mock_vm_machines
    client.async_get_sensors.return_value = mock_sensors
    client.async_get_token_permissions.return_value = mock_token_permissions
    # diagnostics.py reads these private attributes directly off the real client.
    client._base_url = "http://10.0.1.30:80/api/v1/mos"
    client._root_base_url = "http://10.0.1.30:80/api/v1"
    client._token = "test-token"
    return client


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> Generator[MockConfigEntry]:
    """Set up the mos integration with a mocked API client and tear it down afterward."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        yield mock_config_entry
