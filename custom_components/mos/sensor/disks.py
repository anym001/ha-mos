"""Physical disk sensors for mos, sourced from the ``/disks`` endpoint.

Disks are a dynamic list (they can be plugged/unplugged at runtime), so their
entities are added/removed via ``async_setup_dynamic_entities`` rather than a
static ENTITY_DESCRIPTIONS tuple. Each disk gets its own device (linked back
to the main server device via ``via_device_id``), same as LXC/Docker/VM items
(e.g. ``sensor.mos_server_disk_vda_power_status``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTemperature
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


# The ATA power modes a disk can report. Spelled out as an enum so the state
# reads as "Active"/"Standby" in the user's language instead of the raw value,
# which is only possible for a sensor that declares its options.
#
# ``active`` and ``standby`` are the two MOS is known to send; ``idle`` and
# ``sleeping`` are the remaining standard modes, listed so a disk in one of them
# still gets a reading. Options a device never reports cost nothing, whereas a
# missing one is an error.
DISK_POWER_STATES = ["active", "idle", "standby", "sleeping"]


def _power_status(disk: dict[str, Any]) -> StateType:
    """
    Return the disk's power mode, or None if it is not one this sensor names.

    An enum sensor rejects any state outside its options, so a mode MOS reports
    that ``DISK_POWER_STATES`` does not cover would otherwise raise rather than
    read. Reporting it as unknown keeps the entity intact and is honest about
    what happened - the sensor genuinely has no reading it can express.
    """
    status = disk.get("powerStatus")

    return status if status in DISK_POWER_STATES else None


# The space figures a partition reports, which MOS documents as the same shape a
# pool's members carry. Unlike temperature they do not depend on
# ``performance=true``, so a spun-down disk still reports them.
_SPACE_FIELDS = ("totalSpace", "usedSpace", "freeSpace")


def _partition_space(partition: Any) -> dict[str, int] | None:
    """
    Read one partition's space figures, if it has a complete set of them.

    Returns:
        The figures, or ``None`` for a partition that is unmounted or reports
        only some of them - counting a partial set would total up to a quietly
        wrong reading.

    """
    if not isinstance(partition, dict):
        return None
    status = partition.get("status") or {}
    if not status.get("mounted"):
        return None
    space: dict[str, int] = {}
    for field in _SPACE_FIELDS:
        value = status.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            return None
        space[field] = value
    return space


def _space(disk: dict[str, Any]) -> dict[str, int] | None:
    """
    Total the space reported by the disk's mounted partitions.

    Summed rather than read from the first partition, because a disk split
    across several filesystems holds the sum of them.

    Returns:
        The totals, or ``None`` when no partition contributed any.

    """
    totals: dict[str, int] = dict.fromkeys(_SPACE_FIELDS, 0)
    measured = False
    for partition in disk.get("partitions") or []:
        space = _partition_space(partition)
        if space is None:
            continue
        measured = True
        for field, value in space.items():
            totals[field] += value
    return totals if measured else None


def _usage(disk: dict[str, Any]) -> StateType:
    """
    Derive how full the disk is, across all of its mounted partitions.

    Computed here rather than read from the payload: ``/disks`` reports the three
    byte figures but no percentage, unlike a pool's members.

    Returns:
        The percentage, or ``None`` when nothing was measured.

    """
    space = _space(disk)
    if space is None or not space["totalSpace"]:
        return None
    return round(space["usedSpace"] / space["totalSpace"] * 100, 1)


def _space_field(field: str) -> Callable[[dict[str, Any]], StateType]:
    """
    Build the value function reading one summed space field.

    Returns:
        A value function for ``field``.

    """
    return lambda disk: (_space(disk) or {}).get(field)


ENTITY_DESCRIPTIONS: tuple[MOSDiskSensorEntityDescription, ...] = (
    MOSDiskSensorEntityDescription(
        key="power_status",
        translation_key="disk_power_status",
        device_class=SensorDeviceClass.ENUM,
        options=DISK_POWER_STATES,
        value_fn=_power_status,
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
        value_fn=lambda disk: disk.get("model"),
    ),
    MOSDiskSensorEntityDescription(
        key="type",
        translation_key="disk_type",
        value_fn=lambda disk: disk.get("type"),
    ),
    MOSDiskSensorEntityDescription(
        key="size",
        translation_key="disk_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda disk: disk.get("size"),
    ),
    MOSDiskSensorEntityDescription(
        key="usage",
        translation_key="disk_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_usage,
    ),
    MOSDiskSensorEntityDescription(
        key="free_space",
        translation_key="disk_free_space",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_space_field("freeSpace"),
    ),
    MOSDiskSensorEntityDescription(
        key="total_space",
        translation_key="disk_total_space",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_space_field("totalSpace"),
    ),
    MOSDiskSensorEntityDescription(
        key="used_space",
        translation_key="disk_used_space",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_space_field("usedSpace"),
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
            device_kind=MOSDeviceKind.DISK,
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


def build_disk_sensors(coordinator: MOSDataUpdateCoordinator, serial: str) -> list[MOSDiskSensor]:
    """Build all sensor entities for a single disk (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSDiskSensor(coordinator, description, serial, entry_id) for description in ENTITY_DESCRIPTIONS]
