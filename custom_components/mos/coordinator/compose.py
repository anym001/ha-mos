"""
Docker Compose stack shaping for mos.

A stack is not a container, and MOS keeps the two apart: a compose stack never
appears in ``/docker/mos/containers``, and its member containers carry generated
names (``compose_<stack>-<service>-1``) that have no MOS template behind them.
What a stack does have is a single ``running`` flag covering all of its
services, which is also the only thing MOS lets a caller change - start and stop
act on the whole stack.

The one piece the stack list does not carry is update tracking. MOS creates a
container group per stack automatically, and that group holds
``update_available`` alongside the running/total counters, so the two lists are
joined here into the payload the entities read.
"""

from __future__ import annotations

from typing import Any

from custom_components.mos.coordinator.docker_templates import HOST_PLACEHOLDER, PORT_PLACEHOLDER

# Group fields lifted onto a stack, under the names the entities use.
_GROUP_FIELDS = {
    "update_available": "update_available",
    "count": "container_count",
    "runningCount": "running_containers",
}


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
    request would blank the update flag and both counters on every stack while
    the stack list itself answered fine.

    Returns:
        The stacks, each with the ``_GROUP_FIELDS`` it had last poll.

    """
    by_name = {stack.get("name"): stack for stack in previous}
    carried: list[dict[str, Any]] = []
    for stack in stacks:
        before = by_name.get(stack.get("name"))
        if before is None:
            carried.append(stack)
            continue
        carried.append({**stack, **{field: before[field] for field in _GROUP_FIELDS.values() if field in before}})
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
