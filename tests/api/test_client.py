"""Tests for MOSApiClient's URL construction and error mapping."""

from __future__ import annotations

import asyncio
from itertools import pairwise
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.mos.api.client import (
    MOSApiClient,
    MOSApiClientAuthenticationError,
    MOSApiClientCommunicationError,
    MOSApiClientError,
    MOSApiClientPermissionError,
    MOSApiClientRateLimitError,
    _RateLimiter,
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
    aioclient_mock.get("http://10.0.1.30:80/api/v1/disks?performance=true&skipStandby=true", json=[{"serial": "S1"}])
    aioclient_mock.get("http://10.0.1.30:80/api/v1/pools?includeMetrics=true", json=[{"id": 1}])

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_disks() == [{"serial": "S1"}]
    assert await client.async_get_pools() == [{"id": 1}]


async def test_system_load_uses_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """system_load is fetched from the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/system/load",
        json={"cpu": {"load": 42.35}},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_system_load() == {"cpu": {"load": 42.35}}


async def test_lxc_containers_uses_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """lxc_containers is fetched from the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/lxc/containers/usage",
        json=[{"name": "database", "state": "running"}],
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_lxc_containers() == [{"name": "database", "state": "running"}]


async def test_docker_containers_uses_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """docker_containers is fetched from the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/docker/mos/containers",
        json=[{"name": "PushBits", "update_available": True}],
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_docker_containers() == [{"name": "PushBits", "update_available": True}]


async def test_docker_engine_containers_uses_raw_proxy(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """docker_engine_containers hits the raw Docker Engine proxy, not the mos-native endpoint."""
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/docker/containers/json?all=true",
        json=[{"Id": "abc", "Names": ["/PushBits"], "State": "running"}],
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_docker_engine_containers() == [
        {"Id": "abc", "Names": ["/PushBits"], "State": "running"}
    ]


async def test_start_docker_container_posts_to_raw_proxy_and_handles_204(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Starting a Docker container POSTs to the raw proxy; a 204 No Content response doesn't crash."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/docker/containers/PushBits/start",
        status=204,
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    result = await client.async_start_docker_container("PushBits")

    assert result is None
    assert aioclient_mock.mock_calls[0][0] == "post"


async def test_stop_docker_container_posts_to_raw_proxy_and_handles_204(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Stopping a Docker container POSTs to the raw proxy; a 204 No Content response doesn't crash."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/docker/containers/PushBits/stop",
        status=204,
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    result = await client.async_stop_docker_container("PushBits")

    assert result is None
    assert aioclient_mock.mock_calls[0][0] == "post"


async def test_start_lxc_container_posts_to_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Starting an LXC container POSTs to the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/lxc/containers/webserver/start",
        json={"success": True, "message": "Container webserver successfully started"},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    result = await client.async_start_lxc_container("webserver")

    assert result == {"success": True, "message": "Container webserver successfully started"}
    assert aioclient_mock.mock_calls[0][0] == "post"


async def test_stop_lxc_container_posts_to_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Stopping an LXC container POSTs to the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/lxc/containers/webserver/stop",
        json={"success": True, "message": "Container webserver successfully stopped"},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    result = await client.async_stop_lxc_container("webserver")

    assert result == {"success": True, "message": "Container webserver successfully stopped"}
    assert aioclient_mock.mock_calls[0][0] == "post"


async def test_vm_machines_uses_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """vm_machines is fetched from the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/vm/machines/usage",
        json=[{"name": "Test", "state": "running"}],
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_vm_machines() == [{"name": "Test", "state": "running"}]


async def test_start_vm_machine_posts_to_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Starting a VM POSTs to the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/vm/machines/Test/start",
        json={"success": True, "message": "VM Test successfully started"},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    result = await client.async_start_vm_machine("Test")

    assert result == {"success": True, "message": "VM Test successfully started"}
    assert aioclient_mock.mock_calls[0][0] == "post"


async def test_stop_vm_machine_posts_to_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Stopping a VM POSTs to the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/vm/machines/Test/stop",
        json={"success": True, "message": "VM Test successfully stopped"},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    result = await client.async_stop_vm_machine("Test")

    assert result == {"success": True, "message": "VM Test successfully stopped"}
    assert aioclient_mock.mock_calls[0][0] == "post"


@pytest.mark.parametrize(
    ("method_name", "expected_path"),
    [
        ("async_start_lxc_container", "/api/v1/lxc/containers/{name}/start"),
        ("async_stop_lxc_container", "/api/v1/lxc/containers/{name}/stop"),
        ("async_start_docker_container", "/api/v1/docker/containers/{name}/start"),
        ("async_stop_docker_container", "/api/v1/docker/containers/{name}/stop"),
        ("async_start_vm_machine", "/api/v1/vm/machines/{name}/start"),
        ("async_stop_vm_machine", "/api/v1/vm/machines/{name}/stop"),
    ],
)
async def test_write_actions_encode_the_name_as_one_path_segment(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    method_name: str,
    expected_path: str,
) -> None:
    """
    A name containing path separators cannot redirect the request to another endpoint.

    yarl resolves ``..`` while parsing the URL, so an unescaped name would send
    the Bearer token to whatever endpoint it points at - here the token
    introspection resource - instead of the container action.
    """
    hostile = "../../auth/admin-tokens/me"
    encoded = "..%2F..%2Fauth%2Fadmin-tokens%2Fme"
    aioclient_mock.post(
        f"http://10.0.1.30:80{expected_path.format(name=encoded)}",
        json={"success": True, "message": "ok"},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    await getattr(client, method_name)(hostile)

    assert len(aioclient_mock.mock_calls) == 1
    requested = aioclient_mock.mock_calls[0][1]
    assert requested.raw_path == expected_path.format(name=encoded)
    # The traversal target is never reached.
    assert not requested.raw_path.startswith("/api/v1/auth/")


async def test_write_actions_leave_ordinary_names_readable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Encoding must not change the URL for the names that actually occur."""
    aioclient_mock.post(
        "http://10.0.1.30:80/api/v1/docker/containers/PushBits/start",
        json={"success": True},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    await client.async_start_docker_container("PushBits")

    assert aioclient_mock.mock_calls[0][1].raw_path == "/api/v1/docker/containers/PushBits/start"


async def test_token_permissions_use_root_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Token permission introspection is fetched from the /api/v1 root, not /api/v1/mos."""
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/auth/admin-tokens/me",
        json={"id": "1", "name": "ha-mos", "role": "admin", "isBootToken": False, "permissions": {"mode": "full"}},
    )

    client = MOSApiClient(host="10.0.1.30", token="secret-token", session=async_get_clientsession(hass))

    assert await client.async_get_token_permissions() == {
        "id": "1",
        "name": "ha-mos",
        "role": "admin",
        "isBootToken": False,
        "permissions": {"mode": "full"},
    }


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


async def test_401_raises_authentication_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A 401 means the token itself was rejected."""
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", status=401)

    client = MOSApiClient(host="10.0.1.30", token="bad-token", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientAuthenticationError):
        await client.async_get_osinfo()


async def test_403_on_a_scope_denial_raises_permission_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A scope denial is a scope problem, and must not be mistaken for an invalid token.

    Conflating the two is what produced the reauth loop: the token is valid, so
    the reauth flow succeeds, and the very next poll fails again the same way.
    """
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/pools",
        status=403,
        json={"error": "Access denied. This token does not have 'read' permission for 'pools'."},
    )

    client = MOSApiClient(host="10.0.1.30", token="scoped-token", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientPermissionError) as raised:
        await client.async_get_pools()

    # The resource is named so the message points at the entry in the MOS web
    # UI's token editor rather than at our own internal resource key.
    assert "pools" in str(raised.value)
    assert not issubclass(MOSApiClientPermissionError, MOSApiClientAuthenticationError)


