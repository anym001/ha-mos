"""Helpers for reading the ``/nut/status`` payload, shared by the UPS platforms.

The sensor and binary sensor platforms both need the same three things out of
the payload - is a UPS there at all, what does its ``data`` block say, and which
NUT status flags are currently set - so those live here rather than being
duplicated (or imported across platform packages).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from custom_components.mos.coordinator import MOSDataUpdateCoordinator


def nut_payload(coordinator: MOSDataUpdateCoordinator) -> dict[str, Any]:
    """
    Return the current ``/nut/status`` payload.

    Empty when the resource is disabled, was never fetched, or failed on the
    very first poll - all of which read as "no UPS" downstream.
    """
    return (coordinator.data or {}).get("nut") or {}


def nut_data(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return the payload's parsed ``data`` block.

    Absent or ``null`` when the UPS is unreachable, hence the fallback: value
    functions can then read it unconditionally and simply produce ``None``.
    """
    return payload.get("data") or {}


def is_ups_reachable(payload: dict[str, Any]) -> bool:
    """Return whether MOS could talk to a UPS on the last poll."""
    return bool(payload.get("reachable"))


def nut_status_flags(payload: dict[str, Any]) -> frozenset[str]:
    """
    Return the UPS's NUT status flags as a set.

    NUT reports ``ups.status`` as space-separated flags and several apply at
    once ("OB LB" while discharging on a nearly empty battery, "OL CHRG" while
    recharging after that), so membership - not equality against the raw string
    - is what the binary sensors have to test.
    """
    status = payload.get("status")
    if not isinstance(status, str):
        return frozenset()
    return frozenset(status.split())
