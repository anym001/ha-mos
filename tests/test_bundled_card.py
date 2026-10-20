"""Tests for serving the bundled MOS NAS Card and announcing it to the frontend."""

from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.mos import bundled_card
from custom_components.mos.const import CARD_URL, DOMAIN, ISSUE_SEPARATE_CARD
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component


async def _set_up_with_resource(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: AsyncMock, url: str
) -> None:
    """Register a dashboard resource, then set the integration up."""
    assert await async_setup_component(hass, "lovelace", {})
    await hass.data[LOVELACE_DATA].resources.async_create_item({"res_type": "module", "url": url})
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


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


async def test_a_separately_installed_card_raises_a_repair_issue(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """A resource left over from the card's own HACS listing is named in the issue."""
    url = "/hacsfiles/ha-mos-card/mos-card.js?hacstag=123"

    await _set_up_with_resource(hass, mock_config_entry, mock_client, url)

    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_SEPARATE_CARD)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders == {"url": url}


async def test_an_unrelated_resource_raises_no_issue(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Only a resource serving the card's file name counts as a second copy."""
    await _set_up_with_resource(hass, mock_config_entry, mock_client, "/local/other-mos-card.js")

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_SEPARATE_CARD) is None


async def test_no_separate_card_clears_an_earlier_issue(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Removing the old copy is enough; the issue goes on the next start."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_SEPARATE_CARD,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_SEPARATE_CARD,
    )
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mos.MOSApiClient", return_value=mock_client):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_SEPARATE_CARD) is None
