"""Tests for the static system sensors (sourced from /osinfo)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

SYSTEM_SENSOR_STATES = {
    "sensor.sirius_mos_version": "0.5.0-stable",
    "sensor.sirius_update_channel": "stable",
    "sensor.sirius_mos_build": "20260705-1111",
    "sensor.sirius_api_version": "1.4.0",
    "sensor.sirius_frontend_version": "1.4.0",
    "sensor.sirius_running_kernel": "6.1.0-mos",
    "sensor.sirius_recommended_kernel": "6.1.0-mos",
    "sensor.sirius_architecture": "x86_64",
    "sensor.sirius_cpu": "Intel Xeon E-2288G",
    "sensor.sirius_base_os": "Debian 12",
}


async def test_system_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each system sensor exposes the expected value from the osinfo payload."""
    for entity_id, expected_state in SYSTEM_SENSOR_STATES.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} not found"
        assert state.state == expected_state


async def test_boot_time_is_parsed_as_timestamp(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The uptime.since string is parsed into an ISO timestamp."""
    state = hass.states.get("sensor.sirius_boot_time")
    assert state is not None
    assert state.state == "2026-07-25T03:13:48+00:00"


async def test_system_sensors_have_no_entity_category(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """System info sensors are regular sensors, not diagnostics."""
    registry = er.async_get(hass)
    for entity_id in SYSTEM_SENSOR_STATES:
        entry = registry.async_get(entity_id)
        assert entry is not None
        assert entry.entity_category is None
