"""Tests for the dynamic per-stack Compose binary sensors (sourced from /docker/mos/compose/stacks)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant


async def test_update_available_comes_from_the_group(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The stack list has no update flag; the group MOS auto-creates for the stack does."""
    state = hass.states.get("binary_sensor.sirius_compose_hatest_update_available")
    assert state is not None
    assert state.state == STATE_OFF


async def test_a_stack_without_a_group_reports_unknown(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Off would claim the stack is up to date, which nothing on the server ever said."""
    state = hass.states.get("binary_sensor.sirius_compose_orphan_update_available")
    assert state is not None
    assert state.state == STATE_UNKNOWN


async def test_autostart_comes_from_the_stack_itself(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Autostart is on the stack payload, so it stays right even when the group list fails."""
    off = hass.states.get("binary_sensor.sirius_compose_hatest_autostart")
    assert off is not None
    assert off.state == STATE_OFF

    on = hass.states.get("binary_sensor.sirius_compose_orphan_autostart")
    assert on is not None
    assert on.state == STATE_ON


async def test_health_is_aggregated_from_the_member_containers(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """MOS reports no stack-level health, so one failing service is what makes the stack a problem."""
    state = hass.states.get("binary_sensor.sirius_compose_hatest_health")
    assert state is not None
    assert state.state == STATE_ON


async def test_a_stack_with_nothing_running_has_no_health_verdict(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Docker leaves a stopped container's health at whatever it last was, which is no verdict."""
    state = hass.states.get("binary_sensor.sirius_compose_orphan_health")
    assert state is not None
    assert state.state == STATE_UNKNOWN


async def test_stack_binary_sensors_share_the_sensors_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Both platforms describe one stack, so they must land on one device rather than two."""
    registry = er.async_get(hass)
    binary_sensor = registry.async_get("binary_sensor.sirius_compose_hatest_autostart")
    sensor = registry.async_get("sensor.sirius_compose_hatest_state")

    assert binary_sensor is not None
    assert sensor is not None
    assert binary_sensor.device_id == sensor.device_id
    assert binary_sensor.unique_id == f"{setup_integration.entry_id}_compose_hatest_autostart"
    assert setup_integration.domain == DOMAIN
