"""Tests for the dynamic per-container LXC binary sensors (sourced from /lxc/containers/usage).

Running state is not tested here - it's covered by the switch platform
(tests/switch/test_lxc.py), which is both the control and the state indicator.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def test_lxc_autostart_reflects_config(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Autostart reflects the container's configured autostart flag."""
    assert hass.states.get("binary_sensor.sirius_lxc_database_autostart").state == "on"
    assert hass.states.get("binary_sensor.sirius_lxc_webserver_autostart").state == "off"


async def test_lxc_autostart_is_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Container autostart is a regular sensor, not diagnostic."""
    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.sirius_lxc_database_autostart").entity_category is None


async def test_lxc_container_gets_its_own_device_linked_to_server(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each LXC container is its own device, prefixed with the server name and linked via via_device."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    server_device = device_registry.async_get_device(identifiers={("mos", setup_integration.entry_id)})
    assert server_device is not None

    entry = entity_registry.async_get("binary_sensor.sirius_lxc_database_autostart")
    container_device = device_registry.async_get(entry.device_id)
    assert container_device.name == "Sirius LXC database"
    assert container_device.via_device_id == server_device.id
    assert container_device.id != server_device.id


async def test_lxc_container_removal_also_removes_its_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_lxc_containers: list[dict],
) -> None:
    """When a container disappears for good, its now-empty device is cleaned up too."""
    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device(identifiers={("mos", f"{setup_integration.entry_id}_lxc_webserver")})

    mock_client.async_get_lxc_containers.return_value = [mock_lxc_containers[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert (
        device_registry.async_get_device(identifiers={("mos", f"{setup_integration.entry_id}_lxc_webserver")}) is None
    )
