"""Tests for the server-wide guest counters (aggregated over the coordinator's own lists)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from custom_components.mos.api import MOSApiClientCommunicationError
from custom_components.mos.const import (
    CONF_ENABLE_COMPOSE,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_VM,
    RESOURCE_STALE_GRACE_PERIOD,
    RESOURCE_STALE_MIN_FAILURES,
)
from homeassistant.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any
    from unittest.mock import AsyncMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant

# Which option creates which counters, so a group can be asserted on as a whole.
SUMMARY_SENSORS: dict[str, tuple[str, ...]] = {
    CONF_ENABLE_DOCKER: (
        "sensor.sirius_docker_containers_total",
        "sensor.sirius_docker_containers_running",
        "sensor.sirius_docker_updates_available",
    ),
    CONF_ENABLE_COMPOSE: (
        "sensor.sirius_compose_stacks_total",
        "sensor.sirius_compose_stacks_running",
        "sensor.sirius_compose_updates_available",
    ),
    CONF_ENABLE_LXC: (
        "sensor.sirius_lxc_containers_total",
        "sensor.sirius_lxc_containers_running",
    ),
    CONF_ENABLE_VM: (
        "sensor.sirius_virtual_machines_total",
        "sensor.sirius_virtual_machines_running",
    ),
}

ALL_SUMMARY_SENSORS = tuple(entity_id for group in SUMMARY_SENSORS.values() for entity_id in group)

TOTAL_SENSORS = tuple(entity_id for entity_id in ALL_SUMMARY_SENSORS if entity_id.endswith("_total"))
RUNNING_SENSORS = tuple(entity_id for entity_id in ALL_SUMMARY_SENSORS if entity_id.endswith("_running"))
CHANGING_SENSORS = tuple(entity_id for entity_id in ALL_SUMMARY_SENSORS if not entity_id.endswith("_total"))


async def test_counters_aggregate_each_guest_list(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Every fixture list holds two guests, one of them running."""
    for entity_id in TOTAL_SENSORS:
        assert hass.states.get(entity_id).state == "2", entity_id

    for entity_id in RUNNING_SENSORS:
        assert hass.states.get(entity_id).state == "1", entity_id


async def test_only_docker_and_compose_get_an_update_counter(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """MOS tracks no image or template version for an LXC container or a VM, so there is no flag to count."""
    assert hass.states.get("sensor.sirius_lxc_updates_available") is None
    assert hass.states.get("sensor.sirius_virtual_machines_updates_available") is None


async def test_only_an_explicit_update_flag_counts(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_containers: list[dict[str, Any]],
) -> None:
    """A container MOS could not check has no flag, which is not the same as being up to date."""
    assert hass.states.get("sensor.sirius_docker_updates_available").state == "1"

    mock_client.async_get_docker_containers.return_value = [
        {**container, "update_available": None} for container in mock_docker_containers
    ]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_docker_updates_available").state == "0"


async def test_the_compose_update_counter_reads_the_group_list(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_groups: list[dict[str, Any]],
) -> None:
    """A stack's update flag reaches it from its auto-created group, not from the stack list."""
    assert hass.states.get("sensor.sirius_compose_updates_available").state == "0"

    mock_client.async_get_docker_groups.return_value = [
        {**group, "update_available": True} if group["name"] == "hatest" else group for group in mock_docker_groups
    ]
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_compose_updates_available").state == "1"


async def test_the_counters_sit_on_the_server_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """They describe the host rather than one guest, so they belong next to the other server sensors."""
    registry = er.async_get(hass)
    server = dr.async_get(hass).async_get_device_by_identifier(
        (setup_integration.domain, setup_integration.entry_id), setup_integration.entry_id
    )
    assert server is not None

    for entity_id in ALL_SUMMARY_SENSORS:
        entry = registry.async_get(entity_id)
        assert entry is not None, entity_id
        assert entry.device_id == server.id, entity_id
        assert entry.entity_category is None, entity_id


async def test_only_the_changing_counters_carry_a_state_class(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """How many guests exist is a property of the setup; how many run or need an update is worth a history."""
    for entity_id in TOTAL_SENSORS:
        assert ATTR_STATE_CLASS not in hass.states.get(entity_id).attributes, entity_id

    for entity_id in CHANGING_SENSORS:
        state = hass.states.get(entity_id)
        assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT, entity_id


async def test_a_stale_engine_list_only_takes_the_docker_running_counter_down(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """A running state too old to trust would read as containers having stopped.

    Only the Docker counter depends on it: a stack reports its own running flag,
    and an LXC container or a VM carries its state in the list that names it.
    """
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
    assert hass.states.get("sensor.sirius_compose_stacks_running").state == "1"
    assert hass.states.get("sensor.sirius_lxc_containers_running").state == "1"
    assert hass.states.get("sensor.sirius_virtual_machines_running").state == "1"


async def test_a_stale_group_list_only_takes_the_compose_update_counter_down(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    advance_clock: Callable[[float], None],
) -> None:
    """The group list carries the update flag alone; the stacks answer everything else themselves."""
    mock_client.async_get_docker_groups.side_effect = MOSApiClientCommunicationError("timeout")
    coordinator = setup_integration.runtime_data.coordinator
    for _ in range(RESOURCE_STALE_MIN_FAILURES):
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds())
        await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.stale_resources == frozenset({"docker_groups"})
    assert hass.states.get("sensor.sirius_compose_updates_available").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.sirius_compose_stacks_total").state == "2"
    assert hass.states.get("sensor.sirius_compose_stacks_running").state == "1"


@pytest.mark.parametrize("option", list(SUMMARY_SENSORS))
async def test_each_option_governs_its_own_counters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
    option: str,
) -> None:
    """A counter summarizes a group of entities, so it follows the option that decides those exist."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={option: False})

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    for entity_id in SUMMARY_SENSORS[option]:
        assert hass.states.get(entity_id) is None, entity_id

    for other_option, entity_ids in SUMMARY_SENSORS.items():
        if other_option == option:
            continue
        for entity_id in entity_ids:
            assert hass.states.get(entity_id) is not None, entity_id
