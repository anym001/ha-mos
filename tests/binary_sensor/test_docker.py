"""Tests for the dynamic per-container Docker binary sensors (sourced from /docker/mos/containers)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


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
    """update_available is the one Docker container entity that IS diagnostic."""
    registry = er.async_get(hass)
    entry = registry.async_get("binary_sensor.sirius_docker_pushbits_update_available")
    assert entry.entity_category is EntityCategory.DIAGNOSTIC


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
