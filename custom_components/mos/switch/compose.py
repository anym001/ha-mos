"""Compose stack power switch for mos, controlling ``/docker/mos/compose/stacks/{name}/start`` and ``/stop``.

Unlike switch/docker.py, this drives purpose-built MOS endpoints rather than the
raw Docker Engine proxy - and it acts on the whole stack, because MOS exposes no
per-service start or stop. Starting the switch starts every service in the
stack; stopping it stops all of them.

The running state comes from the stack list's own ``running`` flag, so this
switch needs no second resource to know where it stands.
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


def _find_stack(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Compose stack by name."""
    stacks: list[dict[str, Any]] = coordinator.data.get("compose_stacks") or []
    return next((stack for stack in stacks if stack.get("name") == name), None)


ENTITY_DESCRIPTION = SwitchEntityDescription(
    key="power",
    translation_key="compose_power",
)


class MOSComposeStackSwitch(SwitchEntity, MOSEntity):
    """Switch that starts/stops a whole Compose stack on the MOS server."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the Compose stack power switch."""
        self._stack_name = name
        super().__init__(
            coordinator,
            ENTITY_DESCRIPTION,
            unique_id=f"{entry_id}_compose_{name}_{ENTITY_DESCRIPTION.key}",
            container_device=(f"compose_{name}", f"Compose {name}"),
            device_kind=MOSDeviceKind.COMPOSE,
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the stack is currently running."""
        if not self.coordinator.last_update_success:
            return None
        stack = _find_stack(self.coordinator, self._stack_name)
        if stack is None:
            return None
        running = stack.get("running")
        return running if isinstance(running, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start every service in the stack on the MOS server."""
        try:
            await self.coordinator.async_start_compose_stack(self._stack_name)
        except MOSApiClientError as exception:
            LOGGER.warning("Failed to start Compose stack %s: %s", self._stack_name, exception)
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="compose_start_failed",
                translation_placeholders={"name": self._stack_name},
            ) from exception

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop every service in the stack on the MOS server."""
        try:
            await self.coordinator.async_stop_compose_stack(self._stack_name)
        except MOSApiClientError as exception:
            LOGGER.warning("Failed to stop Compose stack %s: %s", self._stack_name, exception)
            raise HomeAssistantError(
                translation_domain="mos",
                translation_key="compose_stop_failed",
                translation_placeholders={"name": self._stack_name},
            ) from exception


def build_compose_stack_switches(
    coordinator: MOSDataUpdateCoordinator,
    name: str,
) -> list[MOSComposeStackSwitch]:
    """Build the switch entity for a single Compose stack (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [MOSComposeStackSwitch(coordinator, name, entry_id)]
