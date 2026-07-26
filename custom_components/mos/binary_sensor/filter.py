"""Filter maintenance binary sensor for mos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.entity import MOSEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="filter_replacement",
        translation_key="filter_replacement",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:air-filter",
        has_entity_name=True,
    ),
)


class MOSFilterSensor(BinarySensorEntity, MOSEntity):
    """Filter replacement binary sensor class."""

    def __init__(
        self,
        coordinator: MOSDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if filter needs replacement."""
        # Simulate filter replacement needed when user ID is divisible by 3
        # In production: check actual filter life from API data
        user_id = self.coordinator.data.get("userId", 0)
        return user_id % 3 == 0

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        """Return additional state attributes."""
        # Calculate simulated filter life percentage
        user_id = self.coordinator.data.get("userId", 0)
        filter_life = 100 - (user_id % 100)

        return {
            "filter_life_remaining": f"{filter_life}%",
            "estimated_days_remaining": max(0, filter_life // 2),  # Rough estimate
        }
