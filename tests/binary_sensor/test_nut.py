"""Tests for the UPS binary sensors (sourced from /nut/status)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

FLAG_SENSORS = (
    "binary_sensor.sirius_ups_on_line_power",
    "binary_sensor.sirius_ups_on_battery",
    "binary_sensor.sirius_ups_battery_low",
    "binary_sensor.sirius_ups_battery_charging",
)


async def _refresh_with_status(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    client: AsyncMock,
    payload: dict[str, Any],
    status: str,
) -> None:
    """Poll once with the UPS reporting ``status``."""
    client.async_get_nut_status.return_value = {**payload, "status": status}
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_flags_reflect_the_reported_status(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A UPS on mains power ("OL") sets that flag and no other."""
    assert hass.states.get("binary_sensor.sirius_ups_connected").state == STATE_ON
    assert hass.states.get("binary_sensor.sirius_ups_on_line_power").state == STATE_ON
    assert hass.states.get("binary_sensor.sirius_ups_on_battery").state == STATE_OFF
    assert hass.states.get("binary_sensor.sirius_ups_battery_low").state == STATE_OFF
    assert hass.states.get("binary_sensor.sirius_ups_battery_charging").state == STATE_OFF


@pytest.mark.parametrize(
    ("status", "expected_on"),
    [
        ("OB", {"binary_sensor.sirius_ups_on_battery"}),
        (
            "OB LB",
            {"binary_sensor.sirius_ups_on_battery", "binary_sensor.sirius_ups_battery_low"},
        ),
        (
            "OL CHRG",
            {"binary_sensor.sirius_ups_on_line_power", "binary_sensor.sirius_ups_battery_charging"},
        ),
    ],
)
async def test_every_flag_of_a_combined_status_is_read(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_nut: dict[str, Any],
    status: str,
    expected_on: set[str],
) -> None:
    """NUT reports several flags at once, so each is tested for membership, not equality."""
    await _refresh_with_status(hass, setup_integration, mock_client, mock_nut, status)

    for entity_id in FLAG_SENSORS:
        expected = STATE_ON if entity_id in expected_on else STATE_OFF
        assert hass.states.get(entity_id).state == expected, entity_id


async def test_connected_keeps_reporting_when_the_ups_disappears(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """The connectivity sensor reports the disconnection; the flag sensors have nothing to say.

    NUT sends no status at all for a UPS it cannot reach, so claiming "not on
    battery" would be an invention - unlike "not connected", which is the fact.
    """
    mock_client.async_get_nut_status.return_value = {"reachable": False, "name": None, "status": None}
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.sirius_ups_connected").state == STATE_OFF
    for entity_id in FLAG_SENSORS:
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE, entity_id
