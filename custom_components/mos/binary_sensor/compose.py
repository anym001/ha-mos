"""Docker Compose stack binary sensors for mos, sourced from ``/docker/mos/compose/stacks``.

Stacks are a dynamic list, so entities are added/removed via
``async_setup_dynamic_entities`` (see sensor/compose.py for the matching state
and counter sensors, on the same per-stack device).

The health flag has no counterpart in anything MOS reports about a stack: a
healthcheck is a property of a container, so it is derived from the stack's
member containers in the raw Docker Engine list (see coordinator/compose.py).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.entity import MOSEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def _find_stack(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Compose stack by name."""
    stacks: list[dict[str, Any]] = coordinator.data.get("compose_stacks") or []
    return next((stack for stack in stacks if stack.get("name") == name), None)


@dataclass(frozen=True, kw_only=True)
class MOSComposeStackBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a MOS Compose stack binary sensor, including how to derive its value from a stack payload."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    # Resources this sensor reads beyond the one the dynamic helper syncs it
    # against. The update flag comes from the group list, which is a separate
    # endpoint from the stack list and can go stale on its own.
    extra_resource_keys: frozenset[str] = frozenset()


ENTITY_DESCRIPTIONS: tuple[MOSComposeStackBinarySensorEntityDescription, ...] = (
    MOSComposeStackBinarySensorEntityDescription(
        key="healthy",
        translation_key="compose_healthy",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda stack: stack.get("unhealthy"),
        extra_resource_keys=frozenset({"docker_engine_containers"}),
    ),
    MOSComposeStackBinarySensorEntityDescription(
        key="update_available",
        translation_key="compose_update_available",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.UPDATE,
        value_fn=lambda stack: stack.get("update_available"),
        extra_resource_keys=frozenset({"docker_groups"}),
    ),
    MOSComposeStackBinarySensorEntityDescription(
        key="autostart",
        translation_key="compose_autostart",
        value_fn=lambda stack: stack.get("autostart"),
    ),
)


class MOSComposeStackBinarySensor(BinarySensorEntity, MOSEntity):
    """Binary sensor for a single Compose stack, backed by a value function."""

    entity_description: MOSComposeStackBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSComposeStackBinarySensorEntityDescription,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize the Compose stack binary sensor."""
        self._stack_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_compose_{name}_{entity_description.key}",
            container_device=(f"compose_{name}", f"Compose {name}"),
            device_kind=MOSDeviceKind.COMPOSE,
        )
        self.resource_keys |= entity_description.extra_resource_keys

    @property
    def is_on(self) -> bool | None:
        """Return the value derived from the current stack payload."""
        if not self.coordinator.last_update_success:
            return None
        stack = _find_stack(self.coordinator, self._stack_name)
        if stack is None:
            return None
        return self.entity_description.value_fn(stack)


def build_compose_stack_binary_sensors(
    coordinator: MOSDataUpdateCoordinator,
    name: str,
) -> list[MOSComposeStackBinarySensor]:
    """Build the binary sensor entities for a single Compose stack (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    return [
        MOSComposeStackBinarySensor(coordinator, description, name, entry_id) for description in ENTITY_DESCRIPTIONS
    ]
