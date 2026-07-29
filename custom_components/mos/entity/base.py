"""
Base entity class for mos.

This module provides the base entity class that all integration entities inherit from.
It handles common functionality like device info, unique IDs, and coordinator integration.

For more information on entities:
https://developers.home-assistant.io/docs/core/entity
https://developers.home-assistant.io/docs/core/entity/index/#common-properties
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import ATTRIBUTION, DEFAULT_SSL
from custom_components.mos.coordinator import MOSDataUpdateCoordinator
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class MOSEntity(CoordinatorEntity[MOSDataUpdateCoordinator]):
    """
    Base entity class for mos.

    All entities in this integration inherit from this class, which provides:
    - Automatic coordinator updates
    - Device info management
    - Unique ID generation
    - Attribution and naming conventions

    For more information:
    https://developers.home-assistant.io/docs/core/entity
    https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    # Coordinator data keys this entity reads. When one of them has been failing
    # long enough to go stale, the entity reports itself unavailable instead of
    # serving values that stopped updating (see ``available``).
    #
    # Entities backed by an always-fetched resource (osinfo, system_load) leave
    # this empty: a failure there takes the whole poll down, which already makes
    # every entity unavailable via ``last_update_success``.
    #
    # Set automatically for dynamically managed entities by
    # ``async_setup_dynamic_entities``, which knows the data key it syncs
    # against; entities created directly declare it themselves. A subclass may
    # declare additional keys, which the helper unions with rather than replaces
    # - the Docker power switch needs this, since its running state comes from
    # ``docker_engine_containers`` while its existence comes from
    # ``docker_containers``.
    resource_keys: frozenset[str] = frozenset()

    @property
    def available(self) -> bool:
        """
        Whether the entity currently has meaningful data.

        Unavailable when the last poll failed outright (inherited behaviour), and
        additionally when one of the resources backing this entity has gone
        stale: its data is still being retained, but it stopped being current
        long enough ago that presenting it as a live reading would be
        misleading. Recovers on its own as soon as the resource answers again.
        """
        return super().available and not (self.resource_keys & self.coordinator.stale_resources)

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: EntityDescription,
        *,
        unique_id: str | None = None,
        container_device: tuple[str, str] | None = None,
    ) -> None:
        """
        Initialize the base entity.

        Args:
            coordinator: The data update coordinator for this entity.
            entity_description: The entity description defining characteristics.
            unique_id: Optional unique_id override, for entities whose identity
                includes more than just the entry and description key (e.g. a
                per-disk or per-pool suffix). Defaults to ``{entry_id}_{key}``.
            container_device: Optional ``(device_key, display_name)`` for
                entities that get their own device instead of the shared
                server device (disks, pools, LXC/Docker containers, VMs -
                items that can be numerous and are individually
                enabled/disabled via the standard HA device page rather than
                cluttering the server device). The device is linked back to
                the server device via ``via_device``, and its name is
                prefixed with the server name so it stays unique/identifiable
                across multiple configured MOS servers.

        """
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry = coordinator.config_entry
        # Include entity description key in unique_id to support multiple entities
        self._attr_unique_id = unique_id or f"{entry.entry_id}_{entity_description.key}"

        if container_device is not None:
            device_key, device_name = container_device
            # Prefix with the server name so container devices/entities stay unique and
            # identifiable when more than one MOS server is configured (e.g. two servers
            # both happen to run a container named "database").
            self._attr_device_info = DeviceInfo(
                identifiers={(entry.domain, f"{entry.entry_id}_{device_key}")},
                name=f"{entry.title} {device_name}" if entry.title else device_name,
                manufacturer="MOS",
                via_device=(entry.domain, entry.entry_id),
            )
            return

        osinfo: dict = (coordinator.data or {}).get("osinfo", {})
        mos: dict = osinfo.get("mos", {})

        host = entry.data.get(CONF_HOST)
        scheme = "https" if entry.data.get(CONF_SSL, DEFAULT_SSL) else "http"
        port = entry.data.get(CONF_PORT)
        configuration_url = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    entry.domain,
                    entry.entry_id,
                ),
            },
            name=entry.title or osinfo.get("hostname"),
            manufacturer="MOS",
            model=mos.get("version"),
            sw_version=mos.get("build"),
            configuration_url=configuration_url if host else None,
        )
