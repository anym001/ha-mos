"""Docker container binary sensors for mos, sourced from ``/docker/mos/containers``.

Containers are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/docker.py for the matching
version sensors, on the same per-container device).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Docker container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("docker_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSDockerContainerBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS Docker container binary sensor, including how to derive its value from a container payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]


ENTITY_DESCRIPTIONS: tuple[MOSDockerContainerBinarySensorEntityDescription, ...] = (
    MOSDockerContainerBinarySensorEntityDescription(
        key="update_available",
        translation_key="docker_update_available",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.UPDATE,
        value_fn=lambda container: container.get("update_available"),
    ),
    MOSDockerContainerBinarySensorEntityDescription(
        key="autostart",
        translation_key="docker_autostart",
        icon="mdi:play-box-outline",
        value_fn=lambda container: container.get("autostart"),
    ),
)


class MOSDockerContainerBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a single Docker container, backed by a value function."""

    entity_description: MOSDockerContainerBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSDockerContainerBinarySensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the Docker container binary sensor."""
        self._container_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_docker_{name}_{entity_description.key}",
            container_device=(f"docker_{name}", f"Docker {name}"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current container payload."""
        if not self.coordinator.last_update_success:
            return None
        container = _find_container(self.coordinator, self._container_name)
        if container is None:
            return None
        return self.entity_description.value_fn(container)


def build_docker_container_binary_sensors(
    coordinator: MOSDataUpdateCoordinator,
    name: str,
) -> list[MOSDockerContainerBinarySensor]:
    """Build the binary sensor entities for a single Docker container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [
        MOSDockerContainerBinarySensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS
    ]
