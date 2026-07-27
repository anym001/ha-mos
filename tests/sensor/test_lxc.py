"""Tests for the dynamic per-container LXC sensors (sourced from /lxc/containers/usage)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_lxc_container_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each LXC container gets its own cpu_usage/memory_usage sensors, named after the container."""
    cpu_usage = hass.states.get("sensor.sirius_database_cpu_usage")
    assert cpu_usage is not None
    assert cpu_usage.state == "25.5"

    memory_usage = hass.states.get("sensor.sirius_database_memory_usage")
    assert memory_usage is not None
    assert memory_usage.state != "unknown"


async def test_lxc_container_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_lxc_containers: list[dict],
) -> None:
    """When a container disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_webserver_cpu_usage") is not None

    mock_client.async_get_lxc_containers.return_value = [mock_lxc_containers[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_webserver_cpu_usage") is None
    assert hass.states.get("sensor.sirius_database_cpu_usage") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_webserver_cpu_usage") is None
