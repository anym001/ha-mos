"""Tests for the hardware sensor readings (sourced from /sensors)."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_hardware_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Every reading of every category becomes one sensor holding its value."""
    assert hass.states.get("sensor.sirius_sensor_fan_cpu_fan_speed").state == "561"
    assert hass.states.get("sensor.sirius_sensor_fan_case_fan_speed").state == "817"
    assert hass.states.get("sensor.sirius_sensor_nvme_1_temperature").state == "37.85"
    assert hass.states.get("sensor.sirius_sensor_psu_voltage_input_voltage").state == "230"
    assert hass.states.get("sensor.sirius_sensor_psu_power_total_wattage").state == "36"
    assert hass.states.get("sensor.sirius_sensor_psu_vrm_temp_temperature").state == "40.25"


async def test_only_reported_readings_become_entities(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Categories the server reports as empty create nothing at all."""
    hardware_sensors = [entity_id for entity_id in hass.states.async_entity_ids("sensor") if "_sensor_" in entity_id]

    assert len(hardware_sensors) == 15


@pytest.mark.parametrize(
    ("entity_id", "device_class", "unit"),
    [
        ("sensor.sirius_sensor_nvme_1_temperature", "temperature", "°C"),
        ("sensor.sirius_sensor_psu_voltage_5v_voltage", "voltage", "V"),
        ("sensor.sirius_sensor_psu_power_5v_wattage", "power", "W"),
        # No device class covers a fan speed, but the unit MOS reports still does.
        ("sensor.sirius_sensor_psu_fan_speed", None, "rpm"),
    ],
)
async def test_device_class_follows_the_subtype(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    entity_id: str,
    device_class: str | None,
    unit: str,
) -> None:
    """The reading's subtype decides its device class; the unit is taken as reported."""
    attributes = hass.states.get(entity_id).attributes

    assert attributes.get(ATTR_DEVICE_CLASS) == device_class
    assert attributes[ATTR_UNIT_OF_MEASUREMENT] == unit
    assert attributes[ATTR_STATE_CLASS] is SensorStateClass.MEASUREMENT


async def test_names_name_the_category_without_repeating_the_subtype(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Names are built from live API data, and must not stutter.

    The category is left out where the subtype already says it (a temperature
    reading in the temperature category), and the subtype is left out where the
    name already ends in it (the PSU's "Fan Speed").
    """
    names = {
        entity_id: hass.states.get(entity_id).attributes[ATTR_FRIENDLY_NAME]
        for entity_id in (
            "sensor.sirius_sensor_fan_cpu_fan_speed",
            "sensor.sirius_sensor_nvme_1_temperature",
            "sensor.sirius_sensor_psu_fan_speed",
            "sensor.sirius_sensor_psu_power_total_wattage",
        )
    }

    assert names == {
        "sensor.sirius_sensor_fan_cpu_fan_speed": "Sirius Sensor Fan CPU Fan Speed",
        "sensor.sirius_sensor_nvme_1_temperature": "Sirius Sensor NVMe #1 Temperature",
        "sensor.sirius_sensor_psu_fan_speed": "Sirius Sensor PSU Fan Speed",
        "sensor.sirius_sensor_psu_power_total_wattage": "Sirius Sensor PSU Power Total Wattage",
    }


async def test_reading_removed_from_api_removes_its_sensor(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_sensors: dict[str, list[dict[str, Any]]],
) -> None:
    """A reading that disappears from a later poll takes its entity with it."""
    assert hass.states.get("sensor.sirius_sensor_fan_case_fan_speed") is not None

    payload = copy.deepcopy(mock_sensors)
    payload["fan"] = payload["fan"][:1]
    mock_client.async_get_sensors.return_value = payload
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_sensor_fan_case_fan_speed") is None
    assert hass.states.get("sensor.sirius_sensor_fan_cpu_fan_speed") is not None
    assert er.async_get(hass).async_get("sensor.sirius_sensor_fan_case_fan_speed") is None


async def test_new_reading_appearing_creates_its_sensor(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_sensors: dict[str, list[dict[str, Any]]],
) -> None:
    """A reading added on the server - a fan plugged in, a new probe - shows up on the next poll."""
    payload = copy.deepcopy(mock_sensors)
    payload["temperature"].append(
        {
            "id": "1767390512345",
            "index": 2,
            "name": "NVMe #3",
            "manufacturer": "Samsung",
            "model": "970 EVO Plus 1TB",
            "subtype": "temperature",
            "value": 33.05,
            "unit": "°C",
        }
    )
    mock_client.async_get_sensors.return_value = payload
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.sirius_sensor_nvme_3_temperature")
    assert state is not None
    assert state.state == "33.05"


async def test_renaming_a_reading_keeps_its_entity(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_sensors: dict[str, list[dict[str, Any]]],
) -> None:
    """Renaming a reading in MOS must not tear down and recreate the entity.

    The identity is MOS's own ``id``, not the name, so history and automations
    survive a rename.
    """
    entity_id = "sensor.sirius_sensor_fan_cpu_fan_speed"
    unique_id = er.async_get(hass).async_get(entity_id).unique_id

    payload = copy.deepcopy(mock_sensors)
    payload["fan"][0]["name"] = "Front Fan"
    payload["fan"][0]["value"] = 604
    mock_client.async_get_sensors.return_value = payload
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "604"
    assert er.async_get(hass).async_get(entity_id).unique_id == unique_id
