"""Docker container version sensors for mos, sourced from ``/docker/mos/containers``.

Containers are a dynamic list (created/removed at runtime), so their
entities are added/removed via ``async_setup_dynamic_entities`` rather than a
static ENTITY_DESCRIPTIONS tuple. They live on the main server device
alongside the system sensors; the container's own name is folded into the
entity name via ``translation_placeholders`` so entity_ids stay unique per
container (e.g. ``sensor.mos_server_pushbits_installed_version``).

Note: the ``local``/``remote`` fields are image tags when the container uses
one (e.g. ``1.20.2``), but fall back to a full image digest (``sha256:...``)
when it doesn't - both are valid string states, just not always human-scale.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Docker container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("docker_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSDockerContainerSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS Docker container sensor, including how to derive its value from a container payload."""

    value_fn: Callable[[dict[str, Any]], StateType]


ENTITY_DESCRIPTIONS: tuple[MOSDockerContainerSensorEntityDescription, ...] = (
    MOSDockerContainerSensorEntityDescription(
        key="installed_version",
        translation_key="docker_installed_version",
        icon="mdi:docker",
        value_fn=lambda container: container.get("local"),
    ),
    MOSDockerContainerSensorEntityDescription(
        key="latest_version",
        translation_key="docker_latest_version",
        icon="mdi:docker",
        value_fn=lambda container: container.get("remote"),
    ),
)


class MOSDockerContainerSensor(SensorEntity, MOSEntity):
    """Sensor for a single Docker container, backed by a value function."""

    entity_description: MOSDockerContainerSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSDockerContainerSensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the Docker container sensor."""
        self._container_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_docker_{name}_{entity_description.key}",
            translation_placeholders={"container_name": name},
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


def build_docker_container_sensors(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSDockerContainerSensor]:
    """Build all sensor entities for a single Docker container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSDockerContainerSensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS]
