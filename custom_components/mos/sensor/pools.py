"""Storage pool sensors for mos, sourced from the ``/pools`` endpoint.

Pools are a dynamic list (they can be created/deleted at runtime), so their
entities are added/removed via ``async_setup_dynamic_entities`` rather than a
static ENTITY_DESCRIPTIONS tuple. They live on the main server device
alongside the system sensors; the pool's own name is folded into the entity
name via ``translation_placeholders`` so entity_ids stay unique per pool
(e.g. ``sensor.mos_server_test1_usage``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_pool(coordinator: MOSDataUpdateCoordinator, pool_id: str) -> dict[str, Any] | None:
    """Look up the current payload for a pool by id."""
    pools: list[dict[str, Any]] = coordinator.data.get("pools") or []
    return next((pool for pool in pools if str(pool.get("id")) == pool_id), None)


@dataclass(frozen=True, kw_only=True)
class MOSPoolSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS pool sensor, including how to derive its value from a pool payload."""

    value_fn: Callable[[dict[str, Any]], StateType]


ENTITY_DESCRIPTIONS: tuple[MOSPoolSensorEntityDescription, ...] = (
    MOSPoolSensorEntityDescription(
        key="usage",
        translation_key="pool_usage",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda pool: (pool.get("status") or {}).get("usagePercent"),
    ),
    MOSPoolSensorEntityDescription(
        key="free_space",
        translation_key="pool_free_space",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda pool: (pool.get("status") or {}).get("freeSpace"),
    ),
)


class MOSPoolSensor(SensorEntity, MOSEntity):
    """Sensor for a single storage pool, backed by a value function."""

    entity_description: MOSPoolSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSPoolSensorEntityDescription,
        pool_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the pool sensor."""
        self._pool_id = pool_id
        pool = _find_pool(coordinator, pool_id) or {}
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_pool_{pool_id}_{entity_description.key}",
            translation_placeholders={"pool_name": pool.get("name") or pool_id},
        )

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current pool payload."""
        if not self.coordinator.last_update_success:
            return None
        pool = _find_pool(self.coordinator, self._pool_id)
        if pool is None:
            return None
        return self.entity_description.value_fn(pool)


def build_pool_sensors(coordinator: MOSDataUpdateCoordinator, pool_id: str) -> list[MOSPoolSensor]:
    """Build all sensor entities for a single pool (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSPoolSensor(coordinator, description, pool_id, entry_id) for description in ENTITY_DESCRIPTIONS]
