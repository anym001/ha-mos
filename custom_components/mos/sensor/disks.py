"""Physical disk sensors for mos, sourced from the ``/disks`` endpoint.

Disks are a dynamic list (they can be plugged/unplugged at runtime), so their
entities are added/removed via ``async_setup_dynamic_entities`` rather than a
static ENTITY_DESCRIPTIONS tuple. Each disk gets its own device (linked back
to the main server device via ``via_device``), same as LXC/Docker/VM items
(e.g. ``sensor.mos_server_disk_vda_power_status``).

Note: ``temperatureStatus`` was ``null`` on every disk of the test system used
to build this (a VM with virtual disks), so its real shape (a numeric reading
vs. a status string) is unverified. The sensor below is deliberately generic
(no fixed device_class/unit) until that's confirmed on real hardware. The
separate ``temperature`` field is the actual numeric Celsius reading.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfInformation, UnitOfTemperature
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_disk(coordinator: MOSDataUpdateCoordinator, serial: str) -> dict[str, Any] | None:
    """Look up the current payload for a disk by serial."""
    disks: list[dict[str, Any]] = coordinator.data.get("disks") or []
    return next((disk for disk in disks if disk.get("serial") == serial), None)


@dataclass(frozen=True, kw_only=True)
class MOSDiskSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS disk sensor, including how to derive its value from a disk payload."""

    value_fn: Callable[[dict[str, Any]], StateType]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


ENTITY_DESCRIPTIONS: tuple[MOSDiskSensorEntityDescription, ...] = (
    MOSDiskSensorEntityDescription(
        key="power_status",
        translation_key="disk_power_status",
        icon="mdi:power",
        value_fn=lambda disk: disk.get("powerStatus"),
    ),
    MOSDiskSensorEntityDescription(
        key="temperature_status",
        translation_key="disk_temperature_status",
        icon="mdi:thermometer",
        value_fn=lambda disk: disk.get("temperatureStatus"),
    ),
    MOSDiskSensorEntityDescription(
        key="temperature",
        translation_key="disk_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda disk: disk.get("temperature"),
    ),
    MOSDiskSensorEntityDescription(
        key="model",
        translation_key="disk_model",
        icon="mdi:harddisk",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda disk: disk.get("model"),
        attributes_fn=lambda disk: {"type": disk.get("type")},
    ),
    MOSDiskSensorEntityDescription(
        key="size",
        translation_key="disk_size",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda disk: disk.get("size"),
    ),
)


class MOSDiskSensor(SensorEntity, MOSEntity):
    """Sensor for a single physical disk, backed by a value function."""

    entity_description: MOSDiskSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSDiskSensorEntityDescription,
        serial: str,
        entry_id: str,
    ) -> None:
        """Initialize the disk sensor."""
        self._serial = serial
        disk = _find_disk(coordinator, serial) or {}
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_disk_{serial}_{entity_description.key}",
            container_device=(f"disk_{serial}", f"Disk {disk.get('name') or serial}"),
        )

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current disk payload."""
        if not self.coordinator.last_update_success:
            return None
        disk = _find_disk(self.coordinator, self._serial)
        if disk is None:
            return None
        return self.entity_description.value_fn(disk)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra descriptive attributes, if the entity description defines any."""
        if self.entity_description.attributes_fn is None or not self.coordinator.last_update_success:
            return None
        disk = _find_disk(self.coordinator, self._serial)
        if disk is None:
            return None
        return self.entity_description.attributes_fn(disk)


def build_disk_sensors(coordinator: MOSDataUpdateCoordinator, serial: str) -> list[MOSDiskSensor]:
    """Build all sensor entities for a single disk (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSDiskSensor(coordinator, description, serial, entry_id) for description in ENTITY_DESCRIPTIONS]
