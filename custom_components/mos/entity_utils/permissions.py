"""Token permission helpers for mos.

MOS admin tokens can be scoped (see ``GET /auth/admin-tokens/me``): ``null``
or mode ``"full"`` grants unrestricted access, ``"readonly"`` blocks all
writes, and ``"custom"`` grants per-resource ``"none"``/``"read"``/``"write"``
levels. Write actions (LXC/Docker start/stop) must check this before
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
            ``TokenPermissions.resources`` (e.g. ``"lxc"``, ``"docker"``).

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
