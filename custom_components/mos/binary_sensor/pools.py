"""Storage pool binary sensors for mos, sourced from the ``/pools`` endpoint.

Pools are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/pools.py for the matching
numeric sensors, on the same main server device).

The maintenance-operation sensors (scrub/balance/parity) are conditional:
which one(s) a pool reports depends on its filesystem type (BTRFS pools
report scrub/balance, XFS/RAID pools report parity) - unavailable ones are
simply not created for that pool.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_pool(coordinator: MOSDataUpdateCoordinator, pool_id: str) -> dict[str, Any] | None:
    """Look up the current payload for a pool by id."""
    pools: list[dict[str, Any]] = coordinator.data.get("pools") or []
    return next((pool for pool in pools if str(pool.get("id")) == pool_id), None)


@dataclass(frozen=True, kw_only=True)
class MOSPoolBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS pool binary sensor, including how to derive its value from a pool payload."""

    presence_key: str | None
    """Key that must exist in ``pool.status`` for this entity to be created. None = always created."""
    value_fn: Callable[[dict[str, Any]], bool | None]


ENTITY_DESCRIPTIONS: tuple[MOSPoolBinarySensorEntityDescription, ...] = (
    MOSPoolBinarySensorEntityDescription(
        key="problem",
        translation_key="pool_problem",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        presence_key=None,
        value_fn=lambda pool: (pool.get("status") or {}).get("health") not in (None, "healthy"),
    ),
    MOSPoolBinarySensorEntityDescription(
        key="scrub_running",
        translation_key="pool_scrub_running",
        icon="mdi:refresh",
        presence_key="scrub_operation",
        value_fn=lambda pool: (pool.get("status") or {}).get("scrub_operation"),
    ),
    MOSPoolBinarySensorEntityDescription(
        key="balance_running",
        translation_key="pool_balance_running",
        icon="mdi:refresh",
        presence_key="balance_operation",
        value_fn=lambda pool: (pool.get("status") or {}).get("balance_operation"),
    ),
    MOSPoolBinarySensorEntityDescription(
        key="parity_running",
        translation_key="pool_parity_running",
        icon="mdi:refresh",
        presence_key="parity_operation",
        value_fn=lambda pool: (pool.get("status") or {}).get("parity_operation"),
    ),
)


class MOSPoolBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a single storage pool, backed by a value function."""

    entity_description: MOSPoolBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSPoolBinarySensorEntityDescription,
        pool_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the pool binary sensor."""
        self._pool_id = pool_id
        pool = _find_pool(coordinator, pool_id) or {}
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_pool_{pool_id}_{entity_description.key}",
            translation_placeholders={"pool_name": pool.get("name") or pool_id},
        )

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current pool payload."""
        if not self.coordinator.last_update_success:
            return None
        pool = _find_pool(self.coordinator, self._pool_id)
        if pool is None:
            return None
        return self.entity_description.value_fn(pool)


def build_pool_binary_sensors(coordinator: MOSDataUpdateCoordinator, pool_id: str) -> list[MOSPoolBinarySensor]:
    """Build the binary sensor entities that apply to this pool (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    pool = _find_pool(coordinator, pool_id) or {}
    status = pool.get("status") or {}
    descriptions = [
        description
        for description in ENTITY_DESCRIPTIONS
        if description.presence_key is None or description.presence_key in status
    ]
    return [MOSPoolBinarySensor(coordinator, description, pool_id, entry_id) for description in descriptions]
