"""Switch platform for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import CONF_ENABLE_LXC, DEFAULT_ENABLE_LXC, PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.mos.entity_utils import async_setup_dynamic_entities

from .lxc import build_lxc_container_switches

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
