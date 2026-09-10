"""Server-wide counters for mos, aggregated over the guest lists the coordinator already holds.

These sit on the server device rather than on one guest's own, and answer the
questions a dashboard asks about the host as a whole - how many Docker
containers, Compose stacks, LXC containers and VMs there are, how many of them
run, and how many have an update waiting - without templating over every
per-guest entity. Each group follows the option that decides its guests get
entities at all.

Docker's scope is MOS's own container list, so the same set of containers this
integration gives a device to. Compose stack members are generated containers
with no MOS template and are absent from it; they are counted by the Compose
group instead, per stack.

Only Docker and Compose get an update counter. MOS tracks no image or template
version for an LXC container or a VM, so there is no flag to count.
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


def _running_states(items: list[dict[str, Any]]) -> int:
    """Count the guests whose ``state`` field reads ``running``."""
    return sum(1 for item in items if item.get("state") == "running")


def _updates_available(items: list[dict[str, Any]]) -> int:
    """Count the guests with an update waiting.

    Only an explicit ``True`` counts: MOS leaves the flag unset for a guest it
    could not check, which is not the same as one that is up to date.
    """
    return sum(1 for item in items if item.get("update_available") is True)


@dataclass(frozen=True, kw_only=True)
class MOSSummarySensorEntityDescription(SensorEntityDescription):
    """Describe a server-wide counter, including which list it aggregates and how."""

    data_key: str
    value_fn: Callable[[list[dict[str, Any]]], StateType]
    # Resources this counter reads beyond ``data_key``, so it can report itself
    # unavailable when they go stale rather than counting a field that stopped
    # being current.
    extra_resource_keys: frozenset[str] = frozenset()


# No state class on any of the totals. How many guests exist is a property of
# how the server is set up rather than a measurement over time, and a long-term
# statistic of it is noise in the recorder. The running and update counters do
# change on their own and are worth a history, so they carry one.
DOCKER_ENTITY_DESCRIPTIONS: tuple[MOSSummarySensorEntityDescription, ...] = (
    MOSSummarySensorEntityDescription(
        key="docker_containers_total",
        translation_key="docker_containers_total",
        data_key="docker_containers",
        value_fn=len,
    ),
    MOSSummarySensorEntityDescription(
        key="docker_containers_running",
        translation_key="docker_containers_running",
        data_key="docker_containers",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_running_states,
        # The running state comes from the Docker Engine proxy, which is a
        # separate endpoint from the container list and can fail on its own.
        # Counting a carried-forward or blanked-out state would read as
        # containers having stopped.
        extra_resource_keys=frozenset({"docker_engine_containers"}),
    ),
    MOSSummarySensorEntityDescription(
        key="docker_updates_available",
        translation_key="docker_updates_available",
        data_key="docker_containers",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_updates_available,
    ),
)

COMPOSE_ENTITY_DESCRIPTIONS: tuple[MOSSummarySensorEntityDescription, ...] = (
    MOSSummarySensorEntityDescription(
        key="compose_stacks_total",
        translation_key="compose_stacks_total",
        data_key="compose_stacks",
        value_fn=len,
    ),
    # A stack reports one boolean for the whole thing, so a stack whose services
    # disagree counts as running here - the same reading its own state sensor
    # gives (see sensor/compose.py).
    MOSSummarySensorEntityDescription(
        key="compose_stacks_running",
        translation_key="compose_stacks_running",
        data_key="compose_stacks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stacks: sum(1 for stack in stacks if stack.get("running") is True),
    ),
    MOSSummarySensorEntityDescription(
        key="compose_updates_available",
        translation_key="compose_updates_available",
        data_key="compose_stacks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_updates_available,
        # The update flag reaches a stack from the group list, which is a
        # separate endpoint from the stack list and can go stale on its own.
        extra_resource_keys=frozenset({"docker_groups"}),
    ),
)

# No extra resource keys on either group below: unlike Docker, an LXC container
# and a VM carry their running state in the same payload that lists them.
LXC_ENTITY_DESCRIPTIONS: tuple[MOSSummarySensorEntityDescription, ...] = (
    MOSSummarySensorEntityDescription(
        key="lxc_containers_total",
        translation_key="lxc_containers_total",
        data_key="lxc_containers",
        value_fn=len,
    ),
    MOSSummarySensorEntityDescription(
        key="lxc_containers_running",
        translation_key="lxc_containers_running",
        data_key="lxc_containers",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_running_states,
    ),
)

VM_ENTITY_DESCRIPTIONS: tuple[MOSSummarySensorEntityDescription, ...] = (
    MOSSummarySensorEntityDescription(
        key="vm_machines_total",
        translation_key="vm_machines_total",
        data_key="vm_machines",
        value_fn=len,
    ),
    MOSSummarySensorEntityDescription(
        key="vm_machines_running",
        translation_key="vm_machines_running",
        data_key="vm_machines",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_running_states,
    ),
)


class MOSSummarySensor(SensorEntity, MOSEntity):
    """Server-wide counter, backed by a value function over one coordinator list."""

    entity_description: MOSSummarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSSummarySensorEntityDescription,
    ) -> None:
        """Initialize the summary sensor."""
        super().__init__(coordinator, entity_description)
        self.resource_keys |= frozenset({entity_description.data_key}) | entity_description.extra_resource_keys

    @property
    def native_value(self) -> StateType:
        """Return the counter derived from the current list."""
        if not self.coordinator.last_update_success:
            return None
        items: list[dict[str, Any]] = (self.coordinator.data or {}).get(self.entity_description.data_key) or []
        return self.entity_description.value_fn(items)
