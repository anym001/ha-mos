"""Tests that an existing installation keeps its devices across the via-link change."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

if TYPE_CHECKING:
    from unittest.mock import AsyncMock


async def test_existing_devices_keep_their_identity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A registry written by an earlier version survives setup unchanged.

    The server device, one container hanging off it and that container's entity
    are seeded as a running installation holds them, so their registry ids,
    entity id and via link have to come back identical rather than as a second
    set of devices.
    """
    mock_config_entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    server = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, mock_config_entry.entry_id)},
        name="Sirius",
        manufacturer="MOS",
        model="0.5.0-stable",
        sw_version="20260705-1111",
    )
    container = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_docker_PushBits")},
        name="Sirius Docker PushBits",
        manufacturer="MOS",
        via_device_id=server.id,
    )
    seeded_entity_id = entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"{mock_config_entry.entry_id}_docker_PushBits_autostart",
        device_id=container.id,
        suggested_object_id="sirius_docker_pushbits_autostart",
    ).entity_id

    assert container.via_device_id == server.id

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    server_after = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    container_after = device_registry.async_get_device_by_identifier(
        (DOMAIN, f"{mock_config_entry.entry_id}_docker_PushBits"), mock_config_entry.entry_id
    )

    assert server_after is not None
    assert container_after is not None
    assert server_after.id == server.id
    assert container_after.id == container.id
    assert container_after.name == "Sirius Docker PushBits"
    assert container_after.via_device_id == server.id
    assert entity_registry.async_get(seeded_entity_id) is not None
    assert hass.states.get(seeded_entity_id) is not None
