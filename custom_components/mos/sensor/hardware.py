"""Hardware sensor readings for mos, sourced from the ``/sensors`` endpoint.

Unlike disks/pools/containers/VMs, one API item here is already one complete
measurement (e.g. "CPU fan speed = 593 rpm"), not a physical thing with several
static attributes - so there is no per-item device, and every reading is a
single entity on the main server device.

That also means these are the only entities in the integration whose display
name is derived from live API data (the reading's ``name``/``subtype``)
instead of a static ``translation_key``: MOS assigns these names per server,
so there is no fixed, translatable set. ``_attr_name`` is set directly instead.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator

_DEVICE_CLASS_BY_SUBTYPE: dict[str, SensorDeviceClass] = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "voltage": SensorDeviceClass.VOLTAGE,
    "wattage": SensorDeviceClass.POWER,
}

# The full set of subtypes MOS reports (voltage, wattage, temperature, speed,
# percentage, mode). All but "mode" are numeric measurements; "mode" is a
# textual/enum-like reading (e.g. a PSU's operating mode), so it gets no
# state_class - HA expects state_class-tagged sensors to be numeric.
_MEASUREMENT_SUBTYPES = frozenset({"voltage", "wattage", "temperature", "speed", "percentage"})

_ICON_BY_CATEGORY: dict[str, str] = {
    "fan": "mdi:fan",
    "temperature": "mdi:thermometer",
    "power": "mdi:flash",
    "voltage": "mdi:sine-wave",
    "psu": "mdi:power-plug",
    "other": "mdi:chip",
}


def _slug(value: str) -> str:
    """Normalize a MOS-provided label into a safe unique_id fragment."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def sensor_key(item: dict[str, Any]) -> str:
    """Build a stable, human-legible key for a reading from its category/name/subtype.

    The category is dropped when it equals the subtype (e.g. temperature and
    voltage readings), the same way ``_sensor_name`` drops it from the display
    name - the subtype value is category-unique in that case, so nothing is
    lost by not repeating it.
    """
    if item["category"] == item["subtype"]:
        return f"{_slug(item['name'])}_{item['subtype']}"
    return f"{item['category']}_{_slug(item['name'])}_{item['subtype']}"


def _sensor_name(item: dict[str, Any]) -> str:
    """Derive a display name, prefixed with "Sensor" like the resource-type word disks/pools/... get from their device name.

    The category is folded in too (e.g. "Sensor Fan CPU Speed"), except when it
    is identical to the subtype (e.g. temperature/voltage readings, where the
    subtype is already named after the category) - there it would just repeat
    the same word twice.
    """
    if item["category"] == item["subtype"]:
        return f"Sensor {item['name']} {item['subtype'].title()}"
    return f"Sensor {item['category'].title()} {item['name']} {item['subtype'].title()}"


def _find_sensor(coordinator: MOSDataUpdateCoordinator, key: str) -> dict[str, Any] | None:
    """Look up the current payload for a reading by its category/name/subtype key."""
    sensors: list[dict[str, Any]] = coordinator.data.get("sensors") or []
    return next((item for item in sensors if sensor_key(item) == key), None)


class MOSHardwareSensor(SensorEntity, MOSEntity):
    """Sensor for a single hardware reading (fan, temperature, voltage, ...)."""

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        key: str,
        entry_id: str,
    ) -> None:
        """Initialize the hardware sensor."""
        self._key = key
        item = _find_sensor(coordinator, key) or {}
        subtype = item.get("subtype", "")
        entity_description = SensorEntityDescription(
            key=key,
            device_class=_DEVICE_CLASS_BY_SUBTYPE.get(subtype),
            native_unit_of_measurement=item.get("unit"),
            state_class=SensorStateClass.MEASUREMENT if subtype in _MEASUREMENT_SUBTYPES else None,
            icon=_ICON_BY_CATEGORY.get(item.get("category", ""), "mdi:chip"),
        )
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_sensor_{key}",
        )
        self._attr_name = _sensor_name(item) if item else key

    @property
    def native_value(self) -> StateType:
        """Return the current reading's value."""
        if not self.coordinator.last_update_success:
            return None
        item = _find_sensor(self.coordinator, self._key)
        if item is None:
            return None
        return item.get("value")


def build_hardware_sensors(coordinator: MOSDataUpdateCoordinator, key: str) -> list[MOSHardwareSensor]:
    """Build the sensor entity for a single hardware reading (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSHardwareSensor(coordinator, key, entry_id)]
