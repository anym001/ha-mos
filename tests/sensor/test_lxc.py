"""Tests for the dynamic per-container LXC sensors (sourced from /lxc/containers/usage)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_lxc_container_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each LXC container gets its own cpu_usage/memory_usage sensors, on its own device."""
    cpu_usage = hass.states.get("sensor.sirius_lxc_database_cpu_usage")
    assert cpu_usage is not None
    assert cpu_usage.state == "25.5"

    memory_usage = hass.states.get("sensor.sirius_lxc_database_memory_usage")
    assert memory_usage is not None
    assert memory_usage.state != "unknown"


async def test_lxc_container_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_lxc_containers: list[dict],
) -> None:
    """When a container disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_lxc_webserver_cpu_usage") is not None

    mock_client.async_get_lxc_containers.return_value = [mock_lxc_containers[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_lxc_webserver_cpu_usage") is None
    assert hass.states.get("sensor.sirius_lxc_database_cpu_usage") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_lxc_webserver_cpu_usage") is None


async def test_lxc_state_sensor_carries_the_running_state(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The state sensor exposes the container state as a value, which the power switch cannot.

    The switch reduces the state to on/off, so a container that is freezing or
    aborting is indistinguishable from a stopped one without this.
    """
    running = hass.states.get("sensor.sirius_lxc_database_state")
    assert running is not None
    assert running.state == "running"

    stopped = hass.states.get("sensor.sirius_lxc_webserver_state")
    assert stopped is not None
    assert stopped.state == "stopped"


async def test_lxc_state_sensor_accepts_every_lxc_state(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Every state LXC can report is an allowed option.

    MOS documents the field as "running, stopped, etc." rather than as a closed
    set, and a state missing from an enum sensor's options is a runtime error -
    on a MOS server the freeze states are reachable straight from the web UI.
    """
    state = hass.states.get("sensor.sirius_lxc_database_state")
    assert state is not None
    assert set(state.attributes["options"]) == {
        "aborting",
        "freezing",
        "frozen",
        "running",
        "starting",
        "stopped",
        "stopping",
        "thawed",
    }


async def test_lxc_state_sensor_carries_the_server_hosted_icon(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
) -> None:
    """MOS serves its own artwork, so a card shows the container's icon without templating.

    ``database`` has no custom icon, so the picture is its distribution's stock
    artwork; ``webserver`` has one uploaded under its own name.
    """
    mock_client.async_static_asset_exists.return_value = True
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()

    stock = hass.states.get("sensor.sirius_lxc_database_state")
    assert stock is not None
    assert stock.attributes["entity_picture"] == "http://10.0.1.30:80/os_icons/debian.png"

    custom = hass.states.get("sensor.sirius_lxc_webserver_state")
    assert custom is not None
    assert custom.attributes["entity_picture"] == "http://10.0.1.30:80/lxc_custom/webserver.png"


async def test_lxc_state_sensor_has_no_picture_when_the_server_hosts_none(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A 404 handed to the frontend renders as a broken image, so no icon means no attribute."""
    state = hass.states.get("sensor.sirius_lxc_database_state")
    assert state is not None
    assert "entity_picture" not in state.attributes
