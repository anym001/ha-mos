"""LXC container power switch for mos, controlling ``/lxc/containers/{name}/start`` and ``/stop``.

This is the integration's first write action - unlike the read-only
sensors/binary_sensors, turning this switch on/off actually starts or stops
the container on the MOS server. It doubles as the container's running-state
indicator (see binary_sensor/lxc.py, which deliberately does not duplicate
this).

Docker containers have no equivalent switch yet: MOS has no single-container
start/stop endpoint for Docker (only compose-stack and group level), so this
is LXC-only until such an endpoint exists.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientError
from custom_components.mos.entity import MOSEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for an LXC container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("lxc_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


ENTITY_DESCRIPTION = SwitchEntityDescription(
    key="power",
    translation_key="lxc_power",
    icon="mdi:power",
)


class MOSLxcContainerSwitch(SwitchEntity, MOSEntity):
    """Switch that starts/stops a single LXC container on the MOS server."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the LXC container power switch."""
        self._container_name = name
        super().__init__(
            coordinator,
            ENTITY_DESCRIPTION,
            unique_id=f"{entry_id}_lxc_{name}_{ENTITY_DESCRIPTION.key}",
            container_device=(f"lxc_{name}", f"LXC {name}"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the container is currently running."""
        if not self.coordinator.last_update_success:
            return None
        container = _find_container(self.coordinator, self._container_name)
        if container is None:
            return None
        return container.get("state") == "running"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the container on the MOS server."""
        try:
            await self.coordinator.async_start_lxc_container(self._container_name)
        except MOSApiClientError as exception:
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="lxc_start_failed",
                translation_placeholders={"name": self._container_name},
            ) from exception

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the container on the MOS server."""
        try:
            await self.coordinator.async_stop_lxc_container(self._container_name)
        except MOSApiClientError as exception:
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="lxc_stop_failed",
                translation_placeholders={"name": self._container_name},
            ) from exception


def build_lxc_container_switches(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSLxcContainerSwitch]:
    """Build the switch entity for a single LXC container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSLxcContainerSwitch(coordinator, name, entry_id)]
