"""Docker container power switch for mos, controlling the raw Docker Engine proxy.

Passing Docker requests straight through to the Docker Engine API (rather
than exposing purpose-built MOS endpoints, as LXC has) was a deliberate MOS
design choice, confirmed with the MOS developer. This switch calls
``POST /docker/containers/{name}/start`` and ``/stop``, proxied straight to
Docker's own ``/containers/{id}/start``/``/stop`` (Docker accepts a container
name in place of an ID).

Running state comes from the coordinator's merged ``state`` field (see
coordinator/base.py's ``_merge_docker_engine_state``) - ``/docker/mos/containers``
alone has no running-state field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientError
from custom_components.mos.const import LOGGER, MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Docker container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("docker_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


ENTITY_DESCRIPTION = SwitchEntityDescription(
    key="power",
    translation_key="docker_power",
    icon="mdi:power",
)


class MOSDockerContainerSwitch(SwitchEntity, MOSEntity):
    """Switch that starts/stops a single Docker container on the MOS server."""

    entity_description: SwitchEntityDescription

    # The container's *existence* comes from ``docker_containers`` (stamped on by
    # async_setup_dynamic_entities), but its running state is merged in from the
    # Docker Engine proxy. If that proxy goes stale, the switch would keep
    # showing a position it can no longer verify, so it counts as a backing
    # resource too. The Docker binary sensors deliberately do not declare it -
    # update-available and autostart come from ``/docker/mos/containers`` alone
    # and stay valid while the proxy is down.
    resource_keys = frozenset({"docker_engine_containers"})

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the Docker container power switch."""
        self._container_name = name
        super().__init__(
            coordinator,
            ENTITY_DESCRIPTION,
            unique_id=f"{entry_id}_docker_{name}_{ENTITY_DESCRIPTION.key}",
            container_device=(f"docker_{name}", f"Docker {name}"),
            device_kind=MOSDeviceKind.DOCKER,
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
            await self.coordinator.async_start_docker_container(self._container_name)
        except MOSApiClientError as exception:
            LOGGER.warning("Failed to start Docker container %s: %s", self._container_name, exception)
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="docker_start_failed",
                translation_placeholders={"name": self._container_name},
            ) from exception

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the container on the MOS server."""
        try:
            await self.coordinator.async_stop_docker_container(self._container_name)
        except MOSApiClientError as exception:
            LOGGER.warning("Failed to stop Docker container %s: %s", self._container_name, exception)
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="docker_stop_failed",
                translation_placeholders={"name": self._container_name},
            ) from exception


def build_docker_container_switches(
    coordinator: MOSDataUpdateCoordinator,
    name: str,
) -> list[MOSDockerContainerSwitch]:
    """Build the switch entity for a single Docker container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSDockerContainerSwitch(coordinator, name, entry_id)]
