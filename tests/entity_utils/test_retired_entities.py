"""Tests for the registry cleanup of entities the integration no longer creates."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry as _MockConfigEntry

from custom_components.mos.const import CONF_API_TOKEN, DOMAIN
from custom_components.mos.entity_utils import async_remove_retired_entities
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant

SURVIVING_KEYS = (
    "docker_PushBits_memory_usage",
    "compose_hatest_memory_usage",
    "lxc_webserver_memory_usage",
    "vm_test_memory_usage",
    "memory_used",
    "memory_total",
    "memory_docker",
)


def _register(
    registry: er.EntityRegistry,
    entry: MockConfigEntry,
    unique_suffix: str,
    platform: str = DOMAIN,
) -> er.RegistryEntry:
    """Put one entity in the registry as if a previous version had created it."""
    return registry.async_get_or_create(
        "sensor",
        platform,
        f"{entry.entry_id}_{unique_suffix}",
        config_entry=entry,
    )


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
    stale = _register(registry, mock_config_entry, "docker_PushBits_memory_percent")
    kept = _register(registry, mock_config_entry, "docker_PushBits_memory_usage")

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert registry.async_get(stale.entity_id) is None
    assert registry.async_get(kept.entity_id) is not None


async def test_the_sweep_touches_only_the_entry_it_was_given(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A second server, and any other integration, keep their entities.

    The unique ID suffix is only unique within one config entry, so the sweep is
    scoped to the entry being set up. Called directly rather than through setup,
    because setting up one entry of a domain sets up every entry of it - and each
    would then clean up after itself, hiding whether the scoping works.
    """
    mock_config_entry.add_to_hass(hass)
    other_entry = _MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "10.0.1.31", CONF_API_TOKEN: "other", CONF_NAME: "Vesta"},
        entry_id="other_mos_entry",
    )
    other_entry.add_to_hass(hass)

    registry = er.async_get(hass)
    mine = _register(registry, mock_config_entry, "docker_PushBits_memory_percent")
    theirs = _register(registry, other_entry, "docker_PushBits_memory_percent")
    outsider = _register(registry, other_entry, "whatever_memory_percent", platform="some_other_integration")

    async_remove_retired_entities(hass, mock_config_entry.entry_id)

    assert registry.async_get(mine.entity_id) is None
    assert registry.async_get(theirs.entity_id) is not None
    assert registry.async_get(outsider.entity_id) is not None


async def test_every_surviving_memory_key_outlives_the_sweep(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The suffix must not catch any key the integration still creates."""
    mock_config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    survivors = [_register(registry, mock_config_entry, key) for key in SURVIVING_KEYS]

    async_remove_retired_entities(hass, mock_config_entry.entry_id)

    assert all(registry.async_get(entity.entity_id) is not None for entity in survivors)
