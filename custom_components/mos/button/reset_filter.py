"""Reset filter button for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.api import MOSApiClientError
from custom_components.mos.const import LOGGER
from custom_components.mos.entity import MOSEntity
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="reset_filter",
        translation_key="reset_filter",
        icon="mdi:restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        has_entity_name=True,
    ),
)


class MOSButton(ButtonEntity, MOSEntity):
    """Reset filter button class."""

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entity_description)

    async def async_press(self) -> None:
        """
        Handle the button press.

        This simulates resetting the filter timer. In a real integration,
        this would send an API command to reset the device's filter counter.

        Demo: This also affects the filter_life sensor - watch it jump to 100%!
        """
        try:
            # In production: Send reset command to device
            # await self.coordinator.config_entry.runtime_data.client.async_reset_filter()

            # For demo: Store reset flag in coordinator data
            # The filter_life sensor will read this and show 100%
            self.coordinator.data["demo_filter_reset"] = True

            # Request a coordinator refresh - this simulates the real flow:
            # 1. API call to device (commented out above)
            # 2. Coordinator fetches updated data from device
            # 3. All entities get updated with fresh data
            await self.coordinator.async_request_refresh()

            LOGGER.info("Filter timer reset successfully")

        except MOSApiClientError as exception:
            msg = f"Failed to reset filter: {exception}"
            raise HomeAssistantError(msg) from exception
