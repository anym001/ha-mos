"""Helpers for reading the ``/nut/status`` payload, shared by the UPS platforms.

The sensor and binary sensor platforms both need the same things out of the
payload - is a UPS there at all, what does its ``data`` block say, which NUT
status flags are currently set - plus the same deferred setup, so those live
here rather than being duplicated (or imported across platform packages).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.mos.const import LOGGER
from custom_components.mos.data import MOSDeviceHardware
from homeassistant.core import callback

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from custom_components.mos.coordinator import MOSDataUpdateCoordinator
    from custom_components.mos.data import MOSConfigEntry
    from custom_components.mos.entity import MOSEntity
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


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


def nut_device_hardware(coordinator: MOSDataUpdateCoordinator) -> MOSDeviceHardware:
    """
    Return the UPS's own maker, model and serial for its device entry.

    The same three values are also sensors, deliberately: the device page shows
    them once at the top where HA shows every other device's hardware, and the
    sensors keep them readable from a template or a dashboard. Both read the
    payload, so neither can drift from the other.

    Read once, when the entities are constructed. That is enough because these
    only change if the UPS itself is swapped, which means a different unit on
    the same NUT name - and a reload (or restart) re-registers the device with
    the new values.
    """
    data = nut_data(nut_payload(coordinator))
    return MOSDeviceHardware(
        manufacturer=data.get("manufacturer"),
        model=data.get("model"),
        serial_number=data.get("serial"),
    )


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


@callback
def async_setup_ups_entities(
    entry: MOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
    entity_factory: Callable[[MOSDataUpdateCoordinator], Sequence[MOSEntity]],
) -> None:
    """
    Create the UPS entities once a UPS has actually answered, not before.

    ``/nut/status`` answers on every MOS server that has the endpoint at all,
    with ``reachable: false`` when nothing is attached - and servers too old to
    have it answer 404, which the coordinator turns into an empty payload that
    reads the same way. Creating the entities up front would therefore give a
    server with no UPS (or no NUT support yet) a full set of permanently
    unavailable entities, which is noise rather than information.

    Waiting for the first ``reachable: true`` instead means the entities exist
    only where there is something to show. From that point on they behave like
    every other fixed entity in this integration: they stay put, and a UPS that
    later stops answering leaves them unavailable rather than removing them, so
    history, custom names and automations survive it. Only the connectivity
    sensor keeps reporting - saying "not connected" is its whole job.

    Unlike ``async_setup_dynamic_entities`` this never removes anything, so the
    listener has nothing left to do once it has fired; it is kept subscribed
    anyway (guarded by ``added``) rather than unsubscribing itself, since
    removing a coordinator listener from inside its own callback is easy to get
    wrong for no gain.

    Args:
        entry: The config entry these entities belong to.
        async_add_entities: Callback to register newly created entities.
        entity_factory: Builds this platform's UPS entities for a coordinator.

    """
    coordinator = entry.runtime_data.coordinator
    added = False

    @callback
    def _add_once_reachable() -> None:
        nonlocal added
        if added or not is_ups_reachable(nut_payload(coordinator)):
            return
        added = True
        LOGGER.debug("UPS reachable - creating its entities")
        async_add_entities(entity_factory(coordinator))

    # Checked once up front for the normal case (a UPS was already there on the
    # first poll, which has run by the time platforms are set up), then on every
    # subsequent poll for one that is attached later - or a MOS server that
    # learns the endpoint in an update. Neither needs a reload.
    _add_once_reachable()
    entry.async_on_unload(coordinator.async_add_listener(_add_once_reachable))
