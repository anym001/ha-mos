"""Tests for the dynamic per-stack Compose sensors (sourced from /docker/mos/compose/stacks)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import DOMAIN, MOSDeviceKind
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant


async def test_stack_state_sensor_maps_the_running_flag(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """MOS reports one boolean for the whole stack, which the enum sensor turns into a readable state."""
    running = hass.states.get("sensor.sirius_compose_hatest_state")
    assert running is not None
    assert running.state == "running"

    stopped = hass.states.get("sensor.sirius_compose_orphan_state")
    assert stopped is not None
    assert stopped.state == "stopped"


async def test_stack_state_sensor_carries_the_card_attributes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """One entity carries everything a dashboard row needs, so a card needs no templating."""
    state = hass.states.get("sensor.sirius_compose_hatest_state")
    assert state is not None

    assert state.attributes["web_ui_url"] == "http://10.0.1.30:18099"
    assert state.attributes["services"] == ["alpha", "beta"]
    assert state.attributes["containers"] == ["compose_hatest-alpha-1", "compose_hatest-beta-1"]
    assert (
        state.attributes["entity_picture"] == "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/docker.png"
    )


async def test_a_stack_without_a_web_interface_omits_the_attribute(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A blank link on a card is worse than no link row at all."""
    state = hass.states.get("sensor.sirius_compose_orphan_state")
    assert state is not None
    assert "web_ui_url" not in state.attributes
    assert "entity_picture" not in state.attributes


async def test_counters_come_from_the_auto_created_group(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The stack list carries no counters; the group MOS creates for the stack does."""
    running = hass.states.get("sensor.sirius_compose_hatest_running_containers")
    assert running is not None
    assert running.state == "2"

    total = hass.states.get("sensor.sirius_compose_hatest_containers")
    assert total is not None
    assert total.state == "2"


async def test_a_stack_without_a_group_reports_unknown_counters(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Unknown is the honest answer - a zero would claim the stack has no containers."""
    running = hass.states.get("sensor.sirius_compose_orphan_running_containers")
    assert running is not None
    assert running.state == STATE_UNKNOWN

    total = hass.states.get("sensor.sirius_compose_orphan_containers")
    assert total is not None
    assert total.state == STATE_UNKNOWN


async def test_each_stack_gets_its_own_device_marked_as_a_stack(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """``model_id`` is what lets a card select every stack without parsing identifiers."""
    registry = dr.async_get(hass)
    device = registry.async_get_device_by_identifier(
        (DOMAIN, f"{setup_integration.entry_id}_compose_hatest"), setup_integration.entry_id
    )

    assert device is not None
    assert device.model_id == MOSDeviceKind.COMPOSE
    assert device.model == "Compose Stack"
    assert device.configuration_url == "http://10.0.1.30:18099"


async def test_stack_sensors_are_scoped_to_the_entry(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The unique ID carries the entry, so two servers with a same-named stack do not collide."""
    entity = er.async_get(hass).async_get("sensor.sirius_compose_hatest_state")

    assert entity is not None
    assert entity.unique_id == f"{setup_integration.entry_id}_compose_hatest_state"
