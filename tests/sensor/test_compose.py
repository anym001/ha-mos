"""Tests for the dynamic per-stack Compose sensors (sourced from /docker/mos/compose/stacks)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import CONF_ENABLE_COMPOSE_STATS, DOMAIN, MOSDeviceKind
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from typing import Any
    from unittest.mock import AsyncMock

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


async def test_counters_survive_a_stack_having_no_group(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The engine answers both counters from the member containers, so the group is not needed for them."""
    running = hass.states.get("sensor.sirius_compose_orphan_running_containers")
    assert running is not None
    assert running.state == "0"

    total = hass.states.get("sensor.sirius_compose_orphan_containers")
    assert total is not None
    assert total.state == "1"


async def test_state_sensor_lists_the_images_in_use(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The stack list reports no images at all; they come from the member containers."""
    state = hass.states.get("sensor.sirius_compose_hatest_state")
    assert state is not None
    assert state.attributes["images"] == ["busybox:latest", "nginx:alpine"]


async def test_the_server_hosted_icon_wins_over_the_stacks_cdn_url(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
) -> None:
    """Same picture either way, but the local mirror also loads on a browser with no internet access."""
    mock_client.async_static_asset_exists.return_value = True
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.sirius_compose_hatest_state")
    assert state is not None
    assert state.attributes["entity_picture"] == "http://10.0.1.30:80/docker_icons/compose/hatest.png"


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


async def test_stats_sensors_are_absent_unless_the_option_is_on(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """The option is off by default, so no stats sensor exists and no service is measured."""
    assert hass.states.get("sensor.sirius_compose_hatest_cpu_usage") is None
    assert hass.states.get("sensor.sirius_compose_hatest_memory_usage") is None
    mock_client.async_get_docker_container_stats.assert_not_awaited()


async def test_stats_sensors_sum_the_running_services(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A stack costs what its services cost together, so the figures are their sum.

    The refreshes are explicit because the very first poll runs before any entity
    exists: with no context registered yet, nothing is measured. The poll after
    that measures the services and establishes their CPU baseline, and the one
    after that is the first to derive a percentage - see
    ``_async_add_compose_stats`` and ``DockerStatsCollector``.
    """
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_COMPOSE_STATS: True})
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_compose_hatest_cpu_usage").state == STATE_UNKNOWN

    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    # Both services answer with the same payload: 64 MiB each.
    assert hass.states.get("sensor.sirius_compose_hatest_memory_usage").state == "128.0"
    assert hass.states.get("sensor.sirius_compose_hatest_cpu_usage").state == STATE_UNKNOWN

    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    # 25% of two CPUs each.
    assert hass.states.get("sensor.sirius_compose_hatest_cpu_usage").state == "50.0"


async def test_a_stopped_stack_reports_no_usage(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Its one service is down, so there is nothing to measure and nothing to report."""
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_COMPOSE_STATS: True})
    await hass.async_block_till_done()
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_compose_orphan_cpu_usage").state == STATE_UNKNOWN
    measured = {call.args[0] for call in mock_client.async_get_docker_container_stats.await_args_list}
    assert measured == {"compose_hatest-alpha-1", "compose_hatest-beta-1"}


async def test_disabling_a_stacks_stats_sensors_stops_measuring_it(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A request per service is only worth paying while something displays the result."""
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_COMPOSE_STATS: True})
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    for key in ("cpu_usage", "memory_usage"):
        registry.async_update_entity(
            f"sensor.sirius_compose_hatest_{key}",
            disabled_by=er.RegistryEntryDisabler.USER,
        )
    await hass.async_block_till_done()

    mock_client.async_get_docker_container_stats.reset_mock()
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    mock_client.async_get_docker_container_stats.assert_not_awaited()


async def test_stack_stats_come_from_the_stack_list_when_mos_reports_them(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_compose_stacks: list[dict[str, Any]],
) -> None:
    """A stack carrying ``performance`` costs no per-service request.

    MOS sums the stack itself, so neither the member list nor the engine list is
    needed to arrive at the figure.
    """
    mock_client.async_get_compose_stacks.return_value = [
        {**stack, "performance": {"cpu": {"usage": 4.5, "unit": "%"}, "memory": {"bytes": 268_435_456}}}
        if stack["name"] == "hatest"
        else stack
        for stack in mock_compose_stacks
    ]
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_COMPOSE_STATS: True})
    await hass.async_block_till_done()
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sirius_compose_hatest_cpu_usage").state == "4.5"
    # Reported in bytes, displayed in mebibytes: 268435456 B is 256 MiB.
    assert hass.states.get("sensor.sirius_compose_hatest_memory_usage").state == "256.0"
    mock_client.async_get_docker_container_stats.assert_not_awaited()


async def test_a_stack_without_performance_still_sums_its_members(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_compose_stacks: list[dict[str, Any]],
) -> None:
    """A server that reports no stack figure falls back to measuring each running service."""
    mock_client.async_get_compose_stacks.return_value = [
        {**stack, "performance": None} for stack in mock_compose_stacks
    ]
    hass.config_entries.async_update_entry(setup_integration, options={CONF_ENABLE_COMPOSE_STATS: True})
    await hass.async_block_till_done()
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    measured = {call.args[0] for call in mock_client.async_get_docker_container_stats.await_args_list}
    assert measured == {"compose_hatest-alpha-1", "compose_hatest-beta-1"}
