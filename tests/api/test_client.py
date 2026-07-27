"""Tests for MOSApiClient's URL construction and error mapping."""

from __future__ import annotations

from unittest.mock import AsyncMock

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.mos.api.client import (
    MOSApiClient,
    MOSApiClientAuthenticationError,
    MOSApiClientCommunicationError,
    MOSApiClientError,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def test_osinfo_and_services_use_mos_base_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """osinfo/services are fetched from the /api/v1/mos base with a Bearer token."""
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", json={"hostname": "sirius"})
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/services", json={"docker": {"running": True}})

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_osinfo() == {"hostname": "sirius"}
    assert await client.async_get_services() == {"docker": {"running": True}}

    for call in aioclient_mock.mock_calls:
        assert call[3]["Authorization"] == "Bearer secret-token"


async def test_disks_and_pools_use_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """disks/pools are fetched directly from the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.get("http://10.0.1.30:80/api/v1/disks", json=[{"serial": "S1"}])
    aioclient_mock.get("http://10.0.1.30:80/api/v1/pools", json=[{"id": 1}])

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_disks() == [{"serial": "S1"}]
    assert await client.async_get_pools() == [{"id": 1}]


async def test_https_and_explicit_port(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """use_ssl selects the https scheme and an explicit port overrides the default."""
    aioclient_mock.get("https://10.0.1.30:8443/api/v1/mos/osinfo", json={})

    client = MOSApiClient(
        host="10.0.1.30",
        token="secret-token",
        session=async_get_clientsession(hass),
        use_ssl=True,
        port=8443,
    )

    await client.async_get_osinfo()
    assert aioclient_mock.call_count == 1


async def test_float_port_is_coerced_to_int(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A float port (as produced by selector.NumberSelector) still builds a valid URL.

    Regression test: config entries created via the config flow store the port
    as a float (e.g. 8080.0) because selector.NumberSelector always coerces to
    float. The client must not embed that float verbatim in the URL.
    """
    aioclient_mock.get("http://10.0.1.30:8080/api/v1/mos/osinfo", json={})

    client = MOSApiClient(
        host="10.0.1.30",
        token="secret-token",
        session=async_get_clientsession(hass),
        port=8080.0,
    )

    await client.async_get_osinfo()
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_error_status_codes_raise_authentication_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    status: int,
) -> None:
    """401 and 403 responses are translated into MOSApiClientAuthenticationError."""
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", status=status)

    client = MOSApiClient(host="10.0.1.30", token="bad-token", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientAuthenticationError):
        await client.async_get_osinfo()


async def test_other_http_error_raises_communication_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A non-auth HTTP error status is a communication error."""
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", status=500)

    client = MOSApiClient(host="10.0.1.30", token="tok", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientCommunicationError):
        await client.async_get_osinfo()


async def test_timeout_raises_communication_error() -> None:
    """A timeout while awaiting the request is a communication error."""
    session = AsyncMock()
    session.request.side_effect = TimeoutError

    client = MOSApiClient(host="10.0.1.30", token="tok", session=session)

    with pytest.raises(MOSApiClientCommunicationError):
        await client.async_get_osinfo()


async def test_client_error_raises_communication_error() -> None:
    """An aiohttp.ClientError while awaiting the request is a communication error."""
    session = AsyncMock()
    session.request.side_effect = aiohttp.ClientConnectionError("connection refused")

    client = MOSApiClient(host="10.0.1.30", token="tok", session=session)

    with pytest.raises(MOSApiClientCommunicationError):
        await client.async_get_osinfo()


async def test_unexpected_error_raises_generic_api_error() -> None:
    """Any other exception is wrapped as the generic MOSApiClientError."""
    session = AsyncMock()
    session.request.side_effect = ValueError("something odd")

    client = MOSApiClient(host="10.0.1.30", token="tok", session=session)

    with pytest.raises(MOSApiClientError):
        await client.async_get_osinfo()
