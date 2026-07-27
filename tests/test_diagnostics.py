"""Tests for the config entry diagnostics."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import CONF_API_TOKEN
from custom_components.mos.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant


async def test_api_token_is_redacted(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The API token never appears in diagnostics output."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert diagnostics["entry"]["data"][CONF_API_TOKEN] == "**REDACTED**"
    assert "test-token" not in str(diagnostics)


async def test_data_sample_includes_all_resources(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_services: dict,
    mock_disks: list[dict],
    mock_pools: list[dict],
) -> None:
    """The data sample surfaces services/disks/pools alongside osinfo."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    data_sample = diagnostics["data_sample"]
    assert data_sample["services"] == mock_services
    assert data_sample["disks"] == mock_disks
    assert data_sample["pools"] == mock_pools
    assert data_sample["osinfo"]["hostname"] == "sirius"


async def test_devices_and_entities_are_reported(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The single server device and its entity count are reported."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert len(diagnostics["devices"]) == 1
    assert diagnostics["devices"][0]["entity_count"] > 0
