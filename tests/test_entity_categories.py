"""Regression test for the Sensor/Diagnostic entity_category split.

Only entities that genuinely serve diagnosing a problem or a pending action
should be EntityCategory.DIAGNOSTIC: a disk's SMART warning, a pool's health
problem, a Docker container's update-available flag, and the UPS flags
reporting the UPS's own condition rather than the mains supply it watches.
Everything else (system info, pool usage/free space, disk power
status/model/type, service status, pool maintenance operations, LXC/Docker
container state, and the UPS sensors and readings) is a regular sensor.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

DIAGNOSTIC_ENTITY_SUFFIXES = ("_smart_warning", "_problem", "_update_available")

# NUT reports the UPS condition as a set of status flags, one binary sensor
# each. The diagnostic half shares no naming suffix with the rest, so it is
# spelled out - which also makes moving a flag across the split a visible edit.
DIAGNOSTIC_UPS_TRANSLATION_KEYS = frozenset(
    {
        "ups_discharging",
        "ups_battery_high",
        "ups_calibrating",
        "ups_replace_battery",
        "ups_bypass",
        "ups_output_off",
        "ups_overload",
        "ups_voltage_trim",
        "ups_voltage_boost",
        "ups_forced_shutdown",
        "ups_alarm",
    }
)


async def test_only_smart_warning_and_problem_are_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Every mos entity is DIAGNOSTIC iff its id ends in _smart_warning, _problem or _update_available, or it is a diagnostic UPS flag."""
    registry = er.async_get(hass)
    mos_entities = [entry for entry in registry.entities.values() if entry.platform == "mos"]
    assert mos_entities, "expected mos entities to be registered"

    for entry in mos_entities:
        should_be_diagnostic = (
            entry.entity_id.endswith(DIAGNOSTIC_ENTITY_SUFFIXES)
            or entry.translation_key in DIAGNOSTIC_UPS_TRANSLATION_KEYS
        )
        if should_be_diagnostic:
            assert entry.entity_category is EntityCategory.DIAGNOSTIC, f"{entry.entity_id} should be DIAGNOSTIC"
        else:
            assert entry.entity_category is None, f"{entry.entity_id} should not be DIAGNOSTIC"
