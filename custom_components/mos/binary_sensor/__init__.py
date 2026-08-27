"""Binary sensor platform for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import (
    CONF_ENABLE_COMPOSE,
    CONF_ENABLE_DISKS,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_NUT,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SERVICES,
    CONF_ENABLE_VM,
    DEFAULT_ENABLE_COMPOSE,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_NUT,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SERVICES,
    DEFAULT_ENABLE_VM,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.mos.entity_utils import async_setup_dynamic_entities, async_setup_ups_entities

from .compose import build_compose_stack_binary_sensors
from .disks import build_disk_binary_sensors
from .docker import build_docker_container_binary_sensors
from .lxc import build_lxc_container_binary_sensors
from .nut import build_nut_binary_sensors
from .pools import build_pool_binary_sensors
from .services import ENTITY_DESCRIPTIONS as SERVICE_DESCRIPTIONS, MOSServiceBinarySensor
from .vm import build_vm_machine_binary_sensors

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    if entry.options.get(CONF_ENABLE_SERVICES, DEFAULT_ENABLE_SERVICES):
        async_add_entities(
            MOSServiceBinarySensor(
                coordinator=entry.runtime_data.coordinator,
                entity_description=entity_description,
            )
            for entity_description in SERVICE_DESCRIPTIONS
        )
    if entry.options.get(CONF_ENABLE_NUT, DEFAULT_ENABLE_NUT):
        async_setup_ups_entities(entry, async_add_entities, build_nut_binary_sensors)

    if entry.options.get(CONF_ENABLE_DISKS, DEFAULT_ENABLE_DISKS):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="disks",
            id_fn=lambda disk: disk["serial"],
            entity_factory=build_disk_binary_sensors,
            device_identifiers_fn=lambda serial: (entry.domain, f"{entry.entry_id}_disk_{serial}"),
        )
    if entry.options.get(CONF_ENABLE_POOLS, DEFAULT_ENABLE_POOLS):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="pools",
            id_fn=lambda pool: str(pool["id"]),
            entity_factory=build_pool_binary_sensors,
            device_identifiers_fn=lambda pool_id: (entry.domain, f"{entry.entry_id}_pool_{pool_id}"),
        )
    if entry.options.get(CONF_ENABLE_LXC, DEFAULT_ENABLE_LXC):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="lxc_containers",
            id_fn=lambda container: container["name"],
            entity_factory=build_lxc_container_binary_sensors,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_lxc_{name}"),
        )
    if entry.options.get(CONF_ENABLE_DOCKER, DEFAULT_ENABLE_DOCKER):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="docker_containers",
            id_fn=lambda container: container["name"],
            entity_factory=build_docker_container_binary_sensors,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_docker_{name}"),
        )
    if entry.options.get(CONF_ENABLE_COMPOSE, DEFAULT_ENABLE_COMPOSE):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="compose_stacks",
            id_fn=lambda stack: stack["name"],
            entity_factory=build_compose_stack_binary_sensors,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_compose_{name}"),
        )
    if entry.options.get(CONF_ENABLE_VM, DEFAULT_ENABLE_VM):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="vm_machines",
            id_fn=lambda machine: machine["name"],
            entity_factory=build_vm_machine_binary_sensors,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_vm_{name}"),
        )
