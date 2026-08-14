"""Tests for the dynamic per-VM sensors (sourced from /vm/machines/usage)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_vm_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each VM gets its own cpu_usage/memory_usage sensors, on its own device."""
    cpu_usage = hass.states.get("sensor.sirius_vm_test_cpu_usage")
    assert cpu_usage is not None
    assert cpu_usage.state == "12.5"

    memory_usage = hass.states.get("sensor.sirius_vm_test_memory_usage")
    assert memory_usage is not None
    assert memory_usage.state != "unknown"


async def test_vm_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_vm_machines: list[dict],
) -> None:
    """When a VM disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_vm_legacy_cpu_usage") is not None

    mock_client.async_get_vm_machines.return_value = [mock_vm_machines[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_vm_legacy_cpu_usage") is None
    assert hass.states.get("sensor.sirius_vm_test_cpu_usage") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_vm_legacy_cpu_usage") is None


async def test_vm_state_sensor_carries_the_running_state(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The state sensor exposes the VM state as a value, which the power switch cannot."""
    running = hass.states.get("sensor.sirius_vm_test_state")
    assert running is not None
    assert running.state == "running"

    stopped = hass.states.get("sensor.sirius_vm_legacy_state")
    assert stopped is not None
    assert stopped.state == "stopped"


async def test_vm_state_sensor_offers_only_the_states_mos_reports(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """MOS declares the VM state as a closed enum of two, unlike LXC's open-ended one.

    libvirt underneath knows many more (paused, crashed, pmsuspended, ...), but
    MOS collapses them before answering, so following libvirt here would offer
    states that can never arrive.
    """
    state = hass.states.get("sensor.sirius_vm_test_state")
    assert state is not None
    assert set(state.attributes["options"]) == {"running", "stopped"}
