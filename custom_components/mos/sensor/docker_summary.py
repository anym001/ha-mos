"""Server-wide Docker counters for mos, aggregated over ``/docker/mos/containers``.

These sit on the server device rather than on a container's own, and answer the
questions a dashboard asks about the host as a whole - how many containers there
are, how many of them run, and how many have an image update waiting - without
templating over every per-container entity.

Scope is MOS's own container list, so the same set of containers this
integration gives a device to. Compose stack members are generated containers
with no MOS template and are absent from it; a stack reports its own members
through ``compose_container_count`` and ``compose_running_containers``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class MOSDockerSummarySensorEntityDescription(SensorEntityDescription):
    """Describe a server-wide Docker counter, including how to derive it from the container list."""

    value_fn: Callable[[list[dict[str, Any]]], StateType]
    # Resources this counter reads beyond ``docker_containers``, so it can report
    # itself unavailable when they go stale rather than counting a field that
    # stopped being current.
    extra_resource_keys: frozenset[str] = frozenset()


ENTITY_DESCRIPTIONS: tuple[MOSDockerSummarySensorEntityDescription, ...] = (
    # No state class: how many containers exist is a property of how the server
    # is set up rather than a measurement over time, and a long-term statistic of
    # it is noise in the recorder. The two counters below do change on their own
    # and are worth a history, so they carry one.
    MOSDockerSummarySensorEntityDescription(
        key="docker_containers_total",
        translation_key="docker_containers_total",
        value_fn=len,
    ),
    MOSDockerSummarySensorEntityDescription(
        key="docker_containers_running",
        translation_key="docker_containers_running",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda containers: sum(1 for container in containers if container.get("state") == "running"),
        # The running state comes from the Docker Engine proxy, which is a
        # separate endpoint from the container list this counter is otherwise
        # derived from and can fail on its own. Counting a carried-forward or
        # blanked-out state would read as containers having stopped.
        extra_resource_keys=frozenset({"docker_engine_containers"}),
    ),
    MOSDockerSummarySensorEntityDescription(
        key="docker_updates_available",
        translation_key="docker_updates_available",
        state_class=SensorStateClass.MEASUREMENT,
        # Only an explicit ``True`` counts: MOS leaves the flag unset for a
        # container it could not check, which is not the same as one that is
        # up to date.
        value_fn=lambda containers: sum(1 for container in containers if container.get("update_available") is True),
    ),
)


class MOSDockerSummarySensor(SensorEntity, MOSEntity):
    """Server-wide Docker counter, backed by a value function over the container list."""

    entity_description: MOSDockerSummarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSDockerSummarySensorEntityDescription,
    ) -> None:
        """Initialize the Docker summary sensor."""
        super().__init__(coordinator, entity_description)
        self.resource_keys |= frozenset({"docker_containers"}) | entity_description.extra_resource_keys

    @property
    def native_value(self) -> StateType:
        """Return the counter derived from the current container list."""
        if not self.coordinator.last_update_success:
            return None
        containers: list[dict[str, Any]] = (self.coordinator.data or {}).get("docker_containers") or []
        return self.entity_description.value_fn(containers)
