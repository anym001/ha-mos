"""Tests for the live system health sensors (sourced from /system/load)."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.sensor.system_health import _cpu_temperature_average
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

SYSTEM_HEALTH_SENSOR_STATES = {
    "sensor.sirius_cpu_load": "42.35",
    "sensor.sirius_cpu_temperature": "55.0",
    "sensor.sirius_cpu_temperature_max": "61.0",
    "sensor.sirius_cpu_temperature_average": "54.0",
    "sensor.sirius_memory_usage": "18",
    "sensor.sirius_swap_usage": "5",
}

MEMORY_BYTE_SENSORS = (
    "sensor.sirius_memory_used",
    "sensor.sirius_memory_total",
    "sensor.sirius_memory_free",
    "sensor.sirius_memory_installed",
    "sensor.sirius_memory_reserved",
    "sensor.sirius_memory_cache",
    "sensor.sirius_memory_docker",
    "sensor.sirius_memory_system",
    "sensor.sirius_memory_lxc",
    "sensor.sirius_memory_vms",
    "sensor.sirius_memory_zram",
    "sensor.sirius_swap_used",
    "sensor.sirius_swap_total",
    "sensor.sirius_swap_free",
)


async def test_system_health_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each system health sensor exposes the expected value from the system_load payload."""
    for entity_id, expected_state in SYSTEM_HEALTH_SENSOR_STATES.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} not found"
        assert state.state == expected_state


@pytest.mark.parametrize("entity_id", MEMORY_BYTE_SENSORS)
async def test_memory_byte_sensors_are_reported_in_bytes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    entity_id: str,
) -> None:
    """Byte-valued memory sensors are populated (unit conversion is handled by HA core)."""
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} not found"
    assert state.state != "unknown"


MEMORY_BREAKDOWN_GIB = {
    "sensor.sirius_memory_docker": 1073741824 / 1024**3,
    "sensor.sirius_memory_system": 536870912 / 1024**3,
    "sensor.sirius_memory_lxc": 289046528 / 1024**3,
    "sensor.sirius_memory_vms": 0.0,
    "sensor.sirius_memory_zram": 0.0,
    "sensor.sirius_memory_cache": 1073741824 / 1024**3,
}


@pytest.mark.parametrize(("entity_id", "expected_gib"), MEMORY_BREAKDOWN_GIB.items())
async def test_memory_breakdown_maps_each_consumer_to_its_own_share(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    entity_id: str,
    expected_gib: float,
) -> None:
    """Each breakdown sensor reads its own consumer, not a neighbour's share."""
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} not found"
    assert float(state.state) == pytest.approx(expected_gib)


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        ({"cores": [30.0, 31.0]}, 30.5),
        ({"cores": [30.0, None, 31.0]}, 30.5),
        ({"cores": []}, None),
        ({"cores": None}, None),
        ({}, None),
    ],
    ids=["mean", "skips-null-cores", "empty-list", "null-list", "missing-key"],
)
async def test_cpu_temperature_average_handles_partial_payloads(
    temperature: dict[str, Any],
    expected: float | None,
) -> None:
    """The core mean ignores hyper-threaded siblings reporting null and never divides by zero."""
    assert _cpu_temperature_average({"temperature": temperature}) == expected


async def test_system_health_sensors_have_no_entity_category(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """System health sensors are regular sensors, not diagnostics."""
    registry = er.async_get(hass)
    for entity_id in (*SYSTEM_HEALTH_SENSOR_STATES, *MEMORY_BYTE_SENSORS):
        entry = registry.async_get(entity_id)
        assert entry is not None
        assert entry.entity_category is None
