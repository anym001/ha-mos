"""UPS sensors for mos, sourced from the ``/nut/status`` endpoint.

MOS talks to the UPS through Network UPS Tools and hands back a parsed ``data``
block next to the raw NUT variables; only the parsed block is used here, since
the raw variable set differs per driver. The entities are a fixed set on the
main server device rather than a dynamic list: MOS reports at most one UPS, and
it is a fixed part of the server's power supply rather than something that
comes and goes like a disk or a container.

They are created the first time a UPS actually answers, and then stay
(``async_setup_ups_entities``), so a server without a UPS gets no UPS entities
at all. Should the UPS stop answering afterwards - unplugged, driver down - MOS
answers ``reachable: false`` with no ``data``, and the entities report
themselves unavailable rather than a value: the honest reading is "we cannot
tell", not "zero volts". They recover on their own as soon as it answers again.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from custom_components.mos.entity_utils import is_ups_reachable, nut_data, nut_payload
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfFrequency, UnitOfPower, UnitOfTime
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class MOSNutSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS UPS sensor, including how to derive its value from the nut payload."""

    value_fn: Callable[[dict[str, Any]], StateType]


def _battery(field: str) -> Callable[[dict[str, Any]], StateType]:
    """Return a value function reading one field from the ``data.battery`` block."""
    return lambda payload: (nut_data(payload).get("battery") or {}).get(field)


def _line(side: str, field: str) -> Callable[[dict[str, Any]], StateType]:
    """Return a value function reading one field from the ``data.input``/``data.output`` block."""
    return lambda payload: (nut_data(payload).get(side) or {}).get(field)


ENTITY_DESCRIPTIONS: tuple[MOSNutSensorEntityDescription, ...] = (
    MOSNutSensorEntityDescription(
        key="ups_status",
        translation_key="ups_status",
        icon="mdi:power-plug",
        # Kept as the raw NUT flag string ("OL", "OB LB", "OL CHRG", ...). The
        # individual flags are exposed as binary sensors; this one is for the
        # combinations no single flag covers.
        value_fn=lambda payload: payload.get("status"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_name",
        translation_key="ups_name",
        icon="mdi:tag-outline",
        value_fn=lambda payload: payload.get("name"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_manufacturer",
        translation_key="ups_manufacturer",
        icon="mdi:factory",
        value_fn=lambda payload: nut_data(payload).get("manufacturer"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_model",
        translation_key="ups_model",
        icon="mdi:power-plug-battery",
        value_fn=lambda payload: nut_data(payload).get("model"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_serial",
        translation_key="ups_serial",
        icon="mdi:identifier",
        value_fn=lambda payload: nut_data(payload).get("serial"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_load",
        translation_key="ups_load",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda payload: nut_data(payload).get("load"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_realpower_nominal",
        translation_key="ups_realpower_nominal",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        # No state class: this is the UPS's nameplate rating, not a reading, so
        # it has no business in long-term statistics.
        value_fn=lambda payload: nut_data(payload).get("realpowerNominal"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_battery_charge",
        translation_key="ups_battery_charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_battery("charge"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_battery_charge_low",
        translation_key="ups_battery_charge_low",
        icon="mdi:battery-alert",
        native_unit_of_measurement=PERCENTAGE,
        # A configured threshold rather than a measurement - same reasoning as
        # the nameplate rating above.
        value_fn=_battery("chargeLow"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_battery_runtime",
        translation_key="ups_battery_runtime",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_battery("runtime"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_battery_voltage",
        translation_key="ups_battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_battery("voltage"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_battery_type",
        translation_key="ups_battery_type",
        icon="mdi:battery",
        value_fn=_battery("type"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_input_voltage",
        translation_key="ups_input_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_line("input", "voltage"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_input_frequency",
        translation_key="ups_input_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_line("input", "frequency"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_output_voltage",
        translation_key="ups_output_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_line("output", "voltage"),
    ),
    MOSNutSensorEntityDescription(
        key="ups_output_frequency",
        translation_key="ups_output_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_line("output", "frequency"),
    ),
)


class MOSNutSensor(SensorEntity, MOSEntity):
    """Sensor for the attached UPS, backed by a value function over the nut payload."""

    entity_description: MOSNutSensorEntityDescription

    # Declared explicitly rather than stamped on by async_setup_dynamic_entities:
    # this is a fixed set of entities on the server device, not a dynamic list.
    resource_keys = frozenset({"nut"})

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSNutSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def available(self) -> bool:
        """Whether a UPS is currently reachable, on top of the usual coordinator checks."""
        return super().available and is_ups_reachable(nut_payload(self.coordinator))

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current nut payload."""
        if not self.coordinator.last_update_success:
            return None
        return self.entity_description.value_fn(nut_payload(self.coordinator))


def build_nut_sensors(coordinator: MOSDataUpdateCoordinator) -> list[MOSNutSensor]:
    """Build every UPS sensor entity (entity_factory for the deferred setup helper)."""
    return [MOSNutSensor(coordinator, description) for description in ENTITY_DESCRIPTIONS]
