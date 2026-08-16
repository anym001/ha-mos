"""Tests for the server-hosted guest icons: which file a guest points at, and whether it exists."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.mos.api import (
    MOSApiClient,
    MOSApiClientAuthenticationError,
    MOSApiClientCommunicationError,
    MOSApiClientNotFoundError,
    MOSApiClientPermissionError,
)
from custom_components.mos.coordinator import guest_icons
from custom_components.mos.coordinator.guest_icons import GuestIconCache, docker_icon_path, lxc_icon_path, vm_icon_path

ROOT_URL = "http://10.0.1.30:80"


def _client(*, exists: bool = True) -> AsyncMock:
    """Build a stand-in API client whose static-asset probe answers ``exists``."""
    client = AsyncMock(spec=MOSApiClient)
    client.root_url = ROOT_URL
    client.async_static_asset_exists.return_value = exists
    client.async_get_lxc_container_details.return_value = []
    client.async_get_vm_machine_details.return_value = []
    return client


# --- which file a guest points at -------------------------------------------


def test_docker_icon_is_named_after_the_container() -> None:
    """Docker has no icon flag; MOS names the file after the container."""
    assert docker_icon_path("PushBits") == "docker_icons/PushBits.png"


def test_a_nameless_guest_has_no_icon_path() -> None:
    """Nothing to build a filename from, so nothing is probed."""
    assert docker_icon_path(None) is None
    assert docker_icon_path("   ") is None


def test_guest_name_is_percent_encoded() -> None:
    """A name is server data, not a promise; it must stay one path segment."""
    assert docker_icon_path("../../etc/passwd") == "docker_icons/..%2F..%2Fetc%2Fpasswd.png"


def test_lxc_without_a_custom_icon_uses_the_distribution_artwork() -> None:
    """The stock case: custom_icon is false, so the icon is the distribution's."""
    detail = {"name": "database", "distribution": "debian", "custom_icon": False}

    assert lxc_icon_path(detail) == "os_icons/debian.png"


def test_lxc_with_a_custom_icon_uses_its_own_name() -> None:
    """An uploaded icon is filed under the container's name, not its distribution's."""
    detail = {"name": "webserver", "distribution": "alpine", "custom_icon": True}

    assert lxc_icon_path(detail) == "lxc_custom/webserver.png"


def test_lxc_without_a_distribution_falls_back_to_its_own_name() -> None:
    """No distribution to name a file after leaves only the per-guest one to try."""
    detail = {"name": "webserver", "distribution": None, "custom_icon": False}

    assert lxc_icon_path(detail) == "lxc_custom/webserver.png"


def test_vm_reads_the_same_rule_under_camel_case_keys() -> None:
    """The VM endpoint spells the two fields differently but means the same thing."""
    assert vm_icon_path({"name": "Test", "icon": "debian", "customIcon": False}) == "os_icons/debian.png"
    assert vm_icon_path({"name": "Test", "icon": "debian", "customIcon": True}) == "lxc_custom/Test.png"
    assert vm_icon_path({"name": "Legacy", "icon": None, "customIcon": False}) == "lxc_custom/Legacy.png"


# --- whether that file exists ------------------------------------------------


async def test_an_existing_icon_becomes_an_absolute_url() -> None:
    """The picture is loaded by the browser, so it needs the server's origin on the front."""
    cache = GuestIconCache(_client())

    assert await cache.async_icon_url("docker_icons/PushBits.png") == f"{ROOT_URL}/docker_icons/PushBits.png"


async def test_a_missing_icon_yields_no_url() -> None:
    """A 404 handed to the frontend renders as a broken image, which is worse than nothing."""
    cache = GuestIconCache(_client(exists=False))

    assert await cache.async_icon_url("docker_icons/Nope.png") is None


async def test_no_path_is_never_probed() -> None:
    """A guest with nothing to look up costs no request."""
    client = _client()
    cache = GuestIconCache(client)

    assert await cache.async_icon_url(None) is None
    client.async_static_asset_exists.assert_not_called()


async def test_a_found_icon_is_probed_once() -> None:
    """Steady state has to cost nothing; the file cannot usefully stop existing."""
    client = _client()
    cache = GuestIconCache(client)

    for _ in range(3):
        await cache.async_icon_url("docker_icons/PushBits.png")

    client.async_static_asset_exists.assert_awaited_once_with("docker_icons/PushBits.png")


