"""Tests for the registry cleanup of entities the integration no longer creates."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from custom_components.mos.const import DOMAIN
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant


async def test_a_retired_entity_is_removed_from_the_registry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A registry entry left over from a removed sensor is deleted rather than left unavailable.

    Home Assistant publishes an ``unavailable`` state for every registered entity
    with no object behind it, so without this the sensor would sit on its device
    page forever with no way to tell it from a broken one.
    """
    mock_config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    stale = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{mock_config_entry.entry_id}_docker_PushBits_memory_percent",
        config_entry=mock_config_entry,
        suggested_object_id="sirius_docker_pushbits_memory_percent",
    )
    kept = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{mock_config_entry.entry_id}_docker_PushBits_memory_usage",
        config_entry=mock_config_entry,
        suggested_object_id="sirius_docker_pushbits_memory_usage",
    )

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert registry.async_get(stale.entity_id) is None
    assert registry.async_get(kept.entity_id) is not None
