"""Tests for the token permission helpers."""

from __future__ import annotations

import pytest

from custom_components.mos.const import MOS_PERMISSION_RESOURCES, READ_PERMISSION_RESOURCES
from custom_components.mos.entity_utils import has_read_access, has_write_access


def test_mapped_scopes_are_resources_mos_actually_has() -> None:
    """Every scope name the coordinator maps to exists in a MOS permission payload.

    A typo or an invented name cannot fail loudly: `has_read_access` denies only
    an explicit "none", so a name MOS never sends simply never matches and the
    resource is probed as if unscoped. The pre-poll skip then quietly does
    nothing, which is exactly what "services" (MOS calls it "mos") did.
    """
    unknown = {resource for resource in READ_PERMISSION_RESOURCES.values() if resource not in MOS_PERMISSION_RESOURCES}
    assert not unknown, f"mapped to scopes MOS does not have: {sorted(unknown)}"


@pytest.mark.parametrize(
    ("token_permissions", "resource", "expected"),
    [
        (None, "lxc", True),
        ({"mode": "full"}, "docker", True),
        ({"mode": "readonly"}, "lxc", False),
        ({"mode": "readonly"}, "docker", False),
        ({"mode": "custom", "resources": {"lxc": "write"}}, "lxc", True),
        ({"mode": "custom", "resources": {"lxc": "read"}}, "lxc", False),
        ({"mode": "custom", "resources": {"lxc": "none"}}, "lxc", False),
        ({"mode": "custom", "resources": {}}, "lxc", False),
        ({"mode": "custom"}, "lxc", False),
        ({"mode": "custom", "resources": {"docker": "write"}}, "lxc", False),
    ],
)
def test_has_write_access(token_permissions: dict | None, resource: str, expected: bool) -> None:
    """has_write_access matches the MOS TokenPermissions semantics for each mode."""
    assert has_write_access(token_permissions, resource) is expected


@pytest.mark.parametrize(
    ("token_permissions", "resource", "expected"),
    [
        (None, "lxc", True),
        ({"mode": "full"}, "docker", True),
        # readonly withholds writes, not reads.
        ({"mode": "readonly"}, "lxc", True),
        ({"mode": "custom", "resources": {"lxc": "write"}}, "lxc", True),
        ({"mode": "custom", "resources": {"lxc": "read"}}, "lxc", True),
        ({"mode": "custom", "resources": {"lxc": "none"}}, "lxc", False),
        # Absent means "let the server decide", unlike has_write_access. Guessing
        # denied here would silently drop entities whenever a resource name in
        # READ_PERMISSION_RESOURCES stops matching what MOS calls it.
        ({"mode": "custom", "resources": {}}, "lxc", True),
        ({"mode": "custom"}, "lxc", True),
        ({"mode": "custom", "resources": {"docker": "none"}}, "lxc", True),
    ],
)
def test_has_read_access(token_permissions: dict | None, resource: str, expected: bool) -> None:
    """has_read_access denies only an explicit "none", so an unknown name stays readable."""
    assert has_read_access(token_permissions, resource) is expected
