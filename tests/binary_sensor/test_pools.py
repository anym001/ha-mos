"""Tests for the dynamic per-pool binary sensors (sourced from /pools)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_pool_problem_reflects_health(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A healthy pool reports problem=off, a degraded one reports problem=on."""
    assert hass.states.get("binary_sensor.sirius_pool_test1_problem").state == "off"
    assert hass.states.get("binary_sensor.sirius_pool_test2_problem").state == "on"


async def test_pool_problem_is_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The pool problem sensor is the one pool entity that IS diagnostic."""
    registry = er.async_get(hass)
    entry = registry.async_get("binary_sensor.sirius_pool_test1_problem")
    assert entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_maintenance_sensors_only_created_when_reported(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """scrub/balance/parity sensors are only created for pools that report that field.

    Test1 (BTRFS-style) reports scrub_operation/balance_operation but not
    parity_operation; Test2 (RAID-style) reports only parity_operation.
    """
    assert hass.states.get("binary_sensor.sirius_pool_test1_scrub_running") is not None
    assert hass.states.get("binary_sensor.sirius_pool_test1_balance_running") is not None
    assert hass.states.get("binary_sensor.sirius_pool_test1_parity_running") is None

    assert hass.states.get("binary_sensor.sirius_pool_test2_parity_running") is not None
    assert hass.states.get("binary_sensor.sirius_pool_test2_scrub_running") is None
    assert hass.states.get("binary_sensor.sirius_pool_test2_balance_running") is None
