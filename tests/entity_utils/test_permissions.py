"""Tests for the has_write_access token permission helper."""

from __future__ import annotations

import pytest

from custom_components.mos.entity_utils import has_write_access


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
