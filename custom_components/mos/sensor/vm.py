"""VM sensors for mos, sourced from the ``/vm/machines/usage`` endpoint.

VMs are a dynamic list (created/destroyed at runtime), so their entities are
added/removed via ``async_setup_dynamic_entities`` rather than a static
ENTITY_DESCRIPTIONS tuple. Each VM gets its own device (linked back to the
main server device via ``via_device``), mirroring the LXC/Docker container
pattern (see sensor/lxc.py).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_machine(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a VM by name."""
    machines: list[dict[str, Any]] = coordinator.data.get("vm_machines") or []
    return next((machine for machine in machines if machine.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSVmMachineSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS VM sensor, including how to derive its value from a machine payload."""

    value_fn: Callable[[dict[str, Any]], StateType]
    # Where to find this sensor's entity picture in the machine payload, for the
    # one sensor that carries the VM's icon (see the LXC and Docker equivalents).
    picture_fn: Callable[[dict[str, Any]], str | None] | None = None


# MOS's own vocabulary for a VM, which its API schema declares as a closed enum
# of exactly these two - unlike LXC, where the same field is documented as open
# ended. libvirt underneath has a much longer list (paused, crashed,
# pmsuspended, ...); MOS collapses it before answering, and this follows what
# MOS reports rather than what libvirt knows.
VM_STATES = ["running", "stopped"]


ENTITY_DESCRIPTIONS: tuple[MOSVmMachineSensorEntityDescription, ...] = (
    # First for the same reason as the LXC and Docker state sensors: the power
    # switch reduces the state to on/off, and nothing else carried it.
    MOSVmMachineSensorEntityDescription(
        key="state",
        translation_key="vm_state",
        device_class=SensorDeviceClass.ENUM,
        options=VM_STATES,
        value_fn=lambda machine: machine.get("state"),
        picture_fn=lambda machine: machine.get("icon_url"),
    ),
    MOSVmMachineSensorEntityDescription(
        key="cpu_usage",
        translation_key="vm_cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda machine: (machine.get("cpu") or {}).get("usage"),
    ),
    MOSVmMachineSensorEntityDescription(
        key="memory_usage",
        translation_key="vm_memory_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda machine: (machine.get("memory") or {}).get("bytes"),
    ),
)


class MOSVmMachineSensor(SensorEntity, MOSEntity):
    """Sensor for a single VM, backed by a value function."""

    entity_description: MOSVmMachineSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSVmMachineSensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the VM sensor."""
        self._machine_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_vm_{name}_{entity_description.key}",
            container_device=(f"vm_{name}", f"VM {name}"),
            device_kind=MOSDeviceKind.VM,
        )

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current machine payload."""
        if not self.coordinator.last_update_success:
            return None
        machine = _find_machine(self.coordinator, self._machine_name)
        if machine is None:
            return None
        return self.entity_description.value_fn(machine)

    @property
    def entity_picture(self) -> str | None:
        """
        Return the VM's icon URL, so cards show it without templating.

        Same source and same guarantee as the LXC counterpart: a URL on the MOS
        server's own web root, set only once the server confirmed the file is
        there (see ``coordinator/guest_icons.py``).

        Returns:
            The icon URL, or ``None`` when the VM has no usable one.

        """
        if self.entity_description.picture_fn is None:
            return None
        machine = _find_machine(self.coordinator, self._machine_name)
        if machine is None:
            return None
        return self.entity_description.picture_fn(machine)


def build_vm_machine_sensors(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSVmMachineSensor]:
    """Build all sensor entities for a single VM (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSVmMachineSensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS]
