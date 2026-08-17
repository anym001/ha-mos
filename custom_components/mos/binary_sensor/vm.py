"""VM binary sensors for mos, sourced from the ``/vm/machines/usage`` endpoint.

VMs are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/vm.py for the matching numeric
sensors, on the same per-VM device).

Running state is not duplicated here - it's covered by the VM's power switch
(switch/vm.py), which is both a control and a state indicator.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_machine(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a VM by name."""
    machines: list[dict[str, Any]] = coordinator.data.get("vm_machines") or []
    return next((machine for machine in machines if machine.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSVmMachineBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS VM binary sensor, including how to derive its value from a machine payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]


ENTITY_DESCRIPTIONS: tuple[MOSVmMachineBinarySensorEntityDescription, ...] = (
    MOSVmMachineBinarySensorEntityDescription(
        key="autostart",
        translation_key="vm_autostart",
        value_fn=lambda machine: machine.get("autostart"),
    ),
)


class MOSVmMachineBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a single VM, backed by a value function."""

    entity_description: MOSVmMachineBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSVmMachineBinarySensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the VM binary sensor."""
        self._machine_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_vm_{name}_{entity_description.key}",
            container_device=(f"vm_{name}", f"VM {name}"),
            device_kind=MOSDeviceKind.VM,
        )

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current machine payload."""
        if not self.coordinator.last_update_success:
            return None
        machine = _find_machine(self.coordinator, self._machine_name)
        if machine is None:
            return None
        return self.entity_description.value_fn(machine)


def build_vm_machine_binary_sensors(
    coordinator: MOSDataUpdateCoordinator,
    name: str,
) -> list[MOSVmMachineBinarySensor]:
    """Build the binary sensor entities for a single VM (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSVmMachineBinarySensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS]
