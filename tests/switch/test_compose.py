"""Tests for the dynamic per-stack Compose power switch (MOS compose endpoints)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from custom_components.mos.api import MOSApiClientCommunicationError
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant


async def test_switch_reflects_the_stacks_running_flag(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A stack's own ``running`` flag is the switch position - no second resource needed."""
    assert hass.states.get("switch.sirius_compose_hatest_power").state == "on"
    assert hass.states.get("switch.sirius_compose_orphan_power").state == "off"


async def test_switch_is_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The power switch is a regular (non-diagnostic) entity."""
    registry = er.async_get(hass)
    assert registry.async_get("switch.sirius_compose_hatest_power").entity_category is None


async def test_turn_on_starts_the_whole_stack(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """MOS exposes no per-service start, so the switch acts on the stack by name."""
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.sirius_compose_orphan_power"},
        blocking=True,
    )

    mock_client.async_start_compose_stack.assert_called_once_with("orphan")


async def test_turn_off_stops_the_whole_stack(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Stopping the switch stops every service in the stack."""
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.sirius_compose_hatest_power"},
        blocking=True,
    )

    mock_client.async_stop_compose_stack.assert_called_once_with("hatest")


async def test_stopping_also_zeroes_the_running_counter(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A stopped stack has no running services - a fact, unlike how many a start brings up."""
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.sirius_compose_hatest_power"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_compose_hatest_running_containers").state == "0"
    assert hass.states.get("sensor.sirius_compose_hatest_containers").state == "2"
    assert hass.states.get("sensor.sirius_compose_hatest_state").state == "stopped"


async def test_starting_leaves_the_running_counter_to_the_next_poll(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """How many services actually came up is not knowable from a successful start."""
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.sirius_compose_orphan_power"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get("switch.sirius_compose_orphan_power").state == "on"
    assert hass.states.get("sensor.sirius_compose_orphan_running_containers").state == "unknown"


@pytest.mark.parametrize(
    ("service", "entity_id", "method"),
    [
        ("turn_on", "switch.sirius_compose_orphan_power", "async_start_compose_stack"),
        ("turn_off", "switch.sirius_compose_hatest_power", "async_stop_compose_stack"),
    ],
)
async def test_a_failed_action_raises_rather_than_silently_doing_nothing(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    *,
    service: str,
    entity_id: str,
    method: str,
) -> None:
    """A stack action that fails must reach the user, not just the log."""
    getattr(mock_client, method).side_effect = MOSApiClientCommunicationError("timeout")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("switch", service, {"entity_id": entity_id}, blocking=True)
