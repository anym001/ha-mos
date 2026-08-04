"""Tests for the UPS sensors (sourced from /nut/status)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import CONF_ENABLE_NUT
from homeassistant.components.sensor import ATTR_STATE_CLASS
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

UPS_OFFLINE = {"reachable": False, "name": None, "status": None}


async def test_ups_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The identifying and measured values come straight from the payload."""
    assert hass.states.get("sensor.sirius_ups_status").state == "OL"
    assert hass.states.get("sensor.sirius_ups_name").state == "ups"
    assert hass.states.get("sensor.sirius_ups_manufacturer").state == "CPS"
    assert hass.states.get("sensor.sirius_ups_model").state == "ACMT1000E"
    assert hass.states.get("sensor.sirius_ups_serial_number").state == "XTBLP2000067"
    assert hass.states.get("sensor.sirius_ups_load").state == "6"
    assert hass.states.get("sensor.sirius_ups_battery").state == "100"
    assert hass.states.get("sensor.sirius_ups_battery_voltage").state == "24"
    assert hass.states.get("sensor.sirius_ups_input_voltage").state == "228"
    assert hass.states.get("sensor.sirius_ups_output_frequency").state == "50"


async def test_battery_runtime_is_shown_in_minutes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """NUT reports the runtime in seconds; a runtime is read in minutes."""
    state = hass.states.get("sensor.sirius_ups_battery_runtime")
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTime.MINUTES
    assert float(state.state) == 15780 / 60


async def test_configured_ratings_are_not_measurements(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The nameplate rating and the low-battery threshold stay out of long-term statistics.

    Both are settings the UPS reports back, not readings, so a state class would
    have Home Assistant record a statistic for a value that never moves.
    """
    assert ATTR_STATE_CLASS not in hass.states.get("sensor.sirius_ups_nominal_power").attributes
    assert ATTR_STATE_CLASS not in hass.states.get("sensor.sirius_ups_battery_low_threshold").attributes
    assert ATTR_STATE_CLASS in hass.states.get("sensor.sirius_ups_battery").attributes


async def test_sensors_go_unavailable_when_the_ups_stops_answering(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A UPS that stops answering leaves its sensors unavailable rather than at a stale value.

    MOS keeps answering the endpoint with ``reachable: false``, so this is not a
    failed poll: the entities have to judge it themselves.
    """
    assert hass.states.get("sensor.sirius_ups_input_voltage").state == "228"

    mock_client.async_get_nut_status.return_value = UPS_OFFLINE
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_ups_input_voltage").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.sirius_ups_status").state == STATE_UNAVAILABLE


async def test_sensors_appear_only_once_a_ups_has_answered(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
    mock_nut: dict[str, Any],
) -> None:
    """No UPS on the first poll means no UPS entities; one attached later creates them.

    A server with no UPS would otherwise get a full set of permanently
    unavailable entities.
    """
    mock_config_entry.add_to_hass(hass)
    mock_client.async_get_nut_status.return_value = UPS_OFFLINE

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert hass.states.get("sensor.sirius_ups_status") is None

        mock_client.async_get_nut_status.return_value = mock_nut
        await mock_config_entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_ups_status").state == "OL"


async def test_ups_entities_get_their_own_device_linked_to_server(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """UPS entities live on their own device, linked to the server device via via_device.

    The unique_id stays exactly what it was when these entities lived on the
    server device, so existing users are moved to the new device automatically
    instead of getting a duplicate entity.
    """
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    server_device = device_registry.async_get_device(identifiers={("mos", setup_integration.entry_id)})
    assert server_device is not None

    entry = entity_registry.async_get("sensor.sirius_ups_status")
    assert entry.unique_id == f"{setup_integration.entry_id}_ups_status"

    ups_device = device_registry.async_get(entry.device_id)
    assert ups_device.name == "Sirius UPS"
    assert ups_device.via_device_id == server_device.id
    assert ups_device.id != server_device.id


async def test_disabled_category_creates_no_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """With the UPS category switched off the endpoint is not even asked for."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={CONF_ENABLE_NUT: False})

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    mock_client.async_get_nut_status.assert_not_called()
    assert hass.states.get("sensor.sirius_ups_status") is None
