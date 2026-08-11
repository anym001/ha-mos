"""Tests for MOSEntity's device info.

Regression test: the device info used to show the CPU brand as the device
model; it must show the MOS version instead (build as sw_version).
"""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.api import MOSApiClientCommunicationError
from custom_components.mos.const import DOMAIN, RESOURCE_STALE_GRACE_PERIOD, RESOURCE_STALE_MIN_FAILURES
from custom_components.mos.coordinator import MOSDataUpdateCoordinator
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


async def test_device_info_shows_mos_version_not_cpu(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The device model/sw_version come from osinfo.mos, not osinfo.cpu."""
    registry = dr.async_get(hass)
    device = registry.async_get_device_by_identifier((DOMAIN, setup_integration.entry_id), setup_integration.entry_id)

    assert device is not None
    assert device.manufacturer == "MOS"
    assert device.model == "0.5.0-stable"
    assert device.sw_version == "20260705-1111"
    assert device.model != "Intel Xeon E-2288G"


async def test_disks_and_pools_get_their_own_device(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Each disk/pool is a separate device linked back to the server device, same as LXC/Docker/VM items."""
    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, setup_integration.entry_id)

    # 1 server device + 2 disks + 2 pools + 2 LXC containers + 2 Docker containers
    # + 2 VMs + the UPS.
    assert len(devices) == 12
    server_device = registry.async_get_device_by_identifier(
        (DOMAIN, setup_integration.entry_id), setup_integration.entry_id
    )
    assert server_device is not None
    assert server_device.name == "Sirius"
    container_devices = [device for device in devices if device.id != server_device.id]
    assert len(container_devices) == 11
    assert all(device.via_device_id == server_device.id for device in container_devices)


async def _drive_to_stale(
    coordinator: MOSDataUpdateCoordinator,
    advance_clock: Callable[[float], None],
) -> None:
    """Poll until whatever is currently failing has satisfied both halves of the staleness guard."""
    for _ in range(RESOURCE_STALE_MIN_FAILURES):
        advance_clock(RESOURCE_STALE_GRACE_PERIOD.total_seconds())
        await coordinator.async_refresh()


async def test_stale_resource_marks_only_its_own_entities_unavailable(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    advance_clock: Callable[[float], None],
) -> None:
    """A dead endpoint takes down its own entities and nothing else.

    The blast radius is the point: an integration that turned every entity
    unavailable over one broken endpoint would be worse than the frozen values
    it replaces.
    """
    coordinator = setup_integration.runtime_data.coordinator
    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")

    await _drive_to_stale(coordinator, advance_clock)
    await hass.async_block_till_done()

    assert coordinator.stale_resources == frozenset({"vm_machines"})

    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)
    entry_id = setup_integration.entry_id

    # Both VMs in the fixture are backed by vm_machines, so both go with it.
    vm_entity_ids: list[str] = []
    for vm_name in ("Test", "Legacy"):
        vm_device = device_reg.async_get_device_by_identifier((DOMAIN, f"{entry_id}_vm_{vm_name}"), entry_id)
        assert vm_device is not None
        vm_entity_ids += [entity.entity_id for entity in er.async_entries_for_device(entity_reg, vm_device.id)]
    assert vm_entity_ids
    for entity_id in vm_entity_ids:
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNAVAILABLE, f"{entity_id} should be unavailable"

    others = [
        entity.entity_id
        for entity in er.async_entries_for_config_entry(entity_reg, entry_id)
        if entity.entity_id not in vm_entity_ids
    ]
    assert others
    for entity_id in others:
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state != STATE_UNAVAILABLE, f"{entity_id} should have stayed available"


async def test_stale_resource_does_not_remove_entities(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    advance_clock: Callable[[float], None],
) -> None:
    """Unavailable, never deleted - the registry entry, its history and its entity_id survive."""
    coordinator = setup_integration.runtime_data.coordinator
    entity_reg = er.async_get(hass)
    before = {entity.entity_id for entity in er.async_entries_for_config_entry(entity_reg, setup_integration.entry_id)}

    mock_client.async_get_vm_machines.side_effect = MOSApiClientCommunicationError("timeout")
    await _drive_to_stale(coordinator, advance_clock)
    await hass.async_block_till_done()

    after = {entity.entity_id for entity in er.async_entries_for_config_entry(entity_reg, setup_integration.entry_id)}
    assert after == before


async def test_docker_switch_follows_the_engine_proxy_but_its_sensors_do_not(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    advance_clock: Callable[[float], None],
) -> None:
    """The power switch depends on two resources; the Docker binary sensors depend on only one.

    ``docker_engine_containers`` supplies the running state the switch renders,
    so a stale proxy makes that switch's position unverifiable. Update-available
    and autostart come from ``/docker/mos/containers`` alone and stay valid.
    """
    coordinator = setup_integration.runtime_data.coordinator
    mock_client.async_get_docker_engine_containers.side_effect = MOSApiClientCommunicationError("timeout")

    await _drive_to_stale(coordinator, advance_clock)
    await hass.async_block_till_done()

    assert coordinator.stale_resources == frozenset({"docker_engine_containers"})

    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)
    docker_device = device_reg.async_get_device_by_identifier(
        (DOMAIN, f"{setup_integration.entry_id}_docker_PushBits"), setup_integration.entry_id
    )
    assert docker_device is not None

    states = {
        entity.entity_id: hass.states.get(entity.entity_id)
        for entity in er.async_entries_for_device(entity_reg, docker_device.id)
    }
    switches = [entity_id for entity_id in states if entity_id.startswith("switch.")]
    sensors = [entity_id for entity_id in states if not entity_id.startswith("switch.")]
    assert switches
    assert sensors

    for entity_id in switches:
        assert states[entity_id] is not None
        assert states[entity_id].state == STATE_UNAVAILABLE
    for entity_id in sensors:
        assert states[entity_id] is not None
        assert states[entity_id].state != STATE_UNAVAILABLE
