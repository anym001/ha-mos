"""LXC container sensors for mos, sourced from the ``/lxc/containers/usage`` endpoint.

Containers are a dynamic list (created/destroyed at runtime), so their
entities are added/removed via ``async_setup_dynamic_entities`` rather than a
static ENTITY_DESCRIPTIONS tuple. Each container gets its own device (linked
back to the main server device via ``via_device``), so it can be individually
enabled/disabled from its device page instead of cluttering the server
device's entity list (e.g. ``sensor.sirius_lxc_database_cpu_usage``; the
server name and "lxc" category keep things unique across multiple servers
and disambiguate from a Docker container of the same name).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for an LXC container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("lxc_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSLxcContainerSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS LXC container sensor, including how to derive its value from a container payload."""

    value_fn: Callable[[dict[str, Any]], StateType]


# LXC's own container states, all of which MOS can pass through. Listed in full
# rather than just the two common ones: a state missing from an enum sensor's
# options is an error at runtime, and MOS itself documents the field as
# "running, stopped, etc.", so the tail of that "etc." has to be covered here.
#
# The freeze states are not hypothetical on a MOS server - it exposes
# /lxc/containers/{name}/freeze and /unfreeze, so a user can reach them from the
# web UI. "thawed" is LXC's transitional state on the way back out of frozen and
# has never been observed in a MOS payload, but costs nothing to accept.
LXC_STATES = ["aborting", "freezing", "frozen", "running", "starting", "stopped", "stopping", "thawed"]


ENTITY_DESCRIPTIONS: tuple[MOSLxcContainerSensorEntityDescription, ...] = (
    # First because it is the one a dashboard card is built around: the power
    # switch collapses the state to on/off, so until now nothing exposed which
    # of LXC's states a container was actually in.
    MOSLxcContainerSensorEntityDescription(
        key="state",
        translation_key="lxc_state",
        device_class=SensorDeviceClass.ENUM,
        options=LXC_STATES,
        value_fn=lambda container: container.get("state"),
    ),
    MOSLxcContainerSensorEntityDescription(
        key="cpu_usage",
        translation_key="lxc_cpu_usage",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda container: (container.get("cpu") or {}).get("usage"),
    ),
    MOSLxcContainerSensorEntityDescription(
        key="memory_usage",
        translation_key="lxc_memory_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda container: (container.get("memory") or {}).get("bytes"),
    ),
)


class MOSLxcContainerSensor(SensorEntity, MOSEntity):
    """Sensor for a single LXC container, backed by a value function."""

    entity_description: MOSLxcContainerSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSLxcContainerSensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the LXC container sensor."""
        self._container_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_lxc_{name}_{entity_description.key}",
            container_device=(f"lxc_{name}", f"LXC {name}"),
        )

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current container payload."""
        if not self.coordinator.last_update_success:
            return None
        container = _find_container(self.coordinator, self._container_name)
        if container is None:
            return None
        return self.entity_description.value_fn(container)


def build_lxc_container_sensors(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSLxcContainerSensor]:
    """Build all sensor entities for a single LXC container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSLxcContainerSensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS]
