"""Tests for the static service binary sensors (sourced from /services)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

SERVICE_BINARY_SENSOR_STATES = {
    "binary_sensor.sirius_docker_running": "off",
    "binary_sensor.sirius_vm_running": "on",
    "binary_sensor.sirius_ssh_enabled": "on",
    "binary_sensor.sirius_samba_enabled": "on",
    "binary_sensor.sirius_nfs_enabled": "off",
    "binary_sensor.sirius_tailscale_online": "on",
    "binary_sensor.sirius_netbird_online": "off",
}


async def test_service_binary_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each service binary sensor reflects the expected flag from the services payload."""
    for entity_id, expected_state in SERVICE_BINARY_SENSOR_STATES.items():
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} not found"
        assert state.state == expected_state


async def test_service_binary_sensors_have_no_entity_category(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Service status is a regular binary sensor, not a diagnostic."""
    registry = er.async_get(hass)
    for entity_id in SERVICE_BINARY_SENSOR_STATES:
        entry = registry.async_get(entity_id)
        assert entry is not None
        assert entry.entity_category is None
