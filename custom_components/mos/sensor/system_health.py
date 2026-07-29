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


ENTITY_DESCRIPTIONS: tuple[MOSSystemHealthSensorEntityDescription, ...] = (
    MOSSystemHealthSensorEntityDescription(
        key="cpu_load",
        translation_key="cpu_load",
        icon="mdi:cpu-64-bit",
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
        key="memory_usage",
        translation_key="memory_usage",
        icon="mdi:memory",
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
        key="swap_usage",
        translation_key="swap_usage",
        icon="mdi:swap-horizontal",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda system_load: (system_load.get("swap") or {}).get("percentage"),
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
