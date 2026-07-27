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


async def test_single_device_for_all_entities(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """All mos entities, including per-disk/per-pool ones, share the one server device."""
    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, setup_integration.entry_id)

    assert len(devices) == 1
    assert devices[0].name == "Sirius"
