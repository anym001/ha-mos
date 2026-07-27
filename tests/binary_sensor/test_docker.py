"""Tests for the dynamic per-container Docker binary sensors (sourced from /docker/mos/containers)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_docker_update_available_reflects_payload(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A container with a newer remote image reports update_available=on."""
    assert hass.states.get("binary_sensor.sirius_pushbits_update_available").state == "on"
    assert hass.states.get("binary_sensor.sirius_nginx_update_available").state == "off"


async def test_docker_update_available_is_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """update_available is the one Docker container entity that IS diagnostic."""
    registry = er.async_get(hass)
    entry = registry.async_get("binary_sensor.sirius_pushbits_update_available")
    assert entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_docker_autostart_reflects_config(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Autostart reflects the container's configured autostart flag and is a regular entity."""
    assert hass.states.get("binary_sensor.sirius_pushbits_autostart").state == "on"
    assert hass.states.get("binary_sensor.sirius_nginx_autostart").state == "off"

    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.sirius_pushbits_autostart").entity_category is None
