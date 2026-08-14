"""Tests for the dynamic per-container Docker binary sensors (sourced from /docker/mos/containers)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def _refresh_with_engine(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    engine_containers: list[dict],
) -> None:
    """Re-poll with a replacement Docker Engine payload."""
    mock_client.async_get_docker_engine_containers.return_value = engine_containers
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_docker_update_available_reflects_payload(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A container with a newer remote image reports update_available=on."""
    assert hass.states.get("binary_sensor.sirius_docker_pushbits_update_available").state == "on"
    assert hass.states.get("binary_sensor.sirius_docker_nginx_update_available").state == "off"


async def test_docker_update_available_is_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """update_available is diagnostic, like the health sensor and unlike the rest of a container's entities."""
    registry = er.async_get(hass)
    entry = registry.async_get("binary_sensor.sirius_docker_pushbits_update_available")
    assert entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_docker_health_reflects_a_passing_healthcheck(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A running container whose healthcheck passes reports no problem."""
    assert hass.states.get("binary_sensor.sirius_docker_pushbits_health").state == "off"


async def test_docker_health_reports_a_failing_healthcheck(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_engine_containers: list[dict],
) -> None:
    """A running container whose healthcheck fails reports a problem."""
    unhealthy = {**mock_docker_engine_containers[0], "Health": {"Status": "unhealthy", "FailingStreak": 3}}
    await _refresh_with_engine(hass, setup_integration, mock_client, [unhealthy, mock_docker_engine_containers[1]])

    assert hass.states.get("binary_sensor.sirius_docker_pushbits_health").state == "on"


async def test_stopped_container_reports_no_health_at_all(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_engine_containers: list[dict],
) -> None:
    """Docker leaves the health status at whatever it was, so a stopped container's is not a verdict.

    This is the exact payload a long-stopped container produces: ``unhealthy``
    with a zero failing streak, from a healthcheck that never ran. Reporting it
    would put a problem badge on every stopped container.
    """
    stopped = {
        **mock_docker_engine_containers[0],
        "State": "exited",
        "Health": {"Status": "unhealthy", "FailingStreak": 0},
    }
    await _refresh_with_engine(hass, setup_integration, mock_client, [stopped, mock_docker_engine_containers[1]])

    assert hass.states.get("binary_sensor.sirius_docker_pushbits_health").state == STATE_UNKNOWN


async def test_container_without_a_healthcheck_gets_no_health_sensor(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """MOS reports "none" rather than omitting health, so a container with no healthcheck is recognisable."""
    assert hass.states.get("binary_sensor.sirius_docker_nginx_health") is None
    assert hass.states.get("binary_sensor.sirius_docker_nginx_autostart") is not None


async def test_docker_autostart_reflects_config(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Autostart reflects the container's configured autostart flag and is a regular entity."""
    assert hass.states.get("binary_sensor.sirius_docker_pushbits_autostart").state == "on"
    assert hass.states.get("binary_sensor.sirius_docker_nginx_autostart").state == "off"

    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.sirius_docker_pushbits_autostart").entity_category is None


async def test_docker_container_gets_its_own_device_linked_to_server(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each Docker container is its own device, prefixed with the server name and linked via via_device."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    server_device = device_registry.async_get_device_by_identifier(
        ("mos", setup_integration.entry_id), setup_integration.entry_id
    )
    assert server_device is not None

    entry = entity_registry.async_get("binary_sensor.sirius_docker_pushbits_autostart")
    container_device = device_registry.async_get(entry.device_id)
    assert container_device.name == "Sirius Docker PushBits"
    assert container_device.via_device_id == server_device.id
    assert container_device.id != server_device.id


async def test_docker_container_removal_also_removes_its_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict],
) -> None:
    """When a container disappears for good, its now-empty device is cleaned up too."""
    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device_by_identifier(
        ("mos", f"{setup_integration.entry_id}_docker_nginx"), setup_integration.entry_id
    )

    mock_client.async_get_docker_containers.return_value = [mock_docker_containers[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert (
        device_registry.async_get_device_by_identifier(
            ("mos", f"{setup_integration.entry_id}_docker_nginx"), setup_integration.entry_id
        )
        is None
    )
