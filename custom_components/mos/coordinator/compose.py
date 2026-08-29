"""
Docker Compose stack shaping for mos.

A stack is not a container, and MOS keeps the two apart: a compose stack never
appears in ``/docker/mos/containers``, and its member containers carry generated
names (``compose_<stack>-<service>-1``) that have no MOS template behind them.
What a stack does have is a single ``running`` flag covering all of its
services, which is also the only thing MOS lets a caller change - start and stop
act on the whole stack.

Two other sources fill in what that flag cannot say. The raw Docker Engine list
already fetched for the containers also carries every stack's member containers,
so their live state, health and images are had for no extra request. The
container group MOS auto-creates per stack carries ``update_available``, which
nothing else reports.

Live CPU and memory are the exception that costs something. Docker measures one
container at a time, so a stack's figures are the sum over its running members -
one request per service per poll, which is why the option behind them is off by
default and separate from the Docker one.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from custom_components.mos.coordinator.docker_templates import HOST_PLACEHOLDER, PORT_PLACEHOLDER

# Group fields lifted onto a stack, under the names the entities use.
#
# Only ``update_available`` has no better source. The counters are kept as a
# fallback for a poll where the engine proxy is unavailable but the group list
# is not - see ``merge_engine_state``, which overwrites them when it can.
_GROUP_FIELDS = {
    "update_available": "update_available",
    "count": "container_count",
    "runningCount": "running_containers",
}

# What ``merge_engine_state`` derives, named once so ``carry_forward_engine_state``
# cannot fall behind and blank one out on a poll where the proxy is unavailable.
ENGINE_DERIVED_FIELDS = ("running_containers", "container_count", "unhealthy", "images")

# What Docker reports for a container that defines no healthcheck at all.
_HEALTH_NOT_CONFIGURED = "none"


def merge_group_data(stacks: list[dict[str, Any]], groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Join each stack with the container group MOS auto-created for it.

    Groups a user built by hand are skipped: only ``compose: true`` marks the
    group that stands for a stack, and matching on the name alone would let a
    hand-made group of the same name supply an unrelated update flag.

    A stack with no matching group keeps the fields absent rather than defaulting
    them, so its entities read unknown instead of asserting "no update available"
    about something nothing was asked about.

    Returns:
        The stacks, each with the ``_GROUP_FIELDS`` added where a group exists.

    """
    by_name = {group.get("name"): group for group in groups if group.get("compose") is True}
    merged: list[dict[str, Any]] = []
    for stack in stacks:
        group = by_name.get(stack.get("name"))
        if group is None:
            merged.append(stack)
            continue
        merged.append(
            {**stack, **{target: group[source] for source, target in _GROUP_FIELDS.items() if source in group}}
        )
    return merged


