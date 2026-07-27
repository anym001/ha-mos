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
        *,
        unique_id: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the base entity.

        Args:
            coordinator: The data update coordinator for this entity.
            entity_description: The entity description defining characteristics.
            unique_id: Optional unique_id override, for entities whose identity
                includes more than just the entry and description key (e.g. a
                per-disk or per-pool suffix). Defaults to ``{entry_id}_{key}``.
            translation_placeholders: Optional placeholders for this entity's
                translated name, e.g. ``{"pool_name": "Test1"}``. Used by
                per-item entities (disks, pools) that share the main server
                device and need the item's own name folded into the entity
                name/entity_id to stay unique and readable.

        """
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry = coordinator.config_entry
        # Include entity description key in unique_id to support multiple entities
        self._attr_unique_id = unique_id or f"{entry.entry_id}_{entity_description.key}"
        if translation_placeholders is not None:
            self._attr_translation_placeholders = translation_placeholders

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
