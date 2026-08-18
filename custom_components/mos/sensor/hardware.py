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

from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.components.sensor.const import DEVICE_CLASS_UNITS
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfPower, UnitOfTemperature
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

# MOS spells the same unit differently depending on where the reading comes
# from - one server reports a CPU temperature in "c", another in "°C" - and HA
# rejects everything but its own spelling for a unit that belongs to a device
# class. Only the spellings that need folding are listed; units HA has no
# opinion on (e.g. "rpm") pass through untouched.
_UNIT_ALIASES: dict[str, str] = {
    "c": UnitOfTemperature.CELSIUS,
    "°c": UnitOfTemperature.CELSIUS,
    "degc": UnitOfTemperature.CELSIUS,
    "celsius": UnitOfTemperature.CELSIUS,
    "f": UnitOfTemperature.FAHRENHEIT,
    "°f": UnitOfTemperature.FAHRENHEIT,
    "degf": UnitOfTemperature.FAHRENHEIT,
    "fahrenheit": UnitOfTemperature.FAHRENHEIT,
    "k": UnitOfTemperature.KELVIN,
    "kelvin": UnitOfTemperature.KELVIN,
    "v": UnitOfElectricPotential.VOLT,
    "volt": UnitOfElectricPotential.VOLT,
    "volts": UnitOfElectricPotential.VOLT,
    "mv": UnitOfElectricPotential.MILLIVOLT,
    "w": UnitOfPower.WATT,
    "watt": UnitOfPower.WATT,
    "watts": UnitOfPower.WATT,
    "kw": UnitOfPower.KILO_WATT,
    "%": PERCENTAGE,
    "percent": PERCENTAGE,
}

# The icons themselves live in icons.json under ``hardware_<category>``. A
# reading's category is assigned per server and only known at runtime, so a
# static icon on the description cannot express it - but a translation_key can,
# because it is resolved per entity. These readings carry one for the icon
# alone; the display name still comes from ``_attr_name`` below, which takes
# precedence over any name translation.
_ICON_CATEGORIES = frozenset({"fan", "temperature", "power", "voltage", "psu", "other"})


_CATEGORY_DISPLAY: dict[str, str] = {"psu": "PSU"}


def sensor_key(item: dict[str, Any]) -> str:
    """Return the reading's stable identity key: MOS's own ``id``.

    Unlike name/category/subtype, this never changes when a user renames a
    reading in MOS, so it keeps unique_id and the entity registry entry
    stable across renames instead of the dynamic-entity helper tearing down
    and recreating the entity.
    """
    return str(item["id"])


def _sensor_name(item: dict[str, Any]) -> str:
    """Derive a display name, prefixed with "Sensor" like the resource-type word disks/pools/... get from their device name.

    The category is folded in too (e.g. "Sensor Fan CPU Speed"), except when it
    is identical to the subtype (e.g. temperature/voltage readings, where the
    subtype is already named after the category) - there it would just repeat
    the same word twice. The subtype word itself is dropped when the name
    already ends with it (e.g. PSU's "Fan Speed" reading with subtype
    "speed") to avoid the same "... Speed Speed" duplication.
    """
    name, subtype, category = item["name"], item["subtype"], item["category"]
    suffix = "" if name.split()[-1].lower() == subtype.lower() else f" {subtype.title()}"
    if category == subtype:
        return f"Sensor {name}{suffix}"
    return f"Sensor {_CATEGORY_DISPLAY.get(category, category.title())} {name}{suffix}"


def _unit(item: dict[str, Any]) -> str | None:
    """Return the reading's unit in the spelling HA expects, or None if MOS reports none."""
    raw = str(item.get("unit") or "").strip()
    if not raw:
        return None
    return _UNIT_ALIASES.get(raw.casefold(), raw)


def _device_class(subtype: str, unit: str | None) -> SensorDeviceClass | None:
    """Return the device class for a subtype, unless the unit contradicts it.

    A device class HA cannot reconcile with the unit is worse than none: it
    makes HA drop the reading out of unit conversion and long-term statistics
    and log a warning per start. Dropping it keeps the reading itself intact,
    so an unforeseen unit costs display polish rather than the entity.
    """
    device_class = _DEVICE_CLASS_BY_SUBTYPE.get(subtype)
    if device_class is None:
        return None
    valid_units = DEVICE_CLASS_UNITS.get(device_class)
    if valid_units is None or unit in valid_units:
        return device_class
    return None


def _icon_translation_key(item: dict[str, Any]) -> str:
    """Return the icons.json key holding this reading's icon.

    An unrecognised category resolves to ``other``, which carries the same
    ``mdi:chip`` this used to fall back to.
    """
    category = item.get("category", "")
    return f"hardware_{category if category in _ICON_CATEGORIES else 'other'}"


def _find_sensor(coordinator: MOSDataUpdateCoordinator, key: str) -> dict[str, Any] | None:
    """Look up the current payload for a reading by its ``id``."""
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
        unit = _unit(item)
        entity_description = SensorEntityDescription(
            key=key,
            device_class=_device_class(subtype, unit),
            native_unit_of_measurement=unit,
            state_class=SensorStateClass.MEASUREMENT if subtype in _MEASUREMENT_SUBTYPES else None,
            translation_key=_icon_translation_key(item),
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
