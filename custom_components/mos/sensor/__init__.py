"""Sensor platform for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import (
    CONF_ENABLE_DISKS,
    CONF_ENABLE_POOLS,
    CONF_ENABLE_SYSTEM_HEALTH,
    DEFAULT_ENABLE_DISKS,
    DEFAULT_ENABLE_POOLS,
    DEFAULT_ENABLE_SYSTEM_HEALTH,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.mos.entity_utils import async_setup_dynamic_entities

from .disks import build_disk_sensors
from .pools import build_pool_sensors
from .system import ENTITY_DESCRIPTIONS as SYSTEM_DESCRIPTIONS, MOSSystemSensor
from .system_health import ENTITY_DESCRIPTIONS as SYSTEM_HEALTH_DESCRIPTIONS, MOSSystemHealthSensor

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        MOSSystemSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in SYSTEM_DESCRIPTIONS
    )

    if entry.options.get(CONF_ENABLE_SYSTEM_HEALTH, DEFAULT_ENABLE_SYSTEM_HEALTH):
        async_add_entities(
            MOSSystemHealthSensor(
                coordinator=entry.runtime_data.coordinator,
                entity_description=entity_description,
            )
            for entity_description in SYSTEM_HEALTH_DESCRIPTIONS
        )

    if entry.options.get(CONF_ENABLE_DISKS, DEFAULT_ENABLE_DISKS):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="disks",
            id_fn=lambda disk: disk["serial"],
            entity_factory=build_disk_sensors,
        )
    if entry.options.get(CONF_ENABLE_POOLS, DEFAULT_ENABLE_POOLS):
        async_setup_dynamic_entities(
            hass,
            entry,
            async_add_entities,
            data_key="pools",
            id_fn=lambda pool: str(pool["id"]),
            entity_factory=build_pool_sensors,
        )
