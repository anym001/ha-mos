"""Tests for the dynamic per-container LXC power switch (starts/stops via /lxc/containers/{name})."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientCommunicationError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


async def test_lxc_switch_reflects_running_state(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A running container's switch is on, a stopped one's is off."""
    assert hass.states.get("switch.sirius_lxc_database_power").state == "on"
    assert hass.states.get("switch.sirius_lxc_webserver_power").state == "off"


async def test_lxc_switch_is_not_diagnostic(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The power switch is a regular (non-diagnostic) entity."""
    registry = er.async_get(hass)
    assert registry.async_get("switch.sirius_lxc_database_power").entity_category is None


async def test_turn_on_starts_the_container_and_refreshes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Turning the switch on calls the start endpoint for that container and refreshes data."""
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.sirius_lxc_webserver_power"},
        blocking=True,
    )

    mock_client.async_start_lxc_container.assert_called_once_with("webserver")


async def test_turn_off_stops_the_container_and_refreshes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Turning the switch off calls the stop endpoint for that container and refreshes data."""
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.sirius_lxc_database_power"},
        blocking=True,
    )

    mock_client.async_stop_lxc_container.assert_called_once_with("database")


async def test_turn_on_failure_raises_home_assistant_error(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A failed start call surfaces as a HomeAssistantError, not a silent no-op."""
    mock_client.async_start_lxc_container.side_effect = MOSApiClientCommunicationError("timeout")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.sirius_lxc_webserver_power"},
            blocking=True,
        )
