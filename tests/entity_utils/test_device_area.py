"""Tests for container devices following the server device's area."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er


def _server_device(hass: HomeAssistant, entry: MockConfigEntry) -> dr.DeviceEntry:
    """Return the entry's server device - the one every other device hangs off."""
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None
    return device


def _container_devices(hass: HomeAssistant, entry: MockConfigEntry) -> list[dr.DeviceEntry]:
    """Return every device of the entry except the server itself."""
    server = _server_device(hass, entry)
    device_registry = dr.async_get(hass)
    return [d for d in dr.async_entries_for_config_entry(device_registry, entry.entry_id) if d.id != server.id]


async def test_container_devices_follow_the_server_into_its_area(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Setting the area on the server device is enough for the whole server.

    Home Assistant has no inheritance of its own: ``via_device`` links these
    devices for display and nothing else, so a MOS server otherwise has to be
    filed into a room a dozen times over - once in the setup dialog for each
    pool, disk, container, VM and the UPS.
    """
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    office = area_registry.async_create("Office")

    containers = _container_devices(hass, setup_integration)
    assert containers
    assert all(device.area_id is None for device in containers)

    device_registry.async_update_device(_server_device(hass, setup_integration).id, area_id=office.id)
    await hass.async_block_till_done()

    assert all(device_registry.async_get(device.id).area_id == office.id for device in containers)


async def test_a_device_placed_elsewhere_on_purpose_stays_there(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Only devices that were where the server was are moved along with it.

    Without this the mechanism would be a bulk overwrite, and every later change
    to the server's area would quietly undo the user's own filing. A disk shelf
    standing in another room is a real arrangement, not an oversight.
    """
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    office = area_registry.async_create("Office")
    basement = area_registry.async_create("Basement")

    filed_by_hand = entity_registry.async_get("binary_sensor.sirius_pool_test1_problem").device_id
    device_registry.async_update_device(filed_by_hand, area_id=basement.id)
    await hass.async_block_till_done()

    device_registry.async_update_device(_server_device(hass, setup_integration).id, area_id=office.id)
    await hass.async_block_till_done()

    assert device_registry.async_get(filed_by_hand).area_id == basement.id
    # Everything that was following along still follows.
    following = entity_registry.async_get("binary_sensor.sirius_pool_test2_problem").device_id
    assert device_registry.async_get(following).area_id == office.id


async def test_moving_the_server_again_takes_the_followers_with_it(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The rule is "was where the server was", not "had no area", so it keeps working.

    A one-shot "fill in the blanks" would move everything the first time and
    never again, leaving the second move to be done by hand twelve times over.
    """
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    office = area_registry.async_create("Office")
    study = area_registry.async_create("Study")
    server_id = _server_device(hass, setup_integration).id
    containers = _container_devices(hass, setup_integration)

    device_registry.async_update_device(server_id, area_id=office.id)
    await hass.async_block_till_done()
    device_registry.async_update_device(server_id, area_id=study.id)
    await hass.async_block_till_done()

    assert all(device_registry.async_get(device.id).area_id == study.id for device in containers)


async def test_clearing_the_server_area_clears_the_followers(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Taking the server out of a room takes its devices out too, for the same reason."""
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    office = area_registry.async_create("Office")
    server_id = _server_device(hass, setup_integration).id
    containers = _container_devices(hass, setup_integration)

    device_registry.async_update_device(server_id, area_id=office.id)
    await hass.async_block_till_done()
    device_registry.async_update_device(server_id, area_id=None)
    await hass.async_block_till_done()

    assert all(device_registry.async_get(device.id).area_id is None for device in containers)


async def test_a_device_appearing_later_starts_in_the_servers_area(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
    mock_pools: list[dict[str, Any]],
) -> None:
    """A pool created after the room was chosen lands in it rather than nowhere.

    This is the half the "follow the server" rule cannot cover: nothing about
    the server changed, so there is no move to follow. Without it, every pool,
    container or VM added months later would be the one device sitting outside
    the room the rest of the server is in.
    """
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        area_registry = ar.async_get(hass)
        device_registry = dr.async_get(hass)
        office = area_registry.async_create("Office")
        device_registry.async_update_device(_server_device(hass, mock_config_entry).id, area_id=office.id)
        await hass.async_block_till_done()

        mock_client.async_get_pools.return_value = [
            *mock_pools,
            {**mock_pools[0], "id": 3, "name": "Later"},
        ]
        await mock_config_entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()

    new_pool_id = er.async_get(hass).async_get("binary_sensor.sirius_pool_later_problem").device_id
    assert device_registry.async_get(new_pool_id).area_id == office.id


async def test_other_integrations_devices_are_left_alone(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The listener sees every device in Home Assistant, so it has to be sure whose it is."""
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    office = area_registry.async_create("Office")

    other_entry = MockConfigEntry(domain="other")
    other_entry.add_to_hass(hass)
    stranger = device_registry.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={("other", "stranger")},
    )

    device_registry.async_update_device(_server_device(hass, setup_integration).id, area_id=office.id)
    await hass.async_block_till_done()

    assert device_registry.async_get(stranger.id).area_id is None
