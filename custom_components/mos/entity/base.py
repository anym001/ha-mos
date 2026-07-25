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

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """
        Initialize the base entity.

        Args:
            coordinator: The data update coordinator for this entity.
            entity_description: The entity description defining characteristics.

        """
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry = coordinator.config_entry
        # Include entity description key in unique_id to support multiple entities
        self._attr_unique_id = f"{entry.entry_id}_{entity_description.key}"

        osinfo: dict = (coordinator.data or {}).get("osinfo", {})
        cpu: dict = osinfo.get("cpu", {})
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
            name=osinfo.get("hostname") or entry.title,
            manufacturer="MOS",
            model=cpu.get("brand"),
            sw_version=mos.get("version"),
            configuration_url=configuration_url if host else None,
        )
