"""Docker Compose stack sensors for mos, sourced from ``/docker/mos/compose/stacks``.

Built to mirror sensor/docker.py, because a card that renders one should render
the other: the state sensor carries the running state as its value, the stack's
descriptive fields as attributes, and its icon as the entity picture.

Where a stack genuinely differs, so does this module. There are no version
sensors - MOS tracks images per container and a stack has several, so it reports
no installed/latest pair to put in one. What a stack has instead is its two
counters and the images its services run, both derived from the member
containers in the raw Docker Engine list (see coordinator/compose.py).

CPU and memory come from a second, optional group (``STATS_ENTITY_DESCRIPTIONS``)
behind an option of its own. Docker measures one container at a time, so a
stack's figures are summed over its running services and cost a request each on
every poll - a bill that scales with the size of the stack rather than with the
number of devices, which is why it is not folded into the Docker stats option.
Like their Docker counterparts they read unknown for one cycle after a start or
reload - see ``_async_add_compose_stats``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import MOSDeviceKind
from custom_components.mos.coordinator.compose import ComposeStatsContext
from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator

# A stack has no equivalent of Docker's seven container states: MOS reports one
# boolean for the whole stack, derived from ``docker compose ls``. A stack whose
# services disagree - one up, one crashed - still reads as running here, which is
# what the running/total counter pair is for.
COMPOSE_STATES = ["running", "stopped"]


def _find_stack(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Compose stack by name."""
    stacks: list[dict[str, Any]] = coordinator.data.get("compose_stacks") or []
    return next((stack for stack in stacks if stack.get("name") == name), None)


def _state(stack: dict[str, Any]) -> StateType:
    """
    Map the stack's running flag onto the enum the sensor declares.

    Returns:
        ``"running"`` or ``"stopped"``, or ``None`` while the flag is missing.

    """
    running = stack.get("running")
    if not isinstance(running, bool):
        return None
    return "running" if running else "stopped"


def _state_attributes(stack: dict[str, Any]) -> dict[str, Any]:
    """
    Collect the descriptive fields a dashboard card needs alongside the state.

    ``services`` and ``containers`` are the pair that makes a stack legible: the
    first is what the compose file declares, the second what Docker actually
    named them, and neither is derivable from the other. ``images`` is what those
    containers are running, which the stack list does not report at all.

    Returns:
        The attributes to expose, with unset ones omitted.

    """
    attributes = {
        "web_ui_url": stack.get("web_ui_url"),
        "services": stack.get("services"),
        "containers": stack.get("containers"),
        # The images actually in use, deduplicated: several services of one
        # stack routinely share an image, and listing it twice says nothing.
        "images": stack.get("images"),
    }
    return {key: value for key, value in attributes.items() if value}


