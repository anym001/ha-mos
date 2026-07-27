"""
Dynamic entity lifecycle helper for mos.

Some MOS resources (disks, storage pools) are lists of items that can appear or
disappear at runtime - a disk gets plugged in, a pool gets deleted, and so on.
This module provides a single, reusable way for a platform (sensor,
binary_sensor, ...) to keep its entities in sync with such a list, including
removing the entity when an item disappears. All such entities live on the
main server device (see entity/base.py's ``translation_placeholders``), so
there is no per-item device to clean up here.

Used by sensor/disks.py, sensor/pools.py, binary_sensor/disks.py and
binary_sensor/pools.py to avoid duplicating the add/remove diffing logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from custom_components.mos.coordinator import MOSDataUpdateCoordinator
    from custom_components.mos.data import MOSConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import Entity
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


def async_setup_dynamic_entities(
    hass: HomeAssistant,
    entry: MOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
    *,
    data_key: str,
    id_fn: Callable[[dict[str, Any]], str],
    entity_factory: Callable[[MOSDataUpdateCoordinator, str], Sequence[Entity]],
) -> None:
    """
    Keep entities in sync with a dynamic list of items in coordinator data.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry these entities belong to.
        async_add_entities: Callback to register newly created entities.
        data_key: The key in ``coordinator.data`` holding the list of items
            (e.g. ``"disks"`` or ``"pools"``).
        id_fn: Extracts a stable id from a raw item (e.g. a disk's ``serial``
            or a pool's ``id``).
        entity_factory: Builds all entities for a given item id (an item can
            back more than one entity, e.g. a disk's power-status sensor and
            its SMART binary_sensor).

    """
    coordinator = entry.runtime_data.coordinator
    known: dict[str, Sequence[Entity]] = {}

    @callback
    def _sync() -> None:
        items = coordinator.data.get(data_key) or []
        current_ids = {id_fn(item) for item in items}

        new_ids = current_ids - known.keys()
        if new_ids:
            new_entities: list[Entity] = []
            for item_id in new_ids:
                entities = entity_factory(coordinator, item_id)
                known[item_id] = entities
                new_entities.extend(entities)
            async_add_entities(new_entities)

        removed_ids = known.keys() - current_ids
        for item_id in removed_ids:
            hass.async_create_task(_async_remove_entities(hass, known.pop(item_id)))

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


async def _async_remove_entities(hass: HomeAssistant, entities: Sequence[Entity]) -> None:
    """Remove entities that no longer have a backing item, including their registry entry.

    ``async_remove`` alone only clears the entity's state; without also removing
    the entity registry entry, a disk/pool that disappears for good would leave
    a permanently orphaned, unavailable entity behind.
    """
    registry = er.async_get(hass)
    for entity in entities:
        await entity.async_remove(force_remove=True)
        if entity.entity_id and registry.async_get(entity.entity_id):
            registry.async_remove(entity.entity_id)
