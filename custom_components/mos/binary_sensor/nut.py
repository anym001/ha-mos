"""UPS binary sensors for mos, sourced from the ``/nut/status`` endpoint.

Splits the two boolean facts out of the payload that automations actually key
on: whether MOS can see a UPS at all, and which of NUT's status flags are
currently set (``OL`` on line power, ``OB`` on battery, ``LB`` low battery,
``CHRG`` charging). The raw flag string stays available as a sensor for the
combinations these do not cover.

Like the UPS sensors, these are created the first time a UPS answers and then
stay. From then on ``ups_reachable`` remains available even with no UPS
attached - reporting "not connected" is its whole job - while the flag-backed
sensors go unavailable along with the rest of the UPS entities, since NUT
reports no status at all then.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from custom_components.mos.entity_utils import is_ups_reachable, nut_payload, nut_status_flags
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class MOSNutBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS UPS binary sensor, including how to derive its value from the nut payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]

    # Whether this sensor still says something useful with no UPS attached.
    # True for the reachability sensor alone; everything else is derived from
    # status flags that do not exist then.
    survives_unreachable: bool = False


def _has_flag(flag: str) -> Callable[[dict[str, Any]], bool | None]:
    """Return a value function testing for one NUT status flag."""
    return lambda payload: flag in nut_status_flags(payload)


ENTITY_DESCRIPTIONS: tuple[MOSNutBinarySensorEntityDescription, ...] = (
    MOSNutBinarySensorEntityDescription(
        key="ups_reachable",
        translation_key="ups_reachable",
        icon="mdi:power-plug-battery",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda payload: is_ups_reachable(payload),
        survives_unreachable=True,
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_online",
        translation_key="ups_online",
        # POWER reads as "on = power detected", which is exactly what OL means:
        # the UPS is running off mains rather than off its battery.
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=_has_flag("OL"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_on_battery",
        translation_key="ups_on_battery",
        icon="mdi:power-plug-off",
        # Not simply the inverse of ups_online: a UPS in bypass or on a failed
        # battery reports neither flag, and conflating the two would claim mains
        # power is fine when NUT never said so.
        value_fn=_has_flag("OB"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_battery_low",
        translation_key="ups_battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=_has_flag("LB"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_battery_charging",
        translation_key="ups_battery_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_has_flag("CHRG"),
    ),
)


class MOSNutBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for the attached UPS, backed by a value function over the nut payload."""

    entity_description: MOSNutBinarySensorEntityDescription

    # Declared explicitly rather than stamped on by async_setup_dynamic_entities:
    # this is a fixed set of entities on the server device, not a dynamic list.
    resource_keys = frozenset({"nut"})

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSNutBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def available(self) -> bool:
        """Whether this sensor has something to say, given whether a UPS answered."""
        if not super().available:
            return False
        return self.entity_description.survives_unreachable or is_ups_reachable(nut_payload(self.coordinator))

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current nut payload."""
        if not self.coordinator.last_update_success:
            return None
        return self.entity_description.value_fn(nut_payload(self.coordinator))


def build_nut_binary_sensors(coordinator: MOSDataUpdateCoordinator) -> list[MOSNutBinarySensor]:
    """Build every UPS binary sensor entity (entity_factory for the deferred setup helper)."""
    return [MOSNutBinarySensor(coordinator, description) for description in ENTITY_DESCRIPTIONS]
