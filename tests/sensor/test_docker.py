"""Tests for the dynamic per-container Docker sensors (sourced from /docker/mos/containers)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import CONF_ENABLE_DOCKER_STATS, DOMAIN
from homeassistant.const import STATE_UNKNOWN
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


async def test_stats_sensors_are_absent_unless_the_option_is_on(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """The stats option is off by default, so no stats sensor exists and nothing is measured."""
    assert hass.states.get("sensor.sirius_docker_pushbits_cpu_usage") is None
    assert hass.states.get("sensor.sirius_docker_pushbits_memory_usage") is None
    assert hass.states.get("sensor.sirius_docker_pushbits_memory_percent") is None
    mock_client.async_get_docker_container_stats.assert_not_awaited()


async def test_stats_sensors_report_the_containers_usage(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """With the option on, a running container reports memory, then CPU a poll later.

    The refreshes are explicit because the very first poll runs before any entity
    exists: with no context registered yet, nothing is measured. The poll after
    that measures the container and establishes its CPU baseline, and the one
    after that is the first to derive a percentage - see
    ``_async_add_docker_stats`` and ``DockerStatsCollector``.
    """
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_DOCKER_STATS: True})
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_pushbits_cpu_usage").state == STATE_UNKNOWN

    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_pushbits_memory_percent").state == "12.5"
    # Reported in bytes, displayed in mebibytes: 67108864 B is 64 MiB.
    assert hass.states.get("sensor.sirius_docker_pushbits_memory_usage").state == "64.0"
    assert hass.states.get("sensor.sirius_docker_pushbits_cpu_usage").state == STATE_UNKNOWN

    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_pushbits_cpu_usage").state == "25.0"


async def test_stopped_container_reports_no_usage(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A stopped container is never measured, so its sensors stay blank rather than reading zero."""
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_DOCKER_STATS: True})
    await hass.async_block_till_done()
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_nginx_cpu_usage").state == STATE_UNKNOWN
    mock_client.async_get_docker_container_stats.assert_awaited_once_with("PushBits")


async def test_disabling_a_containers_stats_sensors_stops_measuring_it(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Disabling every stats sensor of a container drops it from the poll.

    This is the whole point of the coordinator context: a request per container
    is only worth paying while something is displaying the result.
    """
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_DOCKER_STATS: True})
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    for key in ("cpu_usage", "memory_usage", "memory_percent"):
        registry.async_update_entity(
            f"sensor.sirius_docker_pushbits_{key}",
            disabled_by=er.RegistryEntryDisabler.USER,
        )
    await hass.async_block_till_done()

    mock_client.async_get_docker_container_stats.reset_mock()
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    mock_client.async_get_docker_container_stats.assert_not_awaited()


async def test_the_server_hosted_docker_icon_wins_over_the_template_cdn(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
) -> None:
    """Same picture either way, but the local copy also loads on a browser with no internet access."""
    mock_client.async_static_asset_exists.return_value = True
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.sirius_docker_pushbits_state")
    assert state is not None
    assert state.attributes["entity_picture"] == "http://10.0.1.30:80/docker_icons/PushBits.png"