@dataclass(frozen=True, kw_only=True)
class MOSComposeStackSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS Compose stack sensor, including how to derive its value from a stack payload."""

    value_fn: Callable[[dict[str, Any]], StateType]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    picture_fn: Callable[[dict[str, Any]], str | None] | None = None
    # Resources this sensor reads beyond the one the dynamic helper syncs it
    # against, so it can report itself unavailable once they go stale.
    extra_resource_keys: frozenset[str] = frozenset()
    # Whether this sensor's value costs a request per running service. Such a
    # sensor registers a ``ComposeStatsContext``, which is how the coordinator
    # learns that this stack is worth measuring.
    needs_stats: bool = False


ENTITY_DESCRIPTIONS: tuple[MOSComposeStackSensorEntityDescription, ...] = (
    MOSComposeStackSensorEntityDescription(
        key="state",
        translation_key="compose_state",
        device_class=SensorDeviceClass.ENUM,
        options=COMPOSE_STATES,
        value_fn=_state,
        attributes_fn=_state_attributes,
        picture_fn=lambda stack: stack.get("icon_url"),
    ),
    # No state class on either counter. Both are a property of how the stack is
    # defined rather than a measurement over time, and a statistic of "how many
    # containers this stack has" is noise in the recorder. Neither is diagnostic
    # either: this integration reserves that category for the problem and
    # update flags (see tests/test_entity_categories.py).
    MOSComposeStackSensorEntityDescription(
        key="running_containers",
        translation_key="compose_running_containers",
        value_fn=lambda stack: stack.get("running_containers"),
        # Counted from the member containers in the engine proxy, which is a
        # different endpoint from the stack list this sensor is synced against.
        extra_resource_keys=frozenset({"docker_engine_containers"}),
    ),
    MOSComposeStackSensorEntityDescription(
        key="container_count",
        translation_key="compose_container_count",
        value_fn=lambda stack: stack.get("container_count"),
    ),
)

# A separate tuple because these carry ``needs_stats``, which registers the
# coordinator context deciding which stacks the Engine fallback measures.
#
# The keys, device classes and state classes mirror the Docker container stats
# down to the suggested unit, so a dashboard covering both reads the same fields
# from a stack as from a container.
STATS_ENTITY_DESCRIPTIONS: tuple[MOSComposeStackSensorEntityDescription, ...] = (
    MOSComposeStackSensorEntityDescription(
        key="cpu_usage",
        translation_key="compose_cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stack: stack.get("stats_cpu_percent"),
        needs_stats=True,
    ),
    MOSComposeStackSensorEntityDescription(
        key="memory_usage",
        translation_key="compose_memory_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda stack: stack.get("stats_memory_bytes"),
        needs_stats=True,
    ),
)


class MOSComposeStackSensor(SensorEntity, MOSEntity):
    """Sensor for a single Compose stack, backed by a value function."""

    entity_description: MOSComposeStackSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSComposeStackSensorEntityDescription,
        name: str,
        entry_id: str,
        device_configuration_url: str | None = None,
    ) -> None:
        """Initialize the Compose stack sensor."""
        self._stack_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_compose_{name}_{entity_description.key}",
            container_device=(f"compose_{name}", f"Compose {name}"),
            device_kind=MOSDeviceKind.COMPOSE,
            device_configuration_url=device_configuration_url,
            # Only a stats sensor announces itself to the coordinator: it is the
            # one whose value is not already in the poll. Home Assistant drops
            # the context when the entity is removed, so disabling the sensor is
            # what stops its stack from being measured.
            coordinator_context=ComposeStatsContext(name) if entity_description.needs_stats else None,
        )
        self.resource_keys |= entity_description.extra_resource_keys

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current stack payload."""
        if not self.coordinator.last_update_success:
            return None
        stack = _find_stack(self.coordinator, self._stack_name)
        if stack is None:
            return None
        return self.entity_description.value_fn(stack)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """
        Return the descriptive attributes for this stack, if the sensor has any.

        Returns:
            The attributes, or ``None`` for sensors that define none.

        """
        if self.entity_description.attributes_fn is None:
            return None
        stack = _find_stack(self.coordinator, self._stack_name)
        if stack is None:
            return None
        return self.entity_description.attributes_fn(stack)

    @property
    def entity_picture(self) -> str | None:
        """
        Return the stack's icon URL, so cards show it without templating.

        Returns:
            The icon URL, or ``None`` when the stack has no usable one.

        """
        if self.entity_description.picture_fn is None:
            return None
        stack = _find_stack(self.coordinator, self._stack_name)
        if stack is None:
            return None
        return self.entity_description.picture_fn(stack)


def build_compose_stack_sensors(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSComposeStackSensor]:
    """Build all sensor entities for a single Compose stack (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    stack = _find_stack(coordinator, name) or {}
    device_configuration_url = stack.get("web_ui_url")
    return [
        MOSComposeStackSensor(coordinator, description, name, entry_id, device_configuration_url)
        for description in (*ENTITY_DESCRIPTIONS, *STATS_ENTITY_DESCRIPTIONS)
    ]
