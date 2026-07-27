"""Tests for the dynamic per-container LXC binary sensors (sourced from /lxc/containers/usage)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_lxc_running_reflects_state(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A running container reports running=on, a stopped one reports running=off."""
    assert hass.states.get("binary_sensor.sirius_database_running").state == "on"
    assert hass.states.get("binary_sensor.sirius_webserver_running").state == "off"


async def test_lxc_autostart_reflects_config(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Autostart reflects the container's configured autostart flag."""
    assert hass.states.get("binary_sensor.sirius_database_autostart").state == "on"
    assert hass.states.get("binary_sensor.sirius_webserver_autostart").state == "off"


async def test_lxc_entities_are_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Container running/autostart are regular sensors, not diagnostic."""
    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.sirius_database_running").entity_category is None
    assert registry.async_get("binary_sensor.sirius_database_autostart").entity_category is None
