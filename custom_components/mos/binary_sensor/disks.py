"""Physical disk binary sensors for mos, sourced from the ``/disks`` endpoint.

Disks are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/disks.py for the matching
numeric sensors, on the same per-disk device).
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


def _find_disk(coordinator: MOSDataUpdateCoordinator, serial: str) -> dict[str, Any] | None:
    """Look up the current payload for a disk by serial."""
    disks: list[dict[str, Any]] = coordinator.data.get("disks") or []
    return next((disk for disk in disks if disk.get("serial") == serial), None)


@dataclass(frozen=True, kw_only=True)
class MOSDiskBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS disk binary sensor, including how to derive its value from a disk payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]


ENTITY_DESCRIPTIONS: tuple[MOSDiskBinarySensorEntityDescription, ...] = (
    MOSDiskBinarySensorEntityDescription(
        key="smart_warning",
        translation_key="disk_smart_warning",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda disk: disk.get("smartWarning"),
    ),
    MOSDiskBinarySensorEntityDescription(
        key="preclear_running",
        translation_key="disk_preclear_running",
        # Icon is state-dependent (icons.json), not set here: mdi:progress-clock
        # while running, a neutral icon once idle.
        value_fn=lambda disk: disk.get("preclearRunning"),
    ),
)


class MOSDiskBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a single physical disk, backed by a value function."""

    entity_description: MOSDiskBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSDiskBinarySensorEntityDescription,
        serial: str,
        entry_id: str,
    ) -> None:
        """Initialize the disk binary sensor."""
        self._serial = serial
        disk = _find_disk(coordinator, serial) or {}
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_disk_{serial}_{entity_description.key}",
            container_device=(f"disk_{serial}", f"Disk {disk.get('name') or serial}"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current disk payload."""
        if not self.coordinator.last_update_success:
            return None
        disk = _find_disk(self.coordinator, self._serial)
        if disk is None:
            return None
        return self.entity_description.value_fn(disk)


def build_disk_binary_sensors(coordinator: MOSDataUpdateCoordinator, serial: str) -> list[MOSDiskBinarySensor]:
    """Build the binary sensor entities for a single disk (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSDiskBinarySensor(coordinator, description, serial, entry_id) for description in ENTITY_DESCRIPTIONS]
