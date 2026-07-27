"""Tests for the dynamic per-container Docker sensors (sourced from /docker/mos/containers)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_docker_container_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each Docker container gets its own installed_version/latest_version sensors."""
    installed = hass.states.get("sensor.sirius_pushbits_installed_version")
    assert installed is not None
    assert installed.state == "1.20.2"

    latest = hass.states.get("sensor.sirius_pushbits_latest_version")
    assert latest is not None
    assert latest.state == "1.21.0"


async def test_docker_container_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict],
) -> None:
    """When a container disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_nginx_installed_version") is not None

    mock_client.async_get_docker_containers.return_value = [mock_docker_containers[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_nginx_installed_version") is None
    assert hass.states.get("sensor.sirius_pushbits_installed_version") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_nginx_installed_version") is None