async def test_403_on_an_unknown_token_raises_authentication_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """MOS rejects a deleted or expired token with 403, not 401.

    The status code alone therefore says nothing, and reading it as a scope
    problem broke two things at once: the config flow told the user to grant a
    permission to a token that no longer exists, and - because reauth hangs off
    the authentication error - a token revoked at runtime could never reach the
    reauth flow at all. It just failed osinfo forever with every entity
    unavailable and no prompt.
    """
    aioclient_mock.get(
        "http://10.0.1.30:80/api/v1/mos/osinfo",
        status=403,
        json={"error": "Invalid or expired token."},
    )

    client = MOSApiClient(host="10.0.1.30", token="deleted-token", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientAuthenticationError):
        await client.async_get_osinfo()


async def test_403_without_a_readable_body_counts_as_a_rejected_token(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """An unreadable 403 errs towards the token, which is the visible failure.

    Both halves of MOS's 403 are matched on wording we do not control, so one of
    them has to be the fallback. A reverse proxy answering with HTML, or a
    future MOS rewording its message, then produces a reauth prompt - something
    the user can see and act on - rather than a resource that silently stays
    empty forever.
    """
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", status=403, text="<html>Forbidden</html>")

    client = MOSApiClient(host="10.0.1.30", token="tok", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientAuthenticationError):
        await client.async_get_osinfo()


async def test_429_raises_rate_limit_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A 429 is rate limiting - a "retry later", not a token or scope problem.

    It must stay distinct from both a communication error and a permission
    error so the coordinator can keep the resource's last-known state and retry,
    rather than tearing its entities down.
    """
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", status=429)

    client = MOSApiClient(host="10.0.1.30", token="tok", session=async_get_clientsession(hass))

    with pytest.raises(MOSApiClientRateLimitError):
        await client.async_get_osinfo()

    assert not issubclass(MOSApiClientRateLimitError, MOSApiClientPermissionError)
    assert not issubclass(MOSApiClientRateLimitError, MOSApiClientCommunicationError)


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


async def test_rate_limiter_spaces_out_request_starts() -> None:
    """Concurrent requests start at least min_interval apart, not all at once.

    This is the point of the limiter: MOS allows 20 requests/second per token
    and a poll fires every enabled resource concurrently, so without pacing the
    whole burst lands inside one second.
    """
    limiter = _RateLimiter(max_concurrent=10, min_interval=0.02)
    starts: list[float] = []

    async def request() -> None:
        async with limiter:
            starts.append(asyncio.get_running_loop().time())

    await asyncio.gather(*(request() for _ in range(5)))

    assert len(starts) == 5
    # asyncio.sleep never returns early, so the floor holds; the small tolerance
    # only guards against event-loop clock granularity.
    assert all(later - earlier >= 0.015 for earlier, later in pairwise(sorted(starts)))


async def test_rate_limiter_lets_a_lone_request_through_immediately() -> None:
    """Pacing is a floor on the gap between starts, not a delay added to every request."""
    limiter = _RateLimiter(max_concurrent=5, min_interval=10)

    loop = asyncio.get_running_loop()
    before = loop.time()
    async with limiter:
        pass

    assert loop.time() - before < 1


async def test_rate_limiter_caps_requests_in_flight() -> None:
    """No more than max_concurrent requests are outstanding at any moment."""
    limiter = _RateLimiter(max_concurrent=2, min_interval=0)
    in_flight = 0
    peak = 0

    async def request() -> None:
        nonlocal in_flight, peak
        async with limiter:
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1

    await asyncio.gather(*(request() for _ in range(6)))

    assert peak == 2


async def test_rate_limiter_releases_its_slot_when_the_request_fails() -> None:
    """A failed request hands its slot back, so failures cannot shrink the pool for good."""
    limiter = _RateLimiter(max_concurrent=1, min_interval=0)

    with pytest.raises(RuntimeError):
        async with limiter:
            raise RuntimeError

    # Would hang instead of raising TimeoutError if the slot had leaked.
    async with asyncio.timeout(1), limiter:
        pass


async def test_client_paces_its_requests(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """The limiter is wired into every request, not just available on the client.

    Deliberately end-to-end through the public API: pacing that the request path
    doesn't actually go through would be worse than none at all, since the 429
    handling downstream assumes it is there.
    """
    aioclient_mock.get("http://10.0.1.30:80/api/v1/mos/osinfo", json={})

    with patch("custom_components.mos.api.client.API_MIN_REQUEST_INTERVAL", 0.05):
        client = MOSApiClient(host="10.0.1.30", token="tok", session=async_get_clientsession(hass))
        loop = asyncio.get_running_loop()
        before = loop.time()
        await asyncio.gather(*(client.async_get_osinfo() for _ in range(4)))
        elapsed = loop.time() - before

    assert aioclient_mock.call_count == 4
    # Four requests, three enforced gaps of 50 ms between their starts.
    assert elapsed >= 0.13
