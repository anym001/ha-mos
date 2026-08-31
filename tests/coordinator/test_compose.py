"""Tests for the Compose stack shaping helpers."""

from __future__ import annotations

from typing import Any

from custom_components.mos.coordinator.compose import (
    carry_forward_engine_state,
    carry_forward_group_data,
    merge_engine_state,
    merge_group_data,
    merge_stats,
    resolve_stack_icon,
    resolve_stack_web_ui_url,
    stats_targets,
)

HOST = "10.0.1.30"

GIBIBYTE = 1_073_741_824


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


def _member(name: str, **overrides: Any) -> dict[str, Any]:
    """Build one running, healthy member container as the engine list reports it."""
    return {
        "Names": [f"/{name}"],
        "Image": "busybox:latest",
        "State": "running",
        "Health": {"Status": "healthy", "FailingStreak": 0},
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


def test_counters_are_derived_from_the_member_containers() -> None:
    """The engine answers them from the containers themselves, so no group is needed."""
    engine = [
        _member("compose_hatest-alpha-1"),
        _member("compose_hatest-beta-1", State="exited"),
    ]

    merged = merge_engine_state([_stack()], engine)

    assert merged[0]["container_count"] == 2
    assert merged[0]["running_containers"] == 1


def test_engine_counters_win_over_the_groups() -> None:
    """Both describe the same thing, and only one of them counted the actual containers."""
    stacks = merge_group_data([_stack()], [_group(runningCount=2)])

    merged = merge_engine_state(stacks, [_member("compose_hatest-alpha-1", State="exited")])

    assert merged[0]["running_containers"] == 0
    # The one field the engine cannot answer is left alone.
    assert merged[0]["update_available"] is False


def test_members_are_matched_by_name_not_by_compose_label() -> None:
    """A container of another stack must not be counted into this one."""
    engine = [_member("compose_hatest-alpha-1"), _member("compose_other-alpha-1")]

    merged = merge_engine_state([_stack(containers=["compose_hatest-alpha-1"])], engine)

    assert merged[0]["container_count"] == 1
    assert merged[0]["running_containers"] == 1


def test_one_failing_service_makes_the_stack_a_problem() -> None:
    """MOS reports no stack-level health, so any unhealthy member is the verdict."""
    engine = [
        _member("compose_hatest-alpha-1", Health={"Status": "unhealthy", "FailingStreak": 3}),
        _member("compose_hatest-beta-1"),
    ]

    assert merge_engine_state([_stack()], engine)[0]["unhealthy"] is True


def test_a_stack_with_no_running_healthcheck_has_no_verdict() -> None:
    """Docker leaves a stopped container's health at whatever it last was."""
    stopped = [_member("compose_hatest-alpha-1", State="exited", Health={"Status": "unhealthy"})]
    unchecked = [_member("compose_hatest-alpha-1", Health={"Status": "none"})]

    assert merge_engine_state([_stack()], stopped)[0]["unhealthy"] is None
    assert merge_engine_state([_stack()], unchecked)[0]["unhealthy"] is None


def test_images_are_deduplicated() -> None:
    """Several services of one stack routinely share an image, and listing it twice says nothing."""
    engine = [
        _member("compose_hatest-alpha-1"),
        _member("compose_hatest-beta-1", Image="nginx:alpine"),
    ]

    assert merge_engine_state([_stack()], engine)[0]["images"] == ["busybox:latest", "nginx:alpine"]


def test_engine_fields_survive_a_failed_proxy_request() -> None:
    """The stack list still answered, so the last known figures beat blanks."""
    previous = merge_engine_state([_stack()], [_member("compose_hatest-alpha-1")])

    carried = carry_forward_engine_state([_stack(running=False)], previous)

    assert carried[0]["running_containers"] == 1
    assert carried[0]["images"] == ["busybox:latest"]
    assert carried[0]["running"] is False


def _stats(cpu: float | None, used: int | None) -> dict[str, Any]:
    """Build one container's parsed stats as ``parse_stats`` returns them."""
    return {
        "stats_cpu_percent": cpu,
        "stats_memory_bytes": used,
    }


def test_only_running_members_are_worth_a_request() -> None:
    """Docker answers for a stopped container with zeroes, which would read as an idle service."""
    engine = [
        _member("compose_hatest-alpha-1"),
        _member("compose_hatest-beta-1", State="exited"),
    ]

    assert stats_targets([_stack()], engine, {"hatest"}) == {"hatest": ["compose_hatest-alpha-1"]}


def test_a_stack_nobody_watches_is_never_targeted() -> None:
    """The whole point of the context: a stack no sensor asked about costs nothing."""
    engine = [_member("compose_hatest-alpha-1")]

    assert stats_targets([_stack()], engine, set()) == {}


def test_a_stack_with_nothing_running_is_not_targeted_at_all() -> None:
    """An empty target list would still cost the caller a lookup, so the stack drops out entirely."""
    engine = [_member("compose_hatest-alpha-1", State="exited")]

    assert stats_targets([_stack()], engine, {"hatest"}) == {}


def test_figures_are_summed_over_the_services() -> None:
    """A stack's cost is what all of its services cost together."""
    targets = {"hatest": ["compose_hatest-alpha-1", "compose_hatest-beta-1"]}
    measured = {
        "compose_hatest-alpha-1": _stats(25.0, 200_000_000),
        "compose_hatest-beta-1": _stats(15.5, 100_000_000),
    }

    merged = merge_stats([_stack()], targets, measured)[0]

    assert merged["stats_cpu_percent"] == 40.5
    assert merged["stats_memory_bytes"] == 300_000_000


def test_a_service_that_could_not_be_measured_is_left_out_of_the_sum() -> None:
    """One failed request costs that service's share, not the whole stack's figures."""
    targets = {"hatest": ["compose_hatest-alpha-1", "compose_hatest-beta-1"]}
    measured = {"compose_hatest-alpha-1": _stats(25.0, 200_000_000)}

    merged = merge_stats([_stack()], targets, measured)[0]

    assert merged["stats_cpu_percent"] == 25.0
    assert merged["stats_memory_bytes"] == 200_000_000


def test_an_unmeasured_stack_reads_blank_rather_than_zero() -> None:
    """A frozen or invented figure is indistinguishable from a live one."""
    merged = merge_stats([_stack()], {}, {})[0]

    assert merged["stats_cpu_percent"] is None
    assert merged["stats_memory_bytes"] is None
