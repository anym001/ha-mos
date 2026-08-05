"""Token permission helpers for mos.

MOS admin tokens can be scoped (see ``GET /auth/admin-tokens/me``): ``null``
or mode ``"full"`` grants unrestricted access, ``"readonly"`` blocks all
writes, and ``"custom"`` grants per-resource ``"none"``/``"read"``/``"write"``
levels. All three mode strings are confirmed against MOS 0.5.x, where ``"full"``
and ``"readonly"`` carry no ``resources`` block at all - only ``"custom"`` does,
which is why only that mode is ever asked for one. Write actions (LXC/Docker/VM start/stop) must check this before
attempting the API call - not just for a nicer error message, but because a
write attempt with an insufficiently-scoped token would otherwise fail with a
generic 401/403 from the server instead of a clear, actionable one from here.
"""

from __future__ import annotations

from typing import Any


def has_write_access(token_permissions: dict[str, Any] | None, resource: str) -> bool:
    """
    Return whether the token backing this integration may write to `resource`.

    Args:
        token_permissions: The coordinator's cached token permission scope
            (see ``MOSDataUpdateCoordinator.token_permissions``). ``None``
            when introspection is unavailable (older MOS servers, or the
            lookup failed) - treated as unrestricted, matching the server's
            own "null = full access" semantics.
        resource: A MOS API resource name as used in
            ``TokenPermissions.resources`` (e.g. ``"lxc"``, ``"docker"``,
            ``"vm"``).

    Returns:
        True if the token may perform write actions against `resource`.

    """
    if token_permissions is None:
        return True

    mode = token_permissions.get("mode", "full")
    if mode == "readonly":
        return False
    if mode == "custom":
        resources = token_permissions.get("resources") or {}
        return resources.get(resource) == "write"
    # "full" (or any unrecognized future mode) - unrestricted.
    return True


def has_read_access(token_permissions: dict[str, Any] | None, resource: str) -> bool:
    """
    Return whether the token backing this integration may read `resource`.

    Deliberately more optimistic than `has_write_access`: only an explicit
    ``"none"`` counts as denied. A resource that is simply absent from a
    ``"custom"`` scope is treated as readable and left for the server to refuse,
    which the coordinator then records permanently (see
    ``_absorb_scope_denials``). MOS does leave names out that it enforces - 0.5.x
    omits ``nut`` entirely - so this is the normal path for those, not an edge
    case: one wasted request per reload, and the entities are gone from then on
    just as if the scope had said so.

    The asymmetry is on purpose. For writes, guessing wrong means one switch
    reports a clear error instead of a cryptic one. For reads, guessing wrong
    means silently disabling whole categories of entities. The names in
    ``READ_PERMISSION_RESOURCES`` are confirmed against MOS 0.5.x, but a future
    server that renames or splits a resource would otherwise take those entities
    with it; being permissive keeps such a mismatch harmless.

    Args:
        token_permissions: The token's permission scope, i.e. the ``permissions``
            payload of ``GET /auth/admin-tokens/me``. ``None`` when
            introspection is unavailable - treated as unrestricted.
        resource: A MOS API resource name as used in ``TokenPermissions.resources``.

    Returns:
        True unless the scope explicitly denies reading `resource`.

    """
    if token_permissions is None:
        return True

    # "readonly" grants reads; only "custom" can withhold them per resource.
    if token_permissions.get("mode", "full") == "custom":
        resources = token_permissions.get("resources") or {}
        return resources.get(resource) != "none"
    return True
