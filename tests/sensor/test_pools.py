"""Tests for the dynamic per-pool sensors (sourced from /pools)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_pool_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each pool gets its own usage/free_space sensors, named after the pool."""
    usage = hass.states.get("sensor.sirius_pool_test1_usage")
    assert usage is not None
    assert usage.state == "42"

    free_space = hass.states.get("sensor.sirius_pool_test1_free_space")
    assert free_space is not None


async def test_pool_total_and_used_space_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each pool gets its own total_space/used_space sensors."""
    assert hass.states.get("sensor.sirius_pool_test1_total_space") is not None
    assert hass.states.get("sensor.sirius_pool_test1_used_space") is not None
    assert hass.states.get("sensor.sirius_pool_test2_total_space") is not None
    assert hass.states.get("sensor.sirius_pool_test2_used_space") is not None


async def test_pool_type_value_and_is_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each pool gets its own type sensor, which is a regular sensor."""
    assert hass.states.get("sensor.sirius_pool_test1_type").state == "xfs"
    assert hass.states.get("sensor.sirius_pool_test2_type").state == "btrfs"

    registry = er.async_get(hass)
    entry = registry.async_get("sensor.sirius_pool_test1_type")
    assert entry.entity_category is None


async def test_pool_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_pools: list[dict],
) -> None:
    """When a pool disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_pool_test2_usage") is not None

    mock_client.async_get_pools.return_value = [mock_pools[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_pool_test2_usage") is None
    assert hass.states.get("sensor.sirius_pool_test1_usage") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_pool_test2_usage") is None
