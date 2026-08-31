"""Docker container sensors for mos, sourced from ``/docker/mos/containers``.

The state sensor is the one a dashboard card is built around: it carries the
running state as its value, the container's descriptive fields as attributes,
and the MOS template's icon as its entity picture, so a card can render an
icon/name/state/link row from a single entity.


Containers are a dynamic list (created/removed at runtime), so their
entities are added/removed via ``async_setup_dynamic_entities`` rather than a
static ENTITY_DESCRIPTIONS tuple. Each container gets its own device (linked
back to the main server device via ``via_device``), so it can be individually
enabled/disabled from its device page instead of cluttering the server
device's entity list (e.g. ``sensor.sirius_docker_pushbits_installed_version``;
the server name and "docker" category keep things unique across multiple
servers and disambiguate from an LXC container of the same name).

CPU and memory come from a second, optional group (``STATS_ENTITY_DESCRIPTIONS``)
that is only created when the Docker stats option is on. Unlike every other
sensor here, each of those costs a request per poll for the container it belongs
to, so they announce themselves to the coordinator and stop being fetched as
soon as the user disables them. They also read unknown for one cycle after a
start or reload - see ``_async_add_docker_stats``.

Note: the ``local``/``remote`` fields are image tags when the container uses
one (e.g. ``1.20.2``), but fall back to a full image digest (``sha256:...``)
when it doesn't - both are valid string states, just not always human-scale.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import DOCKER_IMAGE_LABEL_ATTRIBUTES, MOSDeviceKind
from custom_components.mos.coordinator.docker_stats import DockerStatsContext
from custom_components.mos.entity import MOSEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.typing import StateType

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator

# Docker's own container states, all of which can appear in the engine payload.
# Listed in full rather than just the common three: a state missing from an enum
# sensor's options is an error at runtime, and "removing" or "dead" showing up is
# exactly when someone is looking at the dashboard.
DOCKER_STATES = ["created", "restarting", "running", "removing", "paused", "exited", "dead"]


def _find_container(coordinator: MOSDataUpdateCoordinator, name: str) -> dict[str, Any] | None:
    """Look up the current payload for a Docker container by name."""
    containers: list[dict[str, Any]] = coordinator.data.get("docker_containers") or []
    return next((container for container in containers if container.get("name") == name), None)


def _state_attributes(container: dict[str, Any]) -> dict[str, Any]:
    """
    Collect the descriptive fields a dashboard card needs alongside the state.

    Attributes rather than entities on purpose: these are strings that describe
    the container instead of measurements that change, and one card row wants
    all of them from a single entity. Empty ones are left out so a container
    without a web interface does not show a blank link.

    Returns:
        The attributes to expose, with unset ones omitted.

    """
    labels: dict[str, Any] = container.get("labels") or {}
    attributes = {
        "web_ui_url": container.get("web_ui_url"),
        # MOS's own ``repo`` rather than the engine's ``Image``: the two agree on
        # every container observed, and this one comes from the container list,
        # so it survives an engine proxy outage without relying on carry-forward.
        "repo": container.get("repo"),
        "network_mode": container.get("network_mode"),
        **{attribute: labels.get(label) for label, attribute in DOCKER_IMAGE_LABEL_ATTRIBUTES.items()},
    }
    return {key: value for key, value in attributes.items() if value}


@dataclass(frozen=True, kw_only=True)
class MOSDockerContainerSensorEntityDescription(SensorEntityDescription):
    """Describe a MOS Docker container sensor, including how to derive its value from a container payload."""

    value_fn: Callable[[dict[str, Any]], StateType]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    picture_fn: Callable[[dict[str, Any]], str | None] | None = None
    # Resources this sensor reads beyond the one the dynamic helper syncs it
    # against, so it can report itself unavailable when they go stale. The
    # running state comes from the Docker Engine proxy, which is a separate
    # endpoint from the container list and can fail on its own.
    extra_resource_keys: frozenset[str] = frozenset()
    # Whether this sensor's value costs a request of its own. Such a sensor
    # registers a ``DockerStatsContext``, which is how the coordinator learns
    # that this container is worth measuring; see ``_async_add_docker_stats``.
    needs_stats: bool = False


ENTITY_DESCRIPTIONS: tuple[MOSDockerContainerSensorEntityDescription, ...] = (
    MOSDockerContainerSensorEntityDescription(
        key="state",
        translation_key="docker_state",
        device_class=SensorDeviceClass.ENUM,
        options=DOCKER_STATES,
        value_fn=lambda container: container.get("state"),
        attributes_fn=_state_attributes,
        picture_fn=lambda container: container.get("icon_url"),
        extra_resource_keys=frozenset({"docker_engine_containers"}),
    ),
    MOSDockerContainerSensorEntityDescription(
        key="installed_version",
        translation_key="docker_installed_version",
        value_fn=lambda container: container.get("local"),
    ),
    MOSDockerContainerSensorEntityDescription(
        key="latest_version",
        translation_key="docker_latest_version",
        value_fn=lambda container: container.get("remote"),
    ),
)

# A separate tuple because these carry ``needs_stats``, which registers the
# coordinator context deciding which containers the Engine fallback measures.
#
# ``cpu_usage`` and ``memory_usage`` deliberately mirror their LXC and VM
# counterparts down to the key, device class and state class (see
# ``sensor/lxc.py``), so a dashboard covering all three kinds of guest reads the
# same fields from each. Only the suggested unit differs: containers are a
# mebibyte-scale thing where a VM is a gibibyte-scale one.
STATS_ENTITY_DESCRIPTIONS: tuple[MOSDockerContainerSensorEntityDescription, ...] = (
    MOSDockerContainerSensorEntityDescription(
        key="cpu_usage",
        translation_key="docker_cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda container: container.get("stats_cpu_percent"),
        needs_stats=True,
    ),
    MOSDockerContainerSensorEntityDescription(
        key="memory_usage",
        translation_key="docker_memory_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda container: container.get("stats_memory_bytes"),
        needs_stats=True,
    ),
)


class MOSDockerContainerSensor(SensorEntity, MOSEntity):
    """Sensor for a single Docker container, backed by a value function."""

    entity_description: MOSDockerContainerSensorEntityDescription

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: MOSDockerContainerSensorEntityDescription,
        name: str,
        entry_id: str,
        device_configuration_url: str | None = None,
    ) -> None:
        """Initialize the Docker container sensor."""
        self._container_name = name
        super().__init__(
            coordinator,
            entity_description,
            unique_id=f"{entry_id}_docker_{name}_{entity_description.key}",
            container_device=(f"docker_{name}", f"Docker {name}"),
            device_kind=MOSDeviceKind.DOCKER,
            device_configuration_url=device_configuration_url,
            # Only a stats sensor announces itself to the coordinator: it is the
            # one whose value is not already in the poll. Home Assistant drops
            # the context when the entity is removed, so disabling the sensor is
            # what stops its container from being measured.
            coordinator_context=DockerStatsContext(name) if entity_description.needs_stats else None,
        )
        self.resource_keys |= entity_description.extra_resource_keys

    @property
    def native_value(self) -> StateType:
        """Return the value derived from the current container payload."""
        if not self.coordinator.last_update_success:
            return None
        container = _find_container(self.coordinator, self._container_name)
        if container is None:
            return None
        return self.entity_description.value_fn(container)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """
        Return the descriptive attributes for this container, if the sensor has any.

        Returns:
            The attributes, or ``None`` for sensors that define none.

        """
        if self.entity_description.attributes_fn is None:
            return None
        container = _find_container(self.coordinator, self._container_name)
        if container is None:
            return None
        return self.entity_description.attributes_fn(container)

    @property
    def entity_picture(self) -> str | None:
        """
        Return the container's icon URL, so cards show it without templating.

        The URL points wherever the MOS template does, which is normally a
        public CDN - it is loaded by the browser rendering the dashboard, not by
        Home Assistant, and stays blank if that browser has no internet access.

        Returns:
            The icon URL, or ``None`` when the container has no usable one.

        """
        if self.entity_description.picture_fn is None:
            return None
        container = _find_container(self.coordinator, self._container_name)
        if container is None:
            return None
        return self.entity_description.picture_fn(container)


def build_docker_container_sensors(coordinator: MOSDataUpdateCoordinator, name: str) -> list[MOSDockerContainerSensor]:
    """Build all sensor entities for a single Docker container (entity_factory for the dynamic helper)."""
    entry_id = coordinator.config_entry.entry_id
    # Passed to every sensor of this container rather than to one chosen sensor:
    # they all describe the same device, so they all report the same URL for it
    # and the device registry sees no conflict.
    container = _find_container(coordinator, name) or {}
    device_configuration_url = container.get("web_ui_url")
    return [
        MOSDockerContainerSensor(coordinator, description, name, entry_id, device_configuration_url)
        for description in (*ENTITY_DESCRIPTIONS, *STATS_ENTITY_DESCRIPTIONS)
    ]
