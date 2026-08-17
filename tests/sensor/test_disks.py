"""Tests for the dynamic per-disk sensors (sourced from /disks)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.sensor.disks import DISK_POWER_STATES
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_disk_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each disk gets its own power_status sensor."""
    assert hass.states.get("sensor.sirius_disk_vda_power_status").state == "active"
    assert hass.states.get("sensor.sirius_disk_vdb_power_status").state == "standby"


async def test_disk_power_status_is_a_translatable_enum(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The power status declares its options, which is what makes it translatable."""
    state = hass.states.get("sensor.sirius_disk_vda_power_status")
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["options"] == DISK_POWER_STATES


@pytest.mark.parametrize("language", ["en", "de"])
def test_disk_power_status_options_are_all_translated(language: str) -> None:
    """Every option carries a string, or it renders to the user as the raw value."""
    translations = json.loads(
        (
            Path(__file__).resolve().parents[2] / "custom_components" / "mos" / "translations" / f"{language}.json"
        ).read_text(encoding="utf-8")
    )
    states = translations["entity"]["sensor"]["disk_power_status"]["state"]

    assert sorted(states) == sorted(DISK_POWER_STATES), f"{language}.json is out of sync with DISK_POWER_STATES"


async def test_unknown_disk_power_status_reads_as_unknown(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_disks: list[dict],
) -> None:
    """A mode outside the options reads as unknown rather than taking the entity down.

    An enum sensor rejects any state it did not declare, so a MOS release that
    grows a new power mode must not turn the reading into an error.
    """
    mock_client.async_get_disks.return_value = [{**mock_disks[0], "powerStatus": "hibernating"}]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_disk_vda_power_status").state == "unknown"


async def test_disk_temperature_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each disk gets its own numeric temperature sensor."""
    assert hass.states.get("sensor.sirius_disk_vda_temperature").state == "32"
    assert hass.states.get("sensor.sirius_disk_vdb_temperature").state == "41"


async def test_disk_model_size_and_type_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each disk gets its own model/size/type sensors."""
    assert hass.states.get("sensor.sirius_disk_vda_model").state == "Samsung SSD 970"
    assert hass.states.get("sensor.sirius_disk_vda_type").state == "ssd"
    assert hass.states.get("sensor.sirius_disk_vdb_type").state == "hdd"
    assert float(hass.states.get("sensor.sirius_disk_vda_size").state) == pytest.approx(2.147483648)


async def test_disk_model_and_type_are_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Model and type are regular sensors, unlike smart_warning."""
    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_disk_vda_model").entity_category is None
    assert registry.async_get("sensor.sirius_disk_vda_type").entity_category is None


async def test_disk_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_disks: list[dict],
) -> None:
    """When a disk disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_disk_vdb_power_status") is not None

    mock_client.async_get_disks.return_value = [mock_disks[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_disk_vdb_power_status") is None
    assert hass.states.get("sensor.sirius_disk_vda_power_status") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_disk_vdb_power_status") is None


async def test_new_disk_appearing_creates_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_disks: list[dict],
) -> None:
    """When a new disk appears in a later refresh, its entities are created."""
    new_disk = {
        "serial": "S3",
        "name": "vdc",
        "powerStatus": "active",
        "smartWarning": False,
    }
    mock_client.async_get_disks.return_value = [*mock_disks, new_disk]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.sirius_disk_vdc_power_status")
    assert state is not None
    assert state.state == "active"
