"""Tests for the server-wide Docker counters (aggregated over /docker/mos/containers)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from custom_components.mos.api import MOSApiClientCommunicationError
from custom_components.mos.const import CONF_ENABLE_DOCKER, RESOURCE_STALE_GRACE_PERIOD, RESOURCE_STALE_MIN_FAILURES
from homeassistant.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any
    from unittest.mock import AsyncMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant

SUMMARY_SENSORS = (
    "sensor.sirius_docker_containers_total",
    "sensor.sirius_docker_containers_running",
    "sensor.sirius_docker_updates_available",
)


async def test_counters_aggregate_the_container_list(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The fixture has two containers, one of them running, one of them with an update waiting."""
    assert hass.states.get("sensor.sirius_docker_containers_total").state == "2"
    assert hass.states.get("sensor.sirius_docker_containers_running").state == "1"
    assert hass.states.get("sensor.sirius_docker_updates_available").state == "1"


async def test_only_an_explicit_update_flag_counts(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict[str, Any]],
) -> None:
    """A container MOS could not check has no flag, which is not the same as being up to date."""
    mock_client.async_get_docker_containers.return_value = [
        {**container, "update_available": None} for container in mock_docker_containers
    ]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_updates_available").state == "0"


async def test_the_counters_sit_on_the_server_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """They describe the host rather than one container, so they belong next to the other server sensors."""
    registry = er.async_get(hass)
    server = dr.async_get(hass).async_get_device_by_identifier(
        (setup_integration.domain, setup_integration.entry_id), setup_integration.entry_id
    )
    assert server is not None

    for entity_id in SUMMARY_SENSORS:
        entry = registry.async_get(entity_id)
        assert entry is not None, entity_id
        assert entry.device_id == server.id, entity_id
        assert entry.entity_category is None, entity_id


async def test_only_the_changing_counters_carry_a_state_class(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """How many containers exist is a property of the setup; how many run or need an update is worth a history."""
    assert ATTR_STATE_CLASS not in hass.states.get("sensor.sirius_docker_containers_total").attributes

    for entity_id in ("sensor.sirius_docker_containers_running", "sensor.sirius_docker_updates_available"):
        state = hass.states.get(entity_id)
        assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT, entity_id


async def test_a_stale_engine_list_only_takes_the_running_counter_down(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A running state too old to trust would read as containers having stopped; the other two do not need it."""
    mock_client.async_get_docker_engine_containers.side_effect = MOSApiClientCommunicationError("timeout")
    coordinator = setup_integration.runtime_data.coordinator
    for _ in range(RESOURCE_STALE_MIN_FAILURES):
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds())
        await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.stale_resources == frozenset({"docker_engine_containers"})
    assert hass.states.get("sensor.sirius_docker_containers_running").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.sirius_docker_containers_total").state == "2"
    assert hass.states.get("sensor.sirius_docker_updates_available").state == "1"


async def test_the_docker_option_governs_the_counters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """They summarize the Docker entities, so they follow the option that decides those exist."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={CONF_ENABLE_DOCKER: False})

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    for entity_id in SUMMARY_SENSORS:
        assert hass.states.get(entity_id) is None, entity_id
