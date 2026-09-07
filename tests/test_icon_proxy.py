"""Tests for the icon proxy that serves guest artwork from Home Assistant's own origin."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
import re
from unittest.mock import AsyncMock

import aiohttp
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.mos.const import ICON_PROXY_HIT_TTL_SECONDS, ICON_PROXY_MISS_TTL_SECONDS
from homeassistant.core import HomeAssistant

_PNG = b"\x89PNG\r\n\x1a\nnot-really-an-image-but-bytes-all-the-same"
_OTHER_PNG = b"\x89PNG\r\n\x1a\ndifferent-bytes-entirely"
_SERVER_ICON = "http://10.0.1.30:80/docker_icons/PushBits.png"
_TEMPLATE_ICON = "https://raw.githubusercontent.com/pushbits/logo/main/logo.png"


async def _picture(hass: HomeAssistant) -> str:
    """Return the picture URL the PushBits container's state sensor publishes."""
    state = hass.states.get("sensor.sirius_docker_pushbits_state")
    assert state is not None
    picture = state.attributes["entity_picture"]
    assert isinstance(picture, str)
    return picture


async def _serve_from_the_server(hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock) -> str:
    """Point the container's picture at the icon MOS hosts itself, and return it."""
    mock_client.async_static_asset_exists.return_value = True
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    return await _picture(hass)


async def test_the_picture_addresses_home_assistant_not_the_server(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The whole point: what the browser is asked to load is on the origin it is already talking to."""
    picture = await _picture(hass)

    assert re.fullmatch(rf"/api/mos/icon/{setup_integration.entry_id}/[0-9a-f]{{32}}", picture)


async def test_the_view_serves_the_icon_the_entity_published(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """The bytes the source answered with, under a header that lets the browser keep them."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")

    response = await (await hass_client_no_auth()).get(picture)

    assert response.status == HTTPStatus.OK
    assert await response.read() == _PNG
    assert response.headers["Content-Type"] == "image/png"
    assert response.headers["Cache-Control"] == f"private, max-age={int(ICON_PROXY_HIT_TTL_SECONDS)}"
    assert response.headers["ETag"]
    mock_client.async_fetch_static_asset.assert_awaited_once_with("docker_icons/PushBits.png")


async def test_an_icon_the_browser_already_holds_is_not_sent_again(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Revalidation costs a header exchange rather than every icon on the dashboard."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")
    client = await hass_client_no_auth()

    etag = (await client.get(picture)).headers["ETag"]
    revalidated = await client.get(picture, headers={"If-None-Match": etag})

    assert revalidated.status == HTTPStatus.NOT_MODIFIED
    assert await revalidated.read() == b""
    assert revalidated.headers["ETag"] == etag
    assert revalidated.headers["Cache-Control"]


async def test_replaced_artwork_gets_a_new_etag_under_the_same_url(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
    advance_clock: Callable[[float], None],
) -> None:
    """The path is derived from the source URL, so the bytes are what says the icon changed."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")
    client = await hass_client_no_auth()
    etag = (await client.get(picture)).headers["ETag"]

    mock_client.async_fetch_static_asset.return_value = (_OTHER_PNG, "image/png")
    advance_clock(ICON_PROXY_HIT_TTL_SECONDS + 1)
    response = await client.get(picture, headers={"If-None-Match": etag})

    assert response.status == HTTPStatus.OK
    assert await response.read() == _OTHER_PNG
    assert response.headers["ETag"] != etag


async def test_a_cached_icon_is_not_fetched_again(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """A dashboard that several people have open is not several requests to the server."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")
    client = await hass_client_no_auth()

    assert (await client.get(picture)).status == HTTPStatus.OK
    assert (await client.get(picture)).status == HTTPStatus.OK

    assert mock_client.async_fetch_static_asset.await_count == 1


async def test_the_cache_is_asked_again_after_the_hit_ttl(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
    advance_clock: Callable[[float], None],
) -> None:
    """Artwork replaced on the server appears without restarting Home Assistant."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")
    client = await hass_client_no_auth()
    await client.get(picture)

    advance_clock(ICON_PROXY_HIT_TTL_SECONDS + 1)
    await client.get(picture)

    assert mock_client.async_fetch_static_asset.await_count == 2


async def test_a_source_that_answered_nothing_is_retried_sooner(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
    advance_clock: Callable[[float], None],
) -> None:
    """A failure is remembered so a busy dashboard cannot hammer the source, but not for the full hour."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = None
    client = await hass_client_no_auth()

    assert (await client.get(picture)).status == HTTPStatus.NOT_FOUND
    assert (await client.get(picture)).status == HTTPStatus.NOT_FOUND
    assert mock_client.async_fetch_static_asset.await_count == 1

    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")
    advance_clock(ICON_PROXY_MISS_TTL_SECONDS + 1)

    assert (await client.get(picture)).status == HTTPStatus.OK
    assert mock_client.async_fetch_static_asset.await_count == 2


async def test_a_token_no_entity_published_is_never_fetched(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """The allow-list is what keeps this from being an open proxy into the network HA sits on."""
    await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.reset_mock()

    response = await (await hass_client_no_auth()).get(f"/api/mos/icon/{setup_integration.entry_id}/{'a' * 32}")

    assert response.status == HTTPStatus.NOT_FOUND
    mock_client.async_fetch_static_asset.assert_not_awaited()


async def test_an_entry_that_is_not_ours_or_not_loaded_is_a_404(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """The proxy of one entry cannot be reached through the id of another, or of an unloaded one."""
    picture = await _serve_from_the_server(hass, setup_integration, mock_client)
    mock_client.async_fetch_static_asset.return_value = (_PNG, "image/png")
    client = await hass_client_no_auth()
    token = picture.rsplit("/", maxsplit=1)[1]

    assert (await client.get(f"/api/mos/icon/not-an-entry/{token}")).status == HTTPStatus.NOT_FOUND

    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert (await client.get(picture)).status == HTTPStatus.NOT_FOUND


async def test_a_template_icon_is_fetched_from_the_cdn_by_home_assistant(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """No dashboard viewer's browser contacts the CDN, and the icon loads without internet access."""
    aioclient_mock.get(_TEMPLATE_ICON, content=_PNG, headers={"Content-Type": "image/png"})

    response = await (await hass_client_no_auth()).get(await _picture(hass))

    assert response.status == HTTPStatus.OK
    assert await response.read() == _PNG
    assert len(aioclient_mock.mock_calls) == 1


async def test_a_source_answering_with_something_that_is_not_an_image_serves_nothing(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """A captive portal's login page must not reach a browser under a picture URL."""
    aioclient_mock.get(_TEMPLATE_ICON, text="<html>Sign in</html>", headers={"Content-Type": "text/html"})

    response = await (await hass_client_no_auth()).get(await _picture(hass))

    assert response.status == HTTPStatus.NOT_FOUND


async def test_a_source_that_cannot_be_reached_serves_nothing(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """A CDN that is down blanks one picture; it never surfaces as an error on the dashboard."""
    aioclient_mock.get(_TEMPLATE_ICON, exc=aiohttp.ClientError)

    response = await (await hass_client_no_auth()).get(await _picture(hass))

    assert response.status == HTTPStatus.NOT_FOUND
