"""Tests for the UPS binary sensors (sourced from /nut/status)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

FLAG_SENSORS = (
    "binary_sensor.sirius_ups_on_line_power",
    "binary_sensor.sirius_ups_on_battery",
    "binary_sensor.sirius_ups_battery_low",
    "binary_sensor.sirius_ups_battery_charging",
    "binary_sensor.sirius_ups_battery_discharging",
    "binary_sensor.sirius_ups_battery_high",
    "binary_sensor.sirius_ups_replace_battery",
    "binary_sensor.sirius_ups_bypass_active",
    "binary_sensor.sirius_ups_calibrating",
    "binary_sensor.sirius_ups_output_off",
    "binary_sensor.sirius_ups_overload",
    "binary_sensor.sirius_ups_voltage_trim",
    "binary_sensor.sirius_ups_voltage_boost",
    "binary_sensor.sirius_ups_forced_shutdown",
    "binary_sensor.sirius_ups_alarm",
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
        # The flags beyond the four primary ones, each on its own and in the
        # combinations a UPS actually reports them in.
        ("RB", {"binary_sensor.sirius_ups_replace_battery"}),
        ("HB", {"binary_sensor.sirius_ups_battery_high"}),
        ("BYPASS", {"binary_sensor.sirius_ups_bypass_active"}),
        ("CAL", {"binary_sensor.sirius_ups_calibrating"}),
        ("OFF", {"binary_sensor.sirius_ups_output_off"}),
        ("OVER", {"binary_sensor.sirius_ups_overload"}),
        ("TRIM", {"binary_sensor.sirius_ups_voltage_trim"}),
        ("BOOST", {"binary_sensor.sirius_ups_voltage_boost"}),
        ("ALARM", {"binary_sensor.sirius_ups_alarm"}),
        (
            "OB DISCHRG LB",
            {
                "binary_sensor.sirius_ups_on_battery",
                "binary_sensor.sirius_ups_battery_discharging",
                "binary_sensor.sirius_ups_battery_low",
            },
        ),
        (
            "OB FSD LB",
            {
                "binary_sensor.sirius_ups_on_battery",
                "binary_sensor.sirius_ups_forced_shutdown",
                "binary_sensor.sirius_ups_battery_low",
            },
        ),
    ],
)
async def test_every_flag_of_a_combined_status_is_read(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_nut: dict[str, Any],
    *,
    status: str,
    expected_on: set[str],
) -> None:
    """NUT reports several flags at once, so each is tested for membership, not equality."""
    await _refresh_with_status(hass, setup_integration, mock_client, mock_nut, status)

    for entity_id in FLAG_SENSORS:
        expected = STATE_ON if entity_id in expected_on else STATE_OFF
        assert hass.states.get(entity_id).state == expected, entity_id


async def test_secondary_flags_are_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Both sides of the split are pinned, not just the diagnostic one.

    Listing only what should be diagnostic lets a later edit quietly promote a
    flag onto the primary card without failing anything; naming the primary
    ones too is what catches that.
    """
    registry = er.async_get(hass)

    for entity_id in (
        "binary_sensor.sirius_ups_replace_battery",
        "binary_sensor.sirius_ups_bypass_active",
        "binary_sensor.sirius_ups_overload",
        "binary_sensor.sirius_ups_forced_shutdown",
        "binary_sensor.sirius_ups_output_off",
        "binary_sensor.sirius_ups_alarm",
        "binary_sensor.sirius_ups_voltage_boost",
        "binary_sensor.sirius_ups_calibrating",
    ):
        assert registry.async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC, entity_id

    for entity_id in (
        "binary_sensor.sirius_ups_on_battery",
        "binary_sensor.sirius_ups_battery_low",
        "binary_sensor.sirius_ups_battery_charging",
        "binary_sensor.sirius_ups_battery_discharging",
    ):
        assert registry.async_get(entity_id).entity_category is None, entity_id


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
