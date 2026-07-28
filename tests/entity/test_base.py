"""Tests for MOSEntity's device info.

Regression test: the device info used to show the CPU brand as the device
model; it must show the MOS version instead (build as sw_version).
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


async def test_device_info_shows_mos_version_not_cpu(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The device model/sw_version come from osinfo.mos, not osinfo.cpu."""
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, setup_integration.entry_id)})

    assert device is not None
    assert device.manufacturer == "MOS"
    assert device.model == "0.5.0-stable"
    assert device.sw_version == "20260705-1111"
    assert device.model != "Intel Xeon E-2288G"


async def test_disks_and_pools_get_their_own_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each disk/pool is a separate device linked back to the server device, same as LXC/Docker/VM items."""
    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, setup_integration.entry_id)

    # 1 server device + 2 disks + 2 pools + 2 LXC containers + 2 Docker containers + 2 VMs.
    assert len(devices) == 11
    server_device = registry.async_get_device(identifiers={(DOMAIN, setup_integration.entry_id)})
    assert server_device is not None
    assert server_device.name == "Sirius"
    container_devices = [device for device in devices if device.id != server_device.id]
    assert len(container_devices) == 10
    assert all(device.via_device_id == server_device.id for device in container_devices)
