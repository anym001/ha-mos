"""Tests for the dynamic per-disk binary sensors (sourced from /disks)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_disk_smart_warning_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """SMART warning reflects each disk's smartWarning flag."""
    assert hass.states.get("binary_sensor.sirius_vda_smart_warning").state == "off"
    assert hass.states.get("binary_sensor.sirius_vdb_smart_warning").state == "on"


async def test_disk_smart_warning_is_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """SMART warning is one of the two entities that IS diagnostic."""
    registry = er.async_get(hass)
    entry = registry.async_get("binary_sensor.sirius_vda_smart_warning")
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
