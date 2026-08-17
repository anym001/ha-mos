"""UPS binary sensors for mos, sourced from the ``/nut/status`` endpoint.

Splits the boolean facts out of the payload that automations actually key on:
whether MOS can see a UPS at all, plus one sensor per NUT status flag. NUT
reports ``ups.status`` as a space-separated set of flags that apply at once
("OB DISCHRG LB" on a draining battery), so a flag is a boolean in its own
right rather than one value of an enumeration - which is why each gets its own
sensor instead of the raw string being mapped to a single state. That raw
string stays available as a sensor for reading the combination as a whole.

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

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from custom_components.mos.entity_utils import is_ups_reachable, nut_device_hardware, nut_payload, nut_status_flags
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

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
        # Icon is state-dependent (icons.json), not set here: this is the
        # loss-of-mains signal, so the shape should flip between on/off, not
        # just the color.
        # Not simply the inverse of ups_online: a UPS in bypass or on a failed
        # battery reports neither flag, and conflating the two would claim mains
        # power is fine when NUT never said so.
        value_fn=_has_flag("OB"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_battery_low",
        translation_key="ups_battery_low",
        # The end of the countdown, not just a level: NUT's own upsmon shuts
        # the host down on OB together with LB. Its counterpart ups_battery_high
        # is diagnostic on purpose - see there.
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=_has_flag("LB"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_battery_charging",
        translation_key="ups_battery_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_has_flag("CHRG"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_discharging",
        translation_key="ups_discharging",
        # Not BATTERY_CHARGING inverted: a UPS on mains with a full battery is
        # neither charging nor discharging, so the two are separate facts. They
        # are one pair for categorising though - the same battery, the same kind
        # of statement - so both sit here rather than one on each side.
        value_fn=_has_flag("DISCHRG"),
    ),
    # The remaining NUT flags, all diagnostic. The split is not about how
    # serious a state is but about what the flag answers. Everything above
    # tracks the live power situation - mains present or lost, and the battery
    # countdown that follows from it - which is what decides whether the server
    # is still up in a few minutes. Everything below reports the UPS's own
    # health, mode or internals, however urgent it happens to be.
    #
    # Urgency is not lost by this: a diagnostic entity sits one section down on
    # the same device page and stays fully available to automations, so
    # anything worth being woken up for belongs in an automation either way.
    MOSNutBinarySensorEntityDescription(
        key="ups_battery_high",
        translation_key="ups_battery_high",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Diagnostic while ups_battery_low is primary, and that asymmetry is
        # deliberate rather than an oversight like the charge/discharge pair
        # was: HB reports the charge sitting in its upper range, which
        # sensor.ups_battery already says continuously and more precisely,
        # while LB is what the shutdown hangs on. Plenty of drivers never send
        # HB at all, so promoting it would mostly add an always-off row.
        # Not the BATTERY device class: that one reads "on = battery low", so
        # using it for the opposite condition would invert its meaning.
        value_fn=_has_flag("HB"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_replace_battery",
        translation_key="ups_replace_battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        # No icon: PROBLEM already flips between an alert and an all-clear,
        # which a fixed icon would override (same as the disk/pool sensors).
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_has_flag("RB"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_bypass",
        translation_key="ups_bypass",
        entity_category=EntityCategory.DIAGNOSTIC,
        # A problem rather than a mode: the load is on raw mains, so the next
        # power cut goes straight through to the server.
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_has_flag("BYPASS"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_calibrating",
        translation_key="ups_calibrating",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Not a problem: a calibration is a scheduled maintenance run the UPS
        # starts and ends on its own. It does put the load on battery while it
        # runs, but so does an outage, and ups_discharging reports the draining
        # either way - this flag only says what caused it.
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=_has_flag("CAL"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_output_off",
        translation_key="ups_output_off",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_has_flag("OFF"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_overload",
        translation_key="ups_overload",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_has_flag("OVER"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_voltage_trim",
        translation_key="ups_voltage_trim",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Regulation doing its job, not a fault - hence a direction arrow
        # rather than a warning icon.
        value_fn=_has_flag("TRIM"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_voltage_boost",
        translation_key="ups_voltage_boost",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_has_flag("BOOST"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_forced_shutdown",
        translation_key="ups_forced_shutdown",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_has_flag("FSD"),
    ),
    MOSNutBinarySensorEntityDescription(
        key="ups_alarm",
        translation_key="ups_alarm",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Driver-specific: what raised it has to be read off ups_status, so
        # this only reports that something did.
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_has_flag("ALARM"),
    ),
)


class MOSNutBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for the attached UPS, backed by a value function over the nut payload."""

    entity_description: MOSNutBinarySensorEntityDescription

    # Declared explicitly rather than stamped on by async_setup_dynamic_entities:
    # this is a fixed set of entities on their own UPS device, not a dynamic list.
    resource_keys = frozenset({"nut"})

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSNutBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            entity_description,
            container_device=("nut", "UPS"),
            device_kind=MOSDeviceKind.UPS,
            device_translation_key="nut",
            device_hardware=nut_device_hardware(coordinator),
        )

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
