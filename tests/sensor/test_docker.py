"""Tests for the dynamic per-container Docker sensors (sourced from /docker/mos/containers)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def test_docker_container_sensor_values(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each Docker container gets its own installed_version/latest_version sensors, on its own device."""
    installed = hass.states.get("sensor.sirius_docker_pushbits_installed_version")
    assert installed is not None
    assert installed.state == "1.20.2"

    latest = hass.states.get("sensor.sirius_docker_pushbits_latest_version")
    assert latest is not None
    assert latest.state == "1.21.0"


async def test_docker_state_sensor_carries_the_running_state(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The state sensor exposes the running state as a value, which the power switch cannot."""
    running = hass.states.get("sensor.sirius_docker_pushbits_state")
    assert running is not None
    assert running.state == "running"

    stopped = hass.states.get("sensor.sirius_docker_nginx_state")
    assert stopped is not None
    assert stopped.state == "exited"


async def test_docker_state_sensor_carries_the_card_attributes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """One entity carries everything a dashboard row needs, so a card needs no templating."""
    state = hass.states.get("sensor.sirius_docker_pushbits_state")
    assert state is not None

    # 8080 is the container port named in the mos.webui label; 8081 is where it
    # is actually published, which is what a click has to go to.
    assert state.attributes["web_ui_url"] == "http://10.0.1.30:8081/"
    assert state.attributes["repo"] == "ghcr.io/pushbits/server"
    assert state.attributes["network_mode"] == "bridge"
    assert state.attributes["image_title"] == "server"
    assert state.attributes["image_source"] == "https://github.com/pushbits/server"
    assert state.attributes["entity_picture"] == "https://raw.githubusercontent.com/pushbits/logo/main/logo.png"


async def test_stopped_container_still_gets_its_link_from_the_template(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Docker publishes no ports for a stopped container, so the link has to come from the cached template."""
    state = hass.states.get("sensor.sirius_docker_nginx_state")
    assert state is not None
    assert state.attributes["web_ui_url"] == "http://10.0.1.30:8080/"


async def test_container_device_links_to_the_container_web_interface(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The device page points at the container's own web interface, not at the MOS server."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, f"{setup_integration.entry_id}_docker_PushBits"), setup_integration.entry_id
    )

    assert device is not None
    assert device.configuration_url == "http://10.0.1.30:8081/"


async def test_docker_container_removed_from_api_removes_its_sensors(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict],
) -> None:
    """When a container disappears from a later refresh, its entities are removed."""
    assert hass.states.get("sensor.sirius_docker_nginx_installed_version") is not None

    mock_client.async_get_docker_containers.return_value = [mock_docker_containers[0]]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_nginx_installed_version") is None
    assert hass.states.get("sensor.sirius_docker_pushbits_installed_version") is not None

    registry = er.async_get(hass)
    assert registry.async_get("sensor.sirius_docker_nginx_installed_version") is None
