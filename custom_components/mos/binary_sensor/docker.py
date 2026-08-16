"""Docker container binary sensors for mos, sourced from ``/docker/mos/containers``.

Containers are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/docker.py for the matching
version sensors, on the same per-container device).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator

# What MOS reports for a container that defines no healthcheck at all. It says
# so explicitly rather than omitting the field, so this value - not a missing
# one - is what tells a container with no healthcheck apart from one whose
# health is merely not known yet.
HEALTH_NOT_CONFIGURED = "none"


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Docker container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("docker_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


def _is_unhealthy(container: dict[str, Any]) -> bool | None:
    """
    Report whether a container's healthcheck is currently failing.

    Only meaningful while the container runs. Docker leaves the health status at
    whatever it last was when a container stops, so a container that exited
    weeks ago still reports ``unhealthy`` with a zero failing streak and an
    empty check log - a verdict no healthcheck ever reached. Reporting that as a
    problem would flag every stopped container on the dashboard, so a container
    that is not running has no health to report.

    Returns:
        ``True`` when the healthcheck is failing, ``False`` when it passes, and
        ``None`` while the container is not running.

    """
    if container.get("state") != "running":
        return None
    return container.get("health") == "unhealthy"


@dataclass(frozen=True, kw_only=True)
class MOSDockerContainerBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS Docker container binary sensor, including how to derive its value from a container payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    # Resources this sensor reads beyond the one the dynamic helper syncs it
    # against; health, like the running state, comes from the Docker Engine
    # proxy rather than from MOS's container list.
    extra_resource_keys: frozenset[str] = frozenset()


ENTITY_DESCRIPTIONS: tuple[MOSDockerContainerBinarySensorEntityDescription, ...] = (
    MOSDockerContainerBinarySensorEntityDescription(
        key="healthy",
        translation_key="docker_healthy",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_is_unhealthy,
        extra_resource_keys=frozenset({"docker_engine_containers"}),
    ),
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
            device_kind=MOSDeviceKind.DOCKER,
        )
        self.resource_keys |= entity_description.extra_resource_keys

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
    """
    Build the binary sensor entities for a single Docker container (entity_factory for the dynamic helper).

    The health sensor is left out for a container that defines no healthcheck,
    rather than added as one that can only ever say "unknown". Only an explicit
    ``none`` counts as that: a container first seen while the Docker Engine
    proxy was unavailable has no health *yet*, and still gets the sensor.

    A container that gains a healthcheck later keeps its name, so the dynamic
    helper does not rebuild its entities; the sensor appears after the next
    reload.

    Returns:
        The binary sensor entities for this container.

    """
    entry_id = coordinator.config_entry.entry_id
    container = _find_container(coordinator, name) or {}
    has_healthcheck = container.get("health") != HEALTH_NOT_CONFIGURED
    return [
        MOSDockerContainerBinarySensor(coordinator, description, name, entry_id)
        for description in ENTITY_DESCRIPTIONS
        if description.key != "healthy" or has_healthcheck
    ]
