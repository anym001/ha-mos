"""LXC container binary sensors for mos, sourced from the ``/lxc/containers/usage`` endpoint.

Containers are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/lxc.py for the matching numeric
sensors, on the same main server device).
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

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for an LXC container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("lxc_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSLxcContainerBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS LXC container binary sensor, including how to derive its value from a container payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]


ENTITY_DESCRIPTIONS: tuple[MOSLxcContainerBinarySensorEntityDescription, ...] = (
    MOSLxcContainerBinarySensorEntityDescription(
        key="running",
        translation_key="lxc_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda container: container.get("state") == "running",
    ),
    MOSLxcContainerBinarySensorEntityDescription(
        key="autostart",
        translation_key="lxc_autostart",
        icon="mdi:play-box-outline",
        value_fn=lambda container: container.get("autostart"),
    ),
)


class MOSLxcContainerBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a single LXC container, backed by a value function."""

    entity_description: MOSLxcContainerBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSLxcContainerBinarySensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the LXC container binary sensor."""
        self._container_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_lxc_{name}_{entity_description.key}",
            translation_placeholders={"container_name": name},
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


def build_lxc_container_binary_sensors(
    coordinator: MOSDataUpdateCoordinator,
    name: str,
) -> list[MOSLxcContainerBinarySensor]:
    """Build the binary sensor entities for a single LXC container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [
        MOSLxcContainerBinarySensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS
    ]
