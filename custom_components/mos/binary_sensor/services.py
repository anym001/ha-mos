"""Service status binary sensors for mos, sourced from the ``/services`` endpoint.

Curated subset of the services MOS reports - the ones users are most likely to
want to monitor - rather than all ~17 flags. These sit on the main server
device (not dynamic; the set of services is fixed by the integration, not by
what MOS currently reports).
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


@dataclass(frozen=True, kw_only=True)
class MOSServiceBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS service binary sensor, including how to derive its value from services."""

    value_fn: Callable[[dict[str, Any]], bool | None]


ENTITY_DESCRIPTIONS: tuple[MOSServiceBinarySensorEntityDescription, ...] = (
    MOSServiceBinarySensorEntityDescription(
        key="docker_running",
        translation_key="docker_running",
        icon="mdi:docker",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda services: (services.get("docker") or {}).get("running"),
    ),
    MOSServiceBinarySensorEntityDescription(
        key="vm_running",
        translation_key="vm_running",
        icon="mdi:server",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda services: (services.get("vm") or {}).get("running"),
    ),
    MOSServiceBinarySensorEntityDescription(
        key="ssh_enabled",
        translation_key="ssh_enabled",
        icon="mdi:ssh",
        value_fn=lambda services: (services.get("ssh") or {}).get("enabled"),
    ),
    MOSServiceBinarySensorEntityDescription(
        key="samba_enabled",
        translation_key="samba_enabled",
        icon="mdi:folder-network",
        value_fn=lambda services: (services.get("samba") or {}).get("enabled"),
    ),
    MOSServiceBinarySensorEntityDescription(
        key="nfs_enabled",
        translation_key="nfs_enabled",
        icon="mdi:folder-network",
        value_fn=lambda services: (services.get("nfs") or {}).get("enabled"),
    ),
    MOSServiceBinarySensorEntityDescription(
        key="tailscale_online",
        translation_key="tailscale_online",
        icon="mdi:network",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda services: (services.get("tailscale") or {}).get("online"),
    ),
    MOSServiceBinarySensorEntityDescription(
        key="netbird_online",
        translation_key="netbird_online",
        icon="mdi:network",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda services: (services.get("netbird") or {}).get("online"),
    ),
)


class MOSServiceBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a MOS service, backed by a value function."""

    entity_description: MOSServiceBinarySensorEntityDescription

    # Declared explicitly rather than stamped on by async_setup_dynamic_entities:
    # the service sensors are a fixed set on the server device, not a dynamic
    # list, so they are constructed directly by the platform.
    resource_keys = frozenset({"services"})

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSServiceBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current services payload."""
        if not self.coordinator.last_update_success:
            return None
        services: dict[str, Any] = self.coordinator.data.get("services", {})
        return self.entity_description.value_fn(services)
