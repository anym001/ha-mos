"""
Keep a MOS server's container devices in the same area as the server itself.

One MOS server produces a dozen devices - the server, its UPS, one per pool,
disk, container and VM - and Home Assistant has no notion of one device
inheriting anything from another. ``via_device`` links them for display only;
the area is set per device or not at all. So assigning a room means picking the
same room twelve times in the dialog Home Assistant shows after setup, and
picking it again for every pool or container that appears later.

This module makes the server device the one that has to be answered. Set its
area and the rest follow; leave it alone and nothing happens. It cannot remove
that dialog - the list of devices in it comes from Home Assistant's frontend and
no integration can influence it - but it does mean only the first row has to be
filled in, and the rest can be skipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.mos.const import DOMAIN, LOGGER
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry
    from homeassistant.core import Event, HomeAssistant


@callback
def async_setup_area_inheritance(hass: HomeAssistant, entry: MOSConfigEntry) -> None:
    """
    Have this entry's container devices follow the area of its server device.

    Two things are watched, which together cover both ways a device can end up
    in the wrong place:

    - the server device being given an area (or having it cleared), which the
      other devices of the entry then adopt
    - a container device appearing after the fact - a new pool, a VM someone
      just defined, a UPS that was plugged in - which starts out in the server's
      area instead of in none at all

    Args:
        hass: The Home Assistant instance.
        entry: The config entry whose devices should be kept together.

    """

    # Decorated rather than a bare lambda: an undecorated listener is classified
    # as an executor job and run in a worker thread, from where touching the
    # device registry is a thread-safety violation Home Assistant rejects
    # outright.
    @callback
    def _device_registry_updated(event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        _handle_device_registry_updated(hass, entry, event)

    entry.async_on_unload(hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _device_registry_updated))


@callback
def _handle_device_registry_updated(
    hass: HomeAssistant,
    entry: MOSConfigEntry,
    event: Event[dr.EventDeviceRegistryUpdatedData],
) -> None:
    """
    React to one device registry change, if it concerns this entry.

    Every registry change in Home Assistant reaches this, so the cheap
    disqualifiers come first. The updates this handler makes itself land back
    here as further events: those are updates to a *container* device, which no
    branch below acts on, so there is no loop to guard against beyond that.
    """
    # Compared through ``event.data`` rather than a local, so the payload narrows
    # to the variant that actually carries ``changes``.
    if event.data["action"] == "remove":
        return

    device_registry = dr.async_get(hass)
    device = device_registry.async_get(event.data["device_id"])
    if device is None or device.config_entry_id != entry.entry_id:
        return

    server = device_registry.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    if server is None:
        return

    if event.data["action"] == "create":
        _adopt_into_server_area(device_registry, server, device)
    elif device.id == server.id and "area_id" in event.data["changes"]:
        _follow_server_area(device_registry, entry, server, event.data["changes"]["area_id"])


@callback
def _adopt_into_server_area(
    device_registry: dr.DeviceRegistry,
    server: dr.DeviceEntry,
    device: dr.DeviceEntry,
) -> None:
    """
    Put a newly created container device in the server's area.

    Only ever fills a blank. A device that already carries an area was placed
    there by something that knew better than this - a restored registry entry,
    or the user, from the very dialog this exists to shorten.

    During setup this does nothing at all: every device is created before anyone
    has had the chance to give the server an area. It earns its place afterwards,
    for the pool or container that shows up on a Tuesday and would otherwise be
    the one device sitting outside the room the rest of the server is in.
    """
    if device.id == server.id or server.area_id is None or device.area_id is not None:
        return

    LOGGER.debug("Placing new device %s in the server's area %s", device.name, server.area_id)
    device_registry.async_update_device(device.id, area_id=server.area_id)


@callback
def _follow_server_area(
    device_registry: dr.DeviceRegistry,
    entry: MOSConfigEntry,
    server: dr.DeviceEntry,
    previous_area_id: str | None,
) -> None:
    """
    Move this entry's container devices along with the server device.

    Only devices that were in the server's *previous* area are moved, which is
    what keeps this from being a bulk overwrite. A UPS deliberately filed under
    "Basement" while the server sits in "Office" stays in the basement when the
    server later moves to "Study"; everything that was merely following along -
    including everything that had no area, the state after a fresh setup -
    follows again.

    The comparison is against the old value rather than a flag stored somewhere,
    so it needs nothing remembered between restarts and reads the same whether
    the user made their choice through this mechanism or by hand.
    """
    moved = [
        device
        for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        if device.id != server.id and device.area_id == previous_area_id
    ]
    for device in moved:
        device_registry.async_update_device(device.id, area_id=server.area_id)

    # A dozen devices changing room at once is startling to come across, and
    # without this the log holds nothing to explain it. One line for the whole
    # move rather than one per device: they all went to the same place, for the
    # same reason, and the names are what makes the entry answerable.
    if moved:
        LOGGER.debug(
            "Server device moved to area %s, taking %s along",
            server.area_id,
            ", ".join(sorted(device.name or device.id for device in moved)),
        )
