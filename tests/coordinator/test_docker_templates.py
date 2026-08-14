"""Tests for the Docker template cache and the web interface link it resolves."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.mos.api import MOSApiClient, MOSApiClientCommunicationError, MOSApiClientNotFoundError
from custom_components.mos.coordinator.docker_templates import DockerTemplateCache, resolve_icon, resolve_web_ui_url

HOST = "10.0.1.30"


def _container(**overrides: Any) -> dict[str, Any]:
    """Build a merged container payload, running and published on 8081 by default."""
    return {
        "name": "PushBits",
        "container_id": "abc123",
        "state": "running",
        "labels": {"mos.webui": "http://[ADDRESS]:[PORT:8080]/"},
        "ports": [{"IP": "0.0.0.0", "PrivatePort": 8080, "PublicPort": 8081, "Type": "tcp"}],
    } | overrides


def _template(**overrides: Any) -> dict[str, Any]:
    """Build a MOS template that maps container port 8080 to host port 8081."""
    return {
        "icon": "https://example.invalid/icon.png",
        "web_ui_url": "http://[IP]:[PORT:8080]/",
        "ports": [{"protocol": "tcp", "host": "8081", "container": "8080"}],
    } | overrides


def test_running_container_uses_the_live_host_port() -> None:
    """The placeholder names the container port, so the published host port is what the link must carry."""
    assert resolve_web_ui_url(_container(), None, HOST) == f"http://{HOST}:8081/"


def test_stopped_container_falls_back_to_the_template_mapping() -> None:
    """Docker reports no ports for a stopped container; the template still knows the pair."""
    stopped = _container(state="exited", ports=[])

    assert resolve_web_ui_url(stopped, _template(), HOST) == f"http://{HOST}:8081/"


def test_live_mapping_wins_over_the_template() -> None:
    """A container remapped outside MOS is reachable where Docker says, not where the template says."""
    remapped = _container(ports=[{"PrivatePort": 8080, "PublicPort": 9999, "Type": "tcp"}])

    assert resolve_web_ui_url(remapped, _template(), HOST) == f"http://{HOST}:9999/"


def test_unresolvable_port_yields_no_link() -> None:
    """Better no link than one that looks right and points at a closed port."""
    stopped = _container(state="exited", ports=[])

    assert resolve_web_ui_url(stopped, None, HOST) is None


def test_template_url_used_when_the_container_has_no_label() -> None:
    """A container without the mos.webui label can still have a web interface configured in its template."""
    unlabelled = _container(labels={})

    assert resolve_web_ui_url(unlabelled, _template(), HOST) == f"http://{HOST}:8081/"


def test_no_web_interface_configured_yields_no_link() -> None:
    """Nothing to link to is a normal state, not an error."""
    assert resolve_web_ui_url(_container(labels={}), None, HOST) is None


def test_empty_template_url_yields_no_link() -> None:
    """A container with no web interface has an empty ``web_ui_url``, not a missing one."""
    unlabelled = _container(labels={})

    assert resolve_web_ui_url(unlabelled, _template(web_ui_url=""), HOST) is None


def test_missing_host_yields_no_link() -> None:
    """Without a host there is nothing to substitute for the address placeholder."""
    assert resolve_web_ui_url(_container(), None, None) is None


def test_url_without_placeholders_is_passed_through() -> None:
    """An absolute URL configured by hand needs no resolving."""
    absolute = _container(labels={"mos.webui": "https://pushbits.example.invalid/"})

    assert resolve_web_ui_url(absolute, None, HOST) == "https://pushbits.example.invalid/"


@pytest.mark.parametrize(
    "template",
    [None, {}, {"icon": ""}, {"icon": "not-a-url"}, {"icon": "file:///etc/passwd"}],
)
def test_only_http_icons_are_offered_to_the_frontend(template: dict[str, Any] | None) -> None:
    """An entity picture is a URL the browser fetches; anything else is dropped."""
    assert resolve_icon(template) is None


def test_icon_url_is_taken_from_the_template() -> None:
    """The template is the only place MOS exposes a container icon."""
    assert resolve_icon(_template()) == "https://example.invalid/icon.png"


@pytest.fixture
def client() -> AsyncMock:
    """Return a client whose template endpoint answers with a counted stub."""
    stub = AsyncMock(spec=MOSApiClient)
    stub.async_get_docker_template.return_value = _template()
    return stub


async def test_unchanged_container_is_not_refetched(client: AsyncMock) -> None:
    """The steady state costs no requests - the whole point of caching this."""
    cache = DockerTemplateCache(client)

    await cache.async_refresh([_container()])
    await cache.async_refresh([_container()])

    assert client.async_get_docker_template.await_count == 1
    assert cache.get("PushBits") == _template()


async def test_recreated_container_is_refetched(client: AsyncMock) -> None:
    """Editing a container's template makes MOS recreate it with a new id, which is the invalidation signal."""
    cache = DockerTemplateCache(client)

    await cache.async_refresh([_container()])
    await cache.async_refresh([_container(container_id="def456")])

    assert client.async_get_docker_template.await_count == 2


async def test_missing_container_id_does_not_cause_a_refetch(client: AsyncMock) -> None:
    """A poll without the engine proxy cannot invalidate anything, and must not retry every cycle."""
    cache = DockerTemplateCache(client)

    await cache.async_refresh([_container(container_id=None)])
    await cache.async_refresh([_container(container_id=None)])

    assert client.async_get_docker_template.await_count == 1


async def test_removed_container_is_dropped_from_the_cache(client: AsyncMock) -> None:
    """A container that disappears takes its template with it."""
    cache = DockerTemplateCache(client)
    await cache.async_refresh([_container()])

    await cache.async_refresh([])

    assert cache.get("PushBits") is None


async def test_container_without_a_template_is_remembered_as_such(client: AsyncMock) -> None:
    """A container created outside MOS answers 404; asking again every poll would be pure waste."""
    client.async_get_docker_template.side_effect = MOSApiClientNotFoundError("no template")
    cache = DockerTemplateCache(client)

    await cache.async_refresh([_container()])
    await cache.async_refresh([_container()])

    assert client.async_get_docker_template.await_count == 1
    assert cache.get("PushBits") is None


async def test_fetch_failure_is_retried_and_does_not_propagate(client: AsyncMock) -> None:
    """An icon is not worth failing a poll over, but it is worth trying again."""
    client.async_get_docker_template.side_effect = MOSApiClientCommunicationError("timeout")
    cache = DockerTemplateCache(client)

    await cache.async_refresh([_container()])
    assert cache.get("PushBits") is None

    client.async_get_docker_template.side_effect = None
    client.async_get_docker_template.return_value = _template()
    await cache.async_refresh([_container()])

    assert cache.get("PushBits") == _template()
