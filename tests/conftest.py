"""Shared fixtures for mos tests."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClient, MOSApiClientNotFoundError
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
        # main is the package sensor, not the core mean (54.0), so the two differ.
        "temperature": {"main": 55.0, "max": 61.0, "min": 48.0, "cores": [48.0, 52.0, 55.0, 61.0]},
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
def mock_lxc_container_details() -> list[dict[str, Any]]:
    """Return a realistic ``/lxc/containers`` payload (the icon-bearing endpoint)."""
    return [
        # Stock distribution artwork.
        {
            "name": "database",
            "state": "running",
            "distribution": "debian",
            "custom_icon": False,
            "architecture": "amd64",
        },
        # An icon uploaded for this container specifically.
        {
            "name": "webserver",
            "state": "stopped",
            "distribution": "alpine",
            "custom_icon": True,
            "architecture": "amd64",
        },
    ]


@pytest.fixture
def mock_docker_containers() -> list[dict[str, Any]]:
    """
    Return a realistic ``/docker/mos/containers`` payload.

    ``local``/``remote`` are image tags for one container and full digests for
    the other, which is how MOS actually answers: a container pinned to a tag
    reports the tag, one without reports ``sha256:...``. Both are valid states
    for the version sensors, so both are represented here.
    """
    return [
        {
            "index": 1,
            "name": "PushBits",
            "autostart": True,
            "wait": "0",
            "repo": "ghcr.io/pushbits/server",
            "local": "1.20.2",
            "remote": "1.21.0",
            "update_available": True,
            "default_shell": "/bin/sh",
            "no_autoupdate": False,
        },
        {
            "index": 2,
            "name": "nginx",
            "autostart": False,
            "wait": "0",
            "repo": "library/nginx",
            "local": "sha256:1c2eac2224f82d2d8b6a7e8af30f1650ed9f06ddf81fe40bbf841fa794295c15",
            "remote": "sha256:1c2eac2224f82d2d8b6a7e8af30f1650ed9f06ddf81fe40bbf841fa794295c15",
            "update_available": False,
            "default_shell": "/bin/sh",
            "no_autoupdate": False,
        },
    ]


@pytest.fixture
def mock_docker_engine_containers() -> list[dict[str, Any]]:
    """
    Return a realistic raw Docker Engine ``/containers/json`` payload.

    The two containers deliberately differ in the ways the entities care about.
    PushBits runs, has a healthcheck and a web interface, and is published on a
    host port that differs from its container port - the case where taking the
    ``mos.webui`` placeholder literally would produce a dead link. nginx is
    stopped, defines no healthcheck (MOS says so with ``"none"`` rather than by
    omitting the field) and has no web interface label, so its link has to come
    from its template or not at all.
    """
    return [
        {
            "Id": "abc123",
            "Names": ["/PushBits"],
            "Image": "ghcr.io/pushbits/server",
            "Created": 1785148413,
            "Ports": [{"IP": "0.0.0.0", "PrivatePort": 8080, "PublicPort": 8081, "Type": "tcp"}],
            "Labels": {
                "mos.backend": "docker",
                "mos.no_autoupdate": "false",
                "mos.webui": "http://[ADDRESS]:[PORT:8080]/",
                "org.opencontainers.image.title": "server",
                "org.opencontainers.image.description": "A simple server for push notifications",
                "org.opencontainers.image.source": "https://github.com/pushbits/server",
            },
            "State": "running",
            "Status": "Up 3 minutes (healthy)",
            "Health": {"Status": "healthy", "FailingStreak": 0},
            "HostConfig": {"NetworkMode": "bridge"},
        },
        {
            "Id": "def456",
            "Names": ["/nginx"],
            "Image": "library/nginx",
            "Created": 1785148583,
            "Ports": [],
            "Labels": {"mos.backend": "docker", "mos.no_autoupdate": "false"},
            "State": "exited",
            "Status": "Exited (0) 2 weeks ago",
            "Health": {"Status": "none", "FailingStreak": 0},
            "HostConfig": {"NetworkMode": "bridge"},
        },
    ]


@pytest.fixture
def mock_docker_templates() -> dict[str, dict[str, Any]]:
    """
    Return realistic ``/docker/mos/templates/{name}`` payloads, keyed by container.

    nginx's template is what makes its web link resolvable at all: it is
    stopped, so Docker reports no port mapping, and the configured
    ``container``/``host`` pair is the only remaining source.
    """
    return {
        "PushBits": {
            "name": "PushBits_new",
            "repo": "ghcr.io/pushbits/server",
            "icon": "https://raw.githubusercontent.com/pushbits/logo/main/logo.png",
            "web_ui_url": "",
            "network": "bridge",
            "ports": [{"name": "TCP - Listen port", "protocol": "tcp", "host": "8081", "container": "8080"}],
        },
        "nginx": {
            "name": "nginx_new",
            "repo": "library/nginx",
            "icon": "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/nginx.png",
            "web_ui_url": "http://[IP]:[PORT:80]/",
            "network": "bridge",
            "ports": [{"name": "WebUI", "protocol": "tcp", "host": "8080", "container": "80"}],
        },
    }


@pytest.fixture
def mock_docker_stats() -> dict[str, Any]:
    """
    Return a realistic raw Docker Engine ``/containers/{name}/stats`` payload.

    Trimmed to the fields the integration reads, but with their real shapes and
    magnitudes: cumulative nanosecond CPU counters in both samples, and a cgroup
    v2 memory block where ``usage`` includes reclaimable page cache that
    ``inactive_file`` accounts for.

    The numbers work out to 25% of two CPUs and 64 MiB of a 512 MiB limit, so a
    test asserting on them reads as a statement about the container rather than
    about arithmetic.
    """
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 1_500_000_000},
            "system_cpu_usage": 40_000_000_000,
            "online_cpus": 2,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 1_000_000_000},
            "system_cpu_usage": 36_000_000_000,
        },
        "memory_stats": {
            "usage": 100_663_296,
            "limit": 536_870_912,
            "stats": {"inactive_file": 33_554_432},
        },
    }


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
def mock_vm_machine_details() -> list[dict[str, Any]]:
    """Return a realistic ``/vm/machines`` payload (the icon-bearing endpoint)."""
    return [
        {
            "name": "Test",
            "state": "running",
            "icon": "debian",
            "customIcon": False,
            "index": 1,
        },
        # MOS leaves ``icon`` null for a VM that was never given stock artwork.
        {
            "name": "Legacy",
            "state": "stopped",
            "icon": None,
            "customIcon": True,
            "index": 2,
        },
    ]


@pytest.fixture
def mock_sensors() -> dict[str, list[dict[str, Any]]]:
    """Return a realistic ``/sensors`` payload.

    Taken from a real server, so it carries the cases that shape the entities:
    categories that are empty, a category whose readings are all of one subtype
    (temperature), a PSU mixing voltage/wattage/temperature/speed readings -
    including one ("Fan Speed") whose name already ends in its own subtype - and
    the two spellings MOS uses for the same unit ("°C" and "c").
    """
    return {
        "fan": [
            {
                "id": "1767034178601",
                "index": 0,
                "name": "CPU Fan",
                "manufacturer": "Noctua",
                "model": "NF-F12",
                "subtype": "speed",
                "value": 561,
                "unit": "rpm",
            },
            {
                "id": "1767385904809",
                "index": 1,
                "name": "Case Fan",
                "manufacturer": "Noctua",
                "model": "NF-F12",
                "subtype": "speed",
                "value": 817,
                "unit": "rpm",
            },
        ],
        "temperature": [
            {
                "id": "1767390439505",
                "index": 0,
                "name": "NVMe #1",
                "manufacturer": "Samsung",
                "model": "970 EVO Plus 1TB",
                "subtype": "temperature",
                "value": 37.85,
                "unit": "°C",
            },
            {
                "id": "1767390494116",
                "index": 1,
                "name": "NVMe #2",
                "manufacturer": "Samsung",
                "model": "970 EVO Plus 1TB",
                "subtype": "temperature",
                "value": 35.85,
                "unit": "°C",
            },
        ],
        "power": [],
        "voltage": [],
        "psu": [
            {
                "id": "1767004133283",
                "index": 0,
                "name": "Voltage Input",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "voltage",
                "value": 230,
                "unit": "V",
            },
            {
                "id": "1767004133505",
                "index": 1,
                "name": "Voltage 12V",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "voltage",
                "value": 12.02,
                "unit": "V",
            },
            {
                "id": "1767004134000",
                "index": 2,
                "name": "Voltage 5V",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "voltage",
                "value": 5.06,
                "unit": "V",
            },
            {
                "id": "1767004134218",
                "index": 3,
                "name": "Voltage 3.3V",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "voltage",
                "value": 3.3,
                "unit": "V",
            },
            {
                "id": "1767004134511",
                "index": 4,
                "name": "Power Total",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "wattage",
                "value": 36,
                "unit": "W",
            },
            {
                "id": "1767004134726",
                "index": 5,
                "name": "Power 12V",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "wattage",
                "value": 24,
                "unit": "W",
            },
            {
                "id": "1767004134934",
                "index": 6,
                "name": "Power 5V",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "wattage",
                "value": 10.5,
                "unit": "W",
            },
            {
                "id": "1767004135148",
                "index": 7,
                "name": "Power 3.3V",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "wattage",
                "value": 2.5,
                "unit": "W",
            },
            {
                "id": "1767004135375",
                "index": 8,
                "name": "VRM Temp",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "temperature",
                "value": 40.25,
                "unit": "c",
            },
            {
                "id": "1767004135523",
                "index": 9,
                "name": "Case Temp",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "temperature",
                "value": 34.25,
                "unit": "°C",
            },
            {
                "id": "1767004135615",
                "index": 10,
                "name": "Fan Speed",
                "manufacturer": "Corsair",
                "model": "HX750i",
                "subtype": "speed",
                "value": 0,
                "unit": "rpm",
            },
        ],
        "other": [],
    }


@pytest.fixture
def mock_nut() -> dict[str, Any]:
    """Return a realistic ``/nut/status`` payload for an attached, online UPS.

    The raw ``vars`` block MOS also returns is left out on purpose: nothing in
    the integration reads it (see ``MOSApiClient.async_get_nut_status``).
    """
    return {
        "reachable": True,
        "name": "ups",
        "status": "OL",
        "data": {
            "model": "ACMT1000E",
            "manufacturer": "CPS",
            "serial": "XTBLP2000067",
            "load": 6,
            "realpowerNominal": 700,
            "battery": {"charge": 100, "chargeLow": 10, "runtime": 15780, "voltage": 24, "type": "PbAcid"},
            "input": {"voltage": 228, "frequency": 50},
            "output": {"voltage": 228, "frequency": 50},
        },
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
    mock_lxc_container_details: list[dict[str, Any]],
    mock_vm_machine_details: list[dict[str, Any]],
    mock_docker_containers: list[dict[str, Any]],
    mock_docker_engine_containers: list[dict[str, Any]],
    mock_docker_templates: dict[str, dict[str, Any]],
    mock_docker_stats: dict[str, Any],
    mock_vm_machines: list[dict[str, Any]],
    mock_sensors: dict[str, list[dict[str, Any]]],
    mock_nut: dict[str, Any],
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

    async def _template(name: str) -> dict[str, Any]:
        """Answer like MOS does: the template, or 404 for a container it did not create."""
        if name not in mock_docker_templates:
            raise MOSApiClientNotFoundError(f"No template for {name}")
        return mock_docker_templates[name]

    client.async_get_docker_template.side_effect = _template
    client.async_get_docker_container_stats.return_value = mock_docker_stats
    client.async_get_vm_machines.return_value = mock_vm_machines
    client.async_get_sensors.return_value = mock_sensors
    client.async_get_nut_status.return_value = mock_nut
    client.async_get_token_permissions.return_value = mock_token_permissions
    client.async_get_lxc_container_details.return_value = mock_lxc_container_details
    client.async_get_vm_machine_details.return_value = mock_vm_machine_details
    # Default to a server that hosts no icons, so the pictures a test cares about
    # are the ones that test opts into. ``root_url`` is a property on the real
    # client, which ``spec`` turns into a plain attribute here.
    client.async_static_asset_exists.return_value = False
    client.root_url = "http://10.0.1.30:80"
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
