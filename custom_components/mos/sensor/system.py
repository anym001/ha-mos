"""System sensors for mos, sourced from the ``/osinfo`` endpoint."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class MOSSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS system sensor, including how to derive its value from osinfo."""

    value_fn: Callable[[dict[str, Any]], StateType | datetime]


def _boot_time(osinfo: dict[str, Any]) -> datetime | None:
    """Parse the boot timestamp from ``uptime.since``.

    The MOS timestamp (e.g. ``2026-07-24 20:13:48``) carries no timezone, so it is
    interpreted as Home Assistant's local timezone.
    """
    since = (osinfo.get("uptime") or {}).get("since")
    if not since:
        return None
    parsed = dt_util.parse_datetime(since)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed


def _base_os(osinfo: dict[str, Any]) -> str | None:
    """Combine the base OS name and version from the first ``base`` entry."""
    base = osinfo.get("base") or []
    if not base:
        return None
    first = base[0]
    name = first.get("os_name")
    version = first.get("os_version")
    if name and version:
        return f"{name} {version}"
    return name


ENTITY_DESCRIPTIONS: tuple[MOSSensorEntityDescription, ...] = (
    MOSSensorEntityDescription(
        key="boot_time",
        translation_key="boot_time",
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_boot_time,
    ),
    MOSSensorEntityDescription(
        key="mos_version",
        translation_key="mos_version",
        icon="mdi:tag-outline",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("version"),
    ),
    MOSSensorEntityDescription(
        key="mos_channel",
        translation_key="mos_channel",
        icon="mdi:source-branch",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("channel"),
    ),
    MOSSensorEntityDescription(
        key="mos_build",
        translation_key="mos_build",
        icon="mdi:hammer-wrench",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("build"),
    ),
    MOSSensorEntityDescription(
        key="mos_api",
        translation_key="mos_api",
        icon="mdi:api",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("api"),
    ),
    MOSSensorEntityDescription(
        key="mos_frontend",
        translation_key="mos_frontend",
        icon="mdi:monitor-dashboard",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("frontend"),
    ),
    MOSSensorEntityDescription(
        key="running_kernel",
        translation_key="running_kernel",
        icon="mdi:penguin",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("running_kernel"),
    ),
    MOSSensorEntityDescription(
        key="recommended_kernel",
        translation_key="recommended_kernel",
        icon="mdi:penguin",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("recommended_kernel"),
    ),
    MOSSensorEntityDescription(
        key="arch",
        translation_key="arch",
        icon="mdi:chip",
        value_fn=lambda osinfo: (osinfo.get("mos") or {}).get("arch"),
    ),
    MOSSensorEntityDescription(
        key="cpu_brand",
        translation_key="cpu_brand",
        icon="mdi:cpu-64-bit",
        value_fn=lambda osinfo: (osinfo.get("cpu") or {}).get("brand"),
    ),
    MOSSensorEntityDescription(
        key="base_os",
        translation_key="base_os",
        icon="mdi:linux",
        value_fn=_base_os,
    ),
)


class MOSSystemSensor(SensorEntity, MOSEntity):
    """System sensor backed by a value function over the osinfo payload."""

    entity_description: MOSSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> StateType | datetime:
        """Return the value derived from the current osinfo data."""
        if not self.coordinator.last_update_success:
            return None
        osinfo: dict[str, Any] = (self.coordinator.data or {}).get("osinfo", {})
        return self.entity_description.value_fn(osinfo)
