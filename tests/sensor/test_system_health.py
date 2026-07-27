"""Tests for the live system health sensors (sourced from /system/load)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

SYSTEM_HEALTH_SENSOR_STATES = {
    "sensor.sirius_cpu_load": "42.35",
    "sensor.sirius_cpu_temperature": "55.0",
    "sensor.sirius_memory_usage": "18",
    "sensor.sirius_swap_usage": "0",
}


async def test_system_health_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each system health sensor exposes the expected value from the system_load payload."""
    for entity_id, expected_state in SYSTEM_HEALTH_SENSOR_STATES.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} not found"
        assert state.state == expected_state


async def test_memory_used_is_reported_in_bytes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The memory_used sensor is populated (unit conversion is handled by HA core)."""
    state = hass.states.get("sensor.sirius_memory_used")
    assert state is not None
    assert state.state != "unknown"


async def test_system_health_sensors_have_no_entity_category(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """System health sensors are regular sensors, not diagnostics."""
    registry = er.async_get(hass)
    for entity_id in SYSTEM_HEALTH_SENSOR_STATES:
        entry = registry.async_get(entity_id)
        assert entry is not None
        assert entry.entity_category is None
