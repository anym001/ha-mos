"""Live system health sensors for mos, sourced from the ``/system/load`` endpoint.

Unlike the static sensors in ``system.py`` (which describe the installed
version/OS and barely change), these reflect the current CPU/memory/swap
load at poll time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTemperature
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class MOSSystemHealthSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS system health sensor, including how to derive its value."""

    value_fn: Callable[[dict[str, Any]], StateType]


def _memory_breakdown(consumer: str) -> Callable[[dict[str, Any]], StateType]:
    """Return a value function reading one consumer's share from ``memory.breakdown``.

    MOS reports each consumer both in bytes and as a rounded percentage; only
    the byte figure is exposed, since the percentage is trivially derived from
    it and ``memory_total`` in a template.
    """

    def value_fn(system_load: dict[str, Any]) -> StateType:
        breakdown = (system_load.get("memory") or {}).get("breakdown") or {}
        return (breakdown.get(consumer) or {}).get("bytes")

    return value_fn


def _cpu_temperature_average(system_load: dict[str, Any]) -> StateType:
    """Return the mean temperature across the physical CPU cores.

    This is deliberately not the same reading as ``temperature.main``: that one
    is the package/die sensor and runs a few degrees above the core mean (35 vs
    33.0 on a 13th-gen i5), so neither value can be derived from the other.

    ``temperature.cores`` is a bare list covering only the physical cores -
    hyper-threaded siblings report no temperature of their own and are already
    absent here.
    """
    cores = (system_load.get("temperature") or {}).get("cores") or []
    readings = [core for core in cores if isinstance(core, (int, float))]
    if not readings:
        return None
    return round(sum(readings) / len(readings), 1)


ENTITY_DESCRIPTIONS: tuple[MOSSystemHealthSensorEntityDescription, ...] = (
    MOSSystemHealthSensorEntityDescription(
        key="cpu_load",
        translation_key="cpu_load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("cpu") or {}).get("load"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="cpu_temperature",
        translation_key="cpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("temperature") or {}).get("main"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="cpu_temperature_max",
        translation_key="cpu_temperature_max",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("temperature") or {}).get("max"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="cpu_temperature_average",
        translation_key="cpu_temperature_average",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_cpu_temperature_average,
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_usage",
        translation_key="memory_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: ((system_load.get("memory") or {}).get("percentage") or {}).get("actuallyUsed"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_used",
        translation_key="memory_used",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("memory") or {}).get("used"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_total",
        translation_key="memory_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("memory") or {}).get("total"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_free",
        translation_key="memory_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("memory") or {}).get("free"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_installed",
        translation_key="memory_installed",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("memory") or {}).get("installed"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_reserved",
        translation_key="memory_reserved",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("memory") or {}).get("reserved"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_cache",
        translation_key="memory_cache",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: ((system_load.get("memory") or {}).get("dirty") or {}).get("dirtyCaches"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_docker",
        translation_key="memory_docker",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_memory_breakdown("docker"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_system",
        translation_key="memory_system",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_memory_breakdown("system"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_lxc",
        translation_key="memory_lxc",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_memory_breakdown("lxc"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_vms",
        translation_key="memory_vms",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_memory_breakdown("vms"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="memory_zram",
        translation_key="memory_zram",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_memory_breakdown("zram"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="swap_usage",
        translation_key="swap_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("swap") or {}).get("percentage"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="swap_used",
        translation_key="swap_used",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("swap") or {}).get("used"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="swap_total",
        translation_key="swap_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("swap") or {}).get("total"),
    ),
    MOSSystemHealthSensorEntityDescription(
        key="swap_free",
        translation_key="swap_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("swap") or {}).get("available"),
    ),
)


class MOSSystemHealthSensor(SensorEntity, MOSEntity):
    """System health sensor backed by a value function over the system_load payload."""

    entity_description: MOSSystemHealthSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSSystemHealthSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current system_load data."""
        if not self.coordinator.last_update_success:
            return None
        system_load: dict[str, Any] = (self.coordinator.data or {}).get("system_load", {})
        return self.entity_description.value_fn(system_load)