async def test_a_missing_icon_is_re_probed_once_its_answer_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    """Artwork uploaded after startup has to appear without restarting Home Assistant."""
    client = _client(exists=False)
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)

    assert await cache.async_icon_url("docker_icons/PushBits.png") is None
    assert await cache.async_icon_url("docker_icons/PushBits.png") is None
    assert client.async_static_asset_exists.await_count == 1

    clock = guest_icons._MISS_TTL_SECONDS + 1
    client.async_static_asset_exists.return_value = True

    assert await cache.async_icon_url("docker_icons/PushBits.png") == f"{ROOT_URL}/docker_icons/PushBits.png"
    assert client.async_static_asset_exists.await_count == 2


# --- the configuration behind the path ---------------------------------------


def _lxc_details() -> list[dict[str, Any]]:
    """Build a ``/lxc/containers`` payload for one stock and one custom-iconed container."""
    return [
        {"name": "database", "distribution": "debian", "custom_icon": False},
        {"name": "webserver", "distribution": "alpine", "custom_icon": True},
    ]


async def test_lxc_containers_are_stamped_with_their_icon_url() -> None:
    """Each container carries the URL for the file its own configuration names."""
    client = _client()
    client.async_get_lxc_container_details.return_value = _lxc_details()
    cache = GuestIconCache(client)

    stamped = await cache.async_add_lxc_icons([{"name": "database"}, {"name": "webserver"}])

    assert [container["icon_url"] for container in stamped] == [
        f"{ROOT_URL}/os_icons/debian.png",
        f"{ROOT_URL}/lxc_custom/webserver.png",
    ]


async def test_vm_machines_are_stamped_with_their_icon_url() -> None:
    """The VM half of the same pass, off the VM configuration endpoint."""
    client = _client()
    client.async_get_vm_machine_details.return_value = [{"name": "Test", "icon": "debian", "customIcon": False}]
    cache = GuestIconCache(client)

    stamped = await cache.async_add_vm_icons([{"name": "Test"}])

    assert stamped[0]["icon_url"] == f"{ROOT_URL}/os_icons/debian.png"


async def test_an_empty_guest_list_costs_nothing() -> None:
    """No guests means no configuration to read and no icon to look for."""
    client = _client()
    cache = GuestIconCache(client)

    assert await cache.async_add_lxc_icons([]) == []
    client.async_get_lxc_container_details.assert_not_called()


async def test_configuration_is_read_once_for_an_unchanged_guest_list() -> None:
    """These fields change when someone edits a container, not every 30 seconds."""
    client = _client()
    client.async_get_lxc_container_details.return_value = _lxc_details()
    cache = GuestIconCache(client)

    for _ in range(3):
        await cache.async_add_lxc_icons([{"name": "database"}])

    client.async_get_lxc_container_details.assert_awaited_once()


async def test_a_new_guest_refetches_the_configuration_early(monkeypatch: pytest.MonkeyPatch) -> None:
    """A container created since the last fetch must not wait out the whole TTL for its picture."""
    client = _client()
    client.async_get_lxc_container_details.return_value = _lxc_details()[:1]
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)
    await cache.async_add_lxc_icons([{"name": "database"}])

    clock = guest_icons._DETAIL_RETRY_SECONDS + 1
    client.async_get_lxc_container_details.return_value = _lxc_details()
    stamped = await cache.async_add_lxc_icons([{"name": "database"}, {"name": "webserver"}])

    assert client.async_get_lxc_container_details.await_count == 2
    assert stamped[1]["icon_url"] == f"{ROOT_URL}/lxc_custom/webserver.png"


async def test_a_guest_the_endpoint_never_lists_does_not_refetch_every_poll() -> None:
    """The early-refetch trigger cannot tell "new" from "never listed", so it is rate limited."""
    client = _client()
    client.async_get_lxc_container_details.return_value = []
    cache = GuestIconCache(client)

    for _ in range(5):
        await cache.async_add_lxc_icons([{"name": "database"}])

    client.async_get_lxc_container_details.assert_awaited_once()


async def test_a_failed_configuration_fetch_keeps_the_previous_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """An icon is not worth taking a poll down over, nor worth blanking a working picture for."""
    client = _client()
    client.async_get_lxc_container_details.return_value = _lxc_details()[:1]
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)
    await cache.async_add_lxc_icons([{"name": "database"}])

    clock = guest_icons._DETAIL_RETRY_SECONDS + 1
    client.async_get_lxc_container_details.side_effect = MOSApiClientCommunicationError("timeout")
    stamped = await cache.async_add_lxc_icons([{"name": "database"}, {"name": "webserver"}])

    assert client.async_get_lxc_container_details.await_count == 2
    assert stamped[0]["icon_url"] == f"{ROOT_URL}/os_icons/debian.png"


