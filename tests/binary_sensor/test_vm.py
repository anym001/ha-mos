"""Tests for the dynamic per-VM binary sensors (sourced from /vm/machines/usage).

Running state is not tested here - it's covered by the switch platform
(tests/switch/test_vm.py), which is both the control and the state indicator.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def test_vm_autostart_reflects_config(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Autostart reflects the VM's configured autostart flag."""
    assert hass.states.get("binary_sensor.sirius_vm_test_autostart").state == "on"
    assert hass.states.get("binary_sensor.sirius_vm_legacy_autostart").state == "off"


async def test_vm_autostart_is_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """VM autostart is a regular sensor, not diagnostic."""
    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.sirius_vm_test_autostart").entity_category is None


async def test_vm_gets_its_own_device_linked_to_server(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each VM is its own device, prefixed with the server name and linked via via_device."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    server_device = device_registry.async_get_device_by_identifier(
        ("mos", setup_integration.entry_id), setup_integration.entry_id
    )
    assert server_device is not None

    entry = entity_registry.async_get("binary_sensor.sirius_vm_test_autostart")
    vm_device = device_registry.async_get(entry.device_id)
    assert vm_device.name == "Sirius VM Test"
    assert vm_device.via_device_id == server_device.id
    assert vm_device.id != server_device.id


async def test_vm_removal_also_removes_its_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_vm_machines: list[dict],
) -> None:
    """When a VM disappears for good, its now-empty device is cleaned up too."""
    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device_by_identifier(
        ("mos", f"{setup_integration.entry_id}_vm_Legacy"), setup_integration.entry_id
    )

    mock_client.async_get_vm_machines.return_value = [mock_vm_machines[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert (
        device_registry.async_get_device_by_identifier(
            ("mos", f"{setup_integration.entry_id}_vm_Legacy"), setup_integration.entry_id
        )
        is None
    )
