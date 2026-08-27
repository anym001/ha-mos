"""Switch platform for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import (
    CONF_ENABLE_COMPOSE,
    CONF_ENABLE_DOCKER,
    CONF_ENABLE_LXC,
    CONF_ENABLE_VM,
    DEFAULT_ENABLE_COMPOSE,
    DEFAULT_ENABLE_DOCKER,
    DEFAULT_ENABLE_LXC,
    DEFAULT_ENABLE_VM,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.mos.entity_utils import async_setup_dynamic_entities

from .compose import build_compose_stack_switches
from .docker import build_docker_container_switches
from .lxc import build_lxc_container_switches
from .vm import build_vm_machine_switches

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    if entry.options.get(CONF_ENABLE_LXC, DEFAULT_ENABLE_LXC):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="lxc_containers",
            id_fn=lambda container: container["name"],
            entity_factory=build_lxc_container_switches,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_lxc_{name}"),
        )
    if entry.options.get(CONF_ENABLE_DOCKER, DEFAULT_ENABLE_DOCKER):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="docker_containers",
            id_fn=lambda container: container["name"],
            entity_factory=build_docker_container_switches,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_docker_{name}"),
        )
    if entry.options.get(CONF_ENABLE_COMPOSE, DEFAULT_ENABLE_COMPOSE):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="compose_stacks",
            id_fn=lambda stack: stack["name"],
            entity_factory=build_compose_stack_switches,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_compose_{name}"),
        )
    if entry.options.get(CONF_ENABLE_VM, DEFAULT_ENABLE_VM):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="vm_machines",
            id_fn=lambda machine: machine["name"],
            entity_factory=build_vm_machine_switches,
            device_identifiers_fn=lambda name: (entry.domain, f"{entry.entry_id}_vm_{name}"),
        )