async def test_a_guest_missing_from_the_configuration_falls_back_to_its_poll_payload() -> None:
    """With nothing to read the flags from, the per-guest name is the only candidate left."""
    client = _client()
    client.async_get_lxc_container_details.return_value = []
    cache = GuestIconCache(client)

    stamped = await cache.async_add_lxc_icons([{"name": "database"}])

    assert stamped[0]["icon_url"] == f"{ROOT_URL}/lxc_custom/database.png"


# --- giving up on an endpoint that cannot answer ------------------------------


async def test_a_scope_denial_stops_the_endpoint_being_asked_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server named the resource it refused, so retrying can only repeat the refusal."""
    client = _client()
    client.async_get_lxc_container_details.side_effect = MOSApiClientPermissionError("no read permission for lxc")
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)

    for _ in range(3):
        clock += guest_icons._DETAIL_TTL_SECONDS + 1
        await cache.async_add_lxc_icons([{"name": "database"}])

    client.async_get_lxc_container_details.assert_awaited_once()
    assert cache.denied_sources == frozenset({"lxc"})


async def test_a_denied_endpoint_still_yields_the_per_guest_icon() -> None:
    """Losing the configuration costs the distribution artwork, not the picture altogether."""
    client = _client()
    client.async_get_vm_machine_details.side_effect = MOSApiClientPermissionError("no read permission for vm")
    cache = GuestIconCache(client)

    stamped = await cache.async_add_vm_icons([{"name": "Test"}])

    assert stamped[0]["icon_url"] == f"{ROOT_URL}/lxc_custom/Test.png"


async def test_a_denial_keeps_the_configuration_it_already_had(monkeypatch: pytest.MonkeyPatch) -> None:
    """A scope narrowed at runtime must not blank the pictures that were already working."""
    client = _client()
    client.async_get_lxc_container_details.return_value = _lxc_details()
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)
    await cache.async_add_lxc_icons([{"name": "database"}])

    clock += guest_icons._DETAIL_TTL_SECONDS + 1
    client.async_get_lxc_container_details.side_effect = MOSApiClientPermissionError("no read permission for lxc")
    stamped = await cache.async_add_lxc_icons([{"name": "database"}])

    assert stamped[0]["icon_url"] == f"{ROOT_URL}/os_icons/debian.png"


async def test_a_missing_endpoint_is_re_probed_but_not_once_a_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every guest is permanently "unknown" on an endpoint that lists none, so the early trigger cannot apply."""
    client = _client()
    client.async_get_lxc_container_details.side_effect = MOSApiClientNotFoundError("no such endpoint")
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)
    await cache.async_add_lxc_icons([{"name": "database"}])

    # The rate the early-refetch trigger would have used, had it applied.
    clock += guest_icons._DETAIL_RETRY_SECONDS + 1
    await cache.async_add_lxc_icons([{"name": "database"}])
    client.async_get_lxc_container_details.assert_awaited_once()
    assert cache.unsupported_sources == frozenset({"lxc"})

    # ... but it is still asked for, so a MOS update needs no reload.
    clock += guest_icons._DETAIL_TTL_SECONDS + 1
    client.async_get_lxc_container_details.side_effect = None
    client.async_get_lxc_container_details.return_value = _lxc_details()
    stamped = await cache.async_add_lxc_icons([{"name": "database"}])

    assert client.async_get_lxc_container_details.await_count == 2
    assert stamped[0]["icon_url"] == f"{ROOT_URL}/os_icons/debian.png"
    assert cache.unsupported_sources == frozenset()


async def test_a_rejected_token_is_not_given_up_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid token is the coordinator's to resolve via reauth; the icons recover with it."""
    client = _client()
    client.async_get_lxc_container_details.side_effect = MOSApiClientAuthenticationError("invalid token")
    cache = GuestIconCache(client)
    clock = 0.0
    monkeypatch.setattr(guest_icons.time, "monotonic", lambda: clock)
    await cache.async_add_lxc_icons([{"name": "database"}])

    clock += guest_icons._DETAIL_RETRY_SECONDS + 1
    await cache.async_add_lxc_icons([{"name": "database"}])

    assert client.async_get_lxc_container_details.await_count == 2
    assert cache.denied_sources == frozenset()