def carry_forward_group_data(stacks: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Re-attach the group-derived fields from the previous poll's stacks.

    ``merge_group_data`` folds the group list into the stacks and the raw list is
    then dropped, so there is nothing for ``_retain_last_known_good`` to carry
    forward when the group endpoint alone fails. Without this, a single failed
    request would blank the update flag on every stack while the stack list
    itself answered fine.

    Returns:
        The stacks, each with the ``_GROUP_FIELDS`` it had last poll.

    """
    return _carry_forward(stacks, previous, _GROUP_FIELDS.values())


def merge_engine_state(stacks: list[dict[str, Any]], engine_containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Derive each stack's live figures from its member containers in the engine list.

    The stack's own ``containers`` field names them, so they are matched by name
    rather than by Compose's ``com.docker.compose.project`` label: MOS derives
    that project name from the stack name by a prefixing rule this integration
    would otherwise have to assume, while the name list is stated outright.

    This overwrites the counters the group supplied. Both describe the same
    thing, but the engine answers it from the containers themselves and is
    already being fetched, so a stack keeps honest counters on a poll where the
    group endpoint fails.

    ``unhealthy`` has no group or stack-list equivalent at all. It is ``None``
    unless at least one running member defines a healthcheck, because Docker
    leaves a stopped container's health at whatever it last was - reporting that
    as a verdict would flag every stopped stack.

    Returns:
        The stacks, each with the ``ENGINE_DERIVED_FIELDS`` added.

    """
    by_name = {(container.get("Names") or [""])[0].lstrip("/"): container for container in engine_containers}
    merged: list[dict[str, Any]] = []
    for stack in stacks:
        names = stack.get("containers")
        if not isinstance(names, list):
            merged.append(stack)
            continue
        members = [by_name[name] for name in names if name in by_name]
        merged.append(
            {
                **stack,
                "container_count": len(names),
                "running_containers": sum(1 for member in members if member.get("State") == "running"),
                "unhealthy": _is_unhealthy(members),
                "images": sorted({image for member in members if (image := member.get("Image"))}),
            }
        )
    return merged


def carry_forward_engine_state(stacks: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Re-attach the engine-derived fields from the previous poll's stacks.

    Mirrors ``carry_forward_group_data``: the raw engine list is merged and then
    dropped, so a poll where the proxy alone fails would otherwise blank the
    counters and the health verdict on every stack.

    Returns:
        The stacks, each with the ``ENGINE_DERIVED_FIELDS`` it had last poll.

    """
    return _carry_forward(stacks, previous, ENGINE_DERIVED_FIELDS)


@dataclass(frozen=True)
class ComposeStatsContext:
    """
    A running stack stats sensor's request to have its stack measured.

    The stack counterpart of ``DockerStatsContext``, and a separate type for the
    same reason that one is: contexts from every platform land in the same
    ``async_contexts()`` stream, and a stack must not be measured because a
    container happens to share its name.
    """

    name: str


def stats_targets(
    stacks: list[dict[str, Any]],
    engine_containers: list[dict[str, Any]],
    wanted: set[str],
) -> dict[str, list[str]]:
    """
    Map each wanted stack to the member containers worth spending a request on.

    Only running members are listed: Docker answers for a stopped container with
    zeroes, which would drag a stack's sum down as if the service were idle
    rather than absent.

    Returns:
        The member container names to measure, keyed by stack name. A stack with
        nothing running is absent rather than present with an empty list.

    """
    running = {
        name
        for container in engine_containers
        if container.get("State") == "running" and (name := (container.get("Names") or [""])[0].lstrip("/"))
    }
    targets: dict[str, list[str]] = {}
    for stack in stacks:
        name = stack.get("name")
        names = stack.get("containers")
        if name not in wanted or not isinstance(names, list):
            continue
        members = [member for member in names if member in running]
        if members:
            targets[name] = members
    return targets


def merge_stats(
    stacks: list[dict[str, Any]],
    targets: dict[str, list[str]],
    measured: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Stamp each stack with the sum of its running members' figures.

    A stack that was not measured at all - not wanted, nothing running, or every
    request failed - is blanked rather than left at its previous values, on the
    same reasoning as the Docker containers: a frozen CPU reading is
    indistinguishable from a live one.

    Returns:
        The stacks, each with the ``DOCKER_STATS_FIELDS`` added.

    """
    merged: list[dict[str, Any]] = []
    for stack in stacks:
        members = [measured[name] for name in targets.get(stack.get("name") or "", []) if name in measured]
        merged.append({**stack, **_sum_stats(members)})
    return merged


def _sum_stats(members: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Add up the per-container figures into one set for the whole stack.

    CPU and used bytes simply add: both are absolute amounts on the same host,
    and a stack using two fully-busy cores reading as 200% matches what its
    containers report individually.

    The percentage is the one that cannot always be formed. It needs a single
    budget to divide by, and members only share one when they are all limited
    the same way - which is the usual case, since an unconstrained container is
    reported by Docker as limited to the host's entire RAM. Where the members
    disagree there is no such budget, and inventing a denominator would produce
    a figure that looks authoritative and means nothing.

    Returns:
        The ``DOCKER_STATS_FIELDS``, each a number or ``None``.

    """
    cpu = [value for member in members if (value := member.get("stats_cpu_percent")) is not None]
    used = [value for member in members if (value := member.get("stats_memory_bytes")) is not None]
    limits = {value for member in members if (value := member.get("stats_memory_limit_bytes")) is not None}

    total_used = sum(used) if used else None
    limit = limits.pop() if len(limits) == 1 else None
    return {
        "stats_cpu_percent": round(sum(cpu), 2) if cpu else None,
        "stats_memory_bytes": total_used,
        "stats_memory_limit_bytes": limit,
        "stats_memory_percent": round(total_used / limit * 100, 2) if total_used is not None and limit else None,
    }


def _is_unhealthy(members: list[dict[str, Any]]) -> bool | None:
    """
    Report whether any running member of a stack is failing its healthcheck.

    Returns:
        ``True`` when at least one running member is unhealthy, ``False`` when
        every running member with a healthcheck passes, and ``None`` when no
        running member defines one - there is no verdict to report then.

    """
    verdicts = [
        (member.get("Health") or {}).get("Status")
        for member in members
        if member.get("State") == "running" and (member.get("Health") or {}).get("Status") != _HEALTH_NOT_CONFIGURED
    ]
    if not verdicts:
        return None
    return "unhealthy" in verdicts


def _carry_forward(
    stacks: list[dict[str, Any]],
    previous: list[dict[str, Any]],
    fields: Iterable[str],
) -> list[dict[str, Any]]:
    """
    Copy a set of fields from the matching stack in the previous poll's data.

    Returns:
        The stacks, each with whichever of `fields` its predecessor carried.

    """
    wanted = list(fields)
    by_name = {stack.get("name"): stack for stack in previous}
    carried: list[dict[str, Any]] = []
    for stack in stacks:
        before = by_name.get(stack.get("name"))
        if before is None:
            carried.append(stack)
            continue
        carried.append({**stack, **{field: before[field] for field in wanted if field in before}})
    return carried


def resolve_stack_icon(stack: dict[str, Any]) -> str | None:
    """
    Return the stack's icon URL if it is one a browser can load.

    Returns:
        The icon URL, or ``None`` when the stack has none usable.

    """
    icon = stack.get("iconUrl")
    if isinstance(icon, str) and icon.startswith(("http://", "https://")):
        return icon
    return None


def resolve_stack_web_ui_url(stack: dict[str, Any], host: str | None) -> str | None:
    """
    Build the clickable web interface URL for a stack, or ``None``.

    A stack's ``webui`` is a finished URL needing only the host substituted, so
    unlike a container's there is no port mapping to consult. A ``[PORT:n]``
    placeholder is therefore unresolvable here and drops the link, on the same
    reasoning as ``resolve_web_ui_url``: a link pointing at the wrong port looks
    like a working one until someone clicks it.

    Returns:
        The resolved URL, or ``None`` when it cannot be determined.

    """
    raw = stack.get("webui")
    if not isinstance(raw, str) or not raw or not isinstance(host, str) or not host:
        return None

    resolved = HOST_PLACEHOLDER.sub(host, raw)
    return None if PORT_PLACEHOLDER.search(resolved) else resolved
