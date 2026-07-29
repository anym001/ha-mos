"""VM power switch for mos, controlling ``/vm/machines/{name}/start`` and ``/stop``.

Mirrors the LXC container power switch (switch/lxc.py): turning it on/off
actually starts or stops the VM on the MOS server, and it doubles as the
VM's running-state indicator (see binary_sensor/vm.py, which deliberately
does not duplicate this).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.mos.api import MOSApiClientError
from custom_components.mos.const import LOGGER
from custom_components.mos.entity import MOSEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_machine(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a VM by name."""
    machines: list[dict[str, Any]] = coordinator.data.get("vm_machines") or []
    return next((machine for machine in machines if machine.get("name") == name), None)


ENTITY_DESCRIPTION = SwitchEntityDescription(
    key="power",
    translation_key="vm_power",
    icon="mdi:power",
)


class MOSVmMachineSwitch(SwitchEntity, MOSEntity):
    """Switch that starts/stops a single VM on the MOS server."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the VM power switch."""
        self._machine_name = name
        super().__init__(
            coordinator,
            ENTITY_DESCRIPTION,
            unique_id=f"{entry_id}_vm_{name}_{ENTITY_DESCRIPTION.key}",
            container_device=(f"vm_{name}", f"VM {name}"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the VM is currently running."""
        if not self.coordinator.last_update_success:
            return None
        machine = _find_machine(self.coordinator, self._machine_name)
        if machine is None:
            return None
        return machine.get("state") == "running"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the VM on the MOS server."""
        try:
            await self.coordinator.async_start_vm_machine(self._machine_name)
        except MOSApiClientError as exception:
            LOGGER.warning("Failed to start VM %s: %s", self._machine_name, exception)
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="vm_start_failed",
                translation_placeholders={"name": self._machine_name},
            ) from exception

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the VM on the MOS server."""
        try:
            await self.coordinator.async_stop_vm_machine(self._machine_name)
        except MOSApiClientError as exception:
            LOGGER.warning("Failed to stop VM %s: %s", self._machine_name, exception)
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="vm_stop_failed",
                translation_placeholders={"name": self._machine_name},
            ) from exception


def build_vm_machine_switches(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSVmMachineSwitch]:
    """Build the switch entity for a single VM (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSVmMachineSwitch(coordinator, name, entry_id)]
