"""Tests for the Compose stack shaping helpers."""

from __future__ import annotations

from typing import Any

from custom_components.mos.coordinator.compose import (
    carry_forward_group_data,
    merge_group_data,
    resolve_stack_icon,
    resolve_stack_web_ui_url,
)

HOST = "10.0.1.30"


def _stack(**overrides: Any) -> dict[str, Any]:
    """Build a running stack payload with a placeholder web interface."""
    return {
        "name": "hatest",
        "services": ["alpha", "beta"],
        "containers": ["compose_hatest-alpha-1", "compose_hatest-beta-1"],
        "iconUrl": "https://example.invalid/icon.png",
        "autostart": False,
        "webui": "http://[ADDRESS]:18099",
        "running": True,
    } | overrides


def _group(**overrides: Any) -> dict[str, Any]:
    """Build the group MOS auto-creates for the stack above."""
    return {
        "id": "1787846094449",
        "name": "hatest",
        "compose": True,
        "count": 2,
        "runningCount": 2,
        "update_available": False,
    } | overrides


def test_group_fields_are_lifted_onto_the_stack() -> None:
    """The three fields the stack list does not carry come from its group."""
    merged = merge_group_data([_stack()], [_group()])

    assert merged[0]["update_available"] is False
    assert merged[0]["container_count"] == 2
    assert merged[0]["running_containers"] == 2


def test_hand_made_group_of_the_same_name_is_ignored() -> None:
    """Only ``compose: true`` marks the group that stands for a stack."""
    merged = merge_group_data([_stack()], [_group(compose=False, update_available=True)])

    assert "update_available" not in merged[0]


def test_stack_without_a_group_keeps_the_fields_absent() -> None:
    """Defaulting them would assert "no update available" about something nothing was asked about."""
    merged = merge_group_data([_stack(name="orphan")], [_group()])

    assert "update_available" not in merged[0]
    assert "running_containers" not in merged[0]


def test_group_fields_survive_a_failed_group_request() -> None:
    """The stack list still answered, so the last known counters are better than blanks."""
    previous = merge_group_data([_stack()], [_group()])

    carried = carry_forward_group_data([_stack(running=False)], previous)

    assert carried[0]["running"] is False
    assert carried[0]["container_count"] == 2
    assert carried[0]["update_available"] is False


def test_a_stack_seen_for_the_first_time_carries_nothing_forward() -> None:
    """There is no previous poll to take the counters from, so they stay unknown."""
    carried = carry_forward_group_data([_stack()], [])

    assert "container_count" not in carried[0]


def test_host_placeholder_is_substituted() -> None:
    """MOS stores the host as a placeholder so the link follows the server it is read from."""
    assert resolve_stack_web_ui_url(_stack(), HOST) == f"http://{HOST}:18099"


def test_port_placeholder_drops_the_link() -> None:
    """A stack has no port mapping to resolve one against, and a wrong port looks like a working link."""
    assert resolve_stack_web_ui_url(_stack(webui="http://[ADDRESS]:[PORT:8080]/"), HOST) is None


def test_no_web_interface_and_no_host_both_give_no_link() -> None:
    """Both halves come from the server, and a link is not worth taking a poll down over."""
    assert resolve_stack_web_ui_url(_stack(webui=None), HOST) is None
    assert resolve_stack_web_ui_url(_stack(), None) is None


def test_icon_must_be_loadable_by_a_browser() -> None:
    """The frontend fetches it directly, so anything that is not plain http(s) is dropped."""
    assert resolve_stack_icon(_stack()) == "https://example.invalid/icon.png"
    assert resolve_stack_icon(_stack(iconUrl=None)) is None
    assert resolve_stack_icon(_stack(iconUrl="/docker_icons/hatest.png")) is None
