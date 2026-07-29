"""
Dynamic entity lifecycle helper for mos.

Some MOS resources (disks, storage pools, LXC/Docker containers) are lists of
items that can appear or disappear at runtime - a disk gets plugged in, a
container gets removed, and so on. This module provides a single, reusable
way for a platform (sensor, binary_sensor, ...) to keep its entities in sync
with such a list, including removing the entity when an item disappears.

Each item gets its own device (``container_device`` in entity/base.py),
linked back to the main server device; when an item disappears, its
now-entity-less device is removed too, via the optional
``device_identifiers_fn``.

Used by sensor/disks.py, sensor/pools.py, sensor/lxc.py, sensor/docker.py,
their binary_sensor counterparts, and switch/lxc.py to avoid duplicating the
add/remove diffing logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from custom_components.mos.coordinator import MOSDataUpdateCoordinator
    from custom_components.mos.data import MOSConfigEntry
    from custom_components.mos.entity import MOSEntity
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
    entity_factory: Callable[[MOSDataUpdateCoordinator, str], Sequence[MOSEntity]],
    device_identifiers_fn: Callable[[str], tuple[str, str]] | None = None,
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
        device_identifiers_fn: For items with their own device (containers):
            given an item id, returns its device registry identifiers
            (``(domain, unique_key)``). When an item disappears, if this
            leaves its device with zero entities (across all platforms), the
            device is removed too. ``None`` for items that share the main
            server device (disks, pools).

    """
    coordinator = entry.runtime_data.coordinator
    known: dict[str, Sequence[MOSEntity]] = {}

    @callback
    def _sync() -> None:
        items = coordinator.data.get(data_key) or []
        current_ids = {id_fn(item) for item in items}

        new_ids = current_ids - known.keys()
        if new_ids:
            new_entities: list[MOSEntity] = []
            for item_id in new_ids:
                entities = entity_factory(coordinator, item_id)
                for entity in entities:
                    # Tell the entity which resource backs it, so it can report
                    # itself unavailable once that resource's data goes stale.
                    # Unioned rather than assigned: an entity may already declare
                    # further keys of its own (the Docker power switch reads its
                    # running state from a second resource).
                    entity.resource_keys |= {data_key}
                known[item_id] = entities
                new_entities.extend(entities)
            async_add_entities(new_entities)

        removed_ids = known.keys() - current_ids
        for item_id in removed_ids:
            device_identifiers = device_identifiers_fn(item_id) if device_identifiers_fn else None
            hass.async_create_task(_async_remove_entities(hass, known.pop(item_id), device_identifiers))

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


async def _async_remove_entities(
    hass: HomeAssistant,
    entities: Sequence[Entity],
    device_identifiers: tuple[str, str] | None,
) -> None:
    """Remove entities that no longer have a backing item, including their registry entry.

    ``async_remove`` alone only clears the entity's state; without also removing
    the entity registry entry, a disk/pool/container that disappears for good
    would leave a permanently orphaned, unavailable entity behind.

    If ``device_identifiers`` is given, also remove that device once it has no
    entities left. Sensor and binary_sensor entities for the same container
    are torn down independently by their own platform, so this check runs
    once per platform and only succeeds once the last one has cleared its
    entities - no extra coordination needed between platforms.
    """
    registry = er.async_get(hass)
    for entity in entities:
        await entity.async_remove(force_remove=True)
        if entity.entity_id and registry.async_get(entity.entity_id):
            registry.async_remove(entity.entity_id)

    if device_identifiers is not None:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(identifiers={device_identifiers})
        if device is not None and not er.async_entries_for_device(registry, device.id, include_disabled_entities=True):
            device_registry.async_remove_device(device.id)
