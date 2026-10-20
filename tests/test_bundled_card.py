"""Tests for serving the bundled MOS NAS Card and announcing it to the frontend."""

from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.mos import bundled_card
from custom_components.mos.const import CARD_URL
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


def _card_urls(hass: HomeAssistant) -> list[str]:
    """Return the extra module URLs that point at the card."""
    return [url for url in hass.data[DATA_EXTRA_MODULE_URL].urls if url.startswith(CARD_URL)]


async def test_the_card_is_announced_with_its_content_hash(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A new bundle changes the URL, so no browser keeps running an old one."""
    digest = sha256(bundled_card.CARD_PATH.read_bytes()).hexdigest()[:16]

    assert _card_urls(hass) == [f"{CARD_URL}?v={digest}"]


async def test_the_bundle_is_served_without_authentication(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """The browser loads the module before it sends any credentials."""
    response = await (await hass_client_no_auth()).get(_card_urls(hass)[0])

    assert response.status == HTTPStatus.OK
    assert await response.read() == bundled_card.CARD_PATH.read_bytes()


async def test_a_second_server_does_not_announce_the_card_twice(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Registration belongs to the integration, not to each config entry."""
    second = MockConfigEntry(
        domain=mock_config_entry.domain,
        title="Vega",
        unique_id="vega",
        data={**mock_config_entry.data, "name": "Vega", "host": "10.0.1.31"},
    )
    second.add_to_hass(hass)

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(second.entry_id)
        await hass.async_block_till_done()

    assert second.state is ConfigEntryState.LOADED

    assert len(_card_urls(hass)) == 1


async def test_a_missing_bundle_leaves_the_integration_working(
    *,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The entities do not need the card, so its absence costs the card alone."""
    monkeypatch.setattr(bundled_card, "CARD_PATH", tmp_path / "mos-card.js")
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert "The bundled MOS NAS Card is missing" in caplog.text
    assert not _card_urls(hass)
