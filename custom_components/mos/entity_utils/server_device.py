"""
The device representing the MOS server itself.

Every other device of an entry - UPS, pools, disks, containers, VMs - links back
to this one, and Home Assistant wants that link as the server device's registry
id. The id only exists once the device is registered, so the entry registers it
during setup, before the platforms build anything that has to point at it.

The same description is what the server's own entities publish as their
``DeviceInfo``, so it is built here once and used from both places.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from custom_components.mos.const import DEFAULT_SSL
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

if TYPE_CHECKING:
    from custom_components.mos.data import MOSConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass(frozen=True, kw_only=True)
class _ServerDeviceFields:
    """The server device's registry fields, named the way both consumers take them."""

    identifiers: set[tuple[str, str]]
    name: str | None
    manufacturer: str
    model: str | None
    sw_version: str | None
    configuration_url: str | None


def _server_device_fields(entry: MOSConfigEntry, data: dict[str, Any] | None) -> _ServerDeviceFields:
    """Read the server device's fields out of the config entry and coordinator data."""
    osinfo: dict = (data or {}).get("osinfo", {})
    mos: dict = osinfo.get("mos", {})

    host = entry.data.get(CONF_HOST)
    scheme = "https" if entry.data.get(CONF_SSL, DEFAULT_SSL) else "http"
    port = entry.data.get(CONF_PORT)
    configuration_url = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"

    return _ServerDeviceFields(
        identifiers={
            (
                entry.domain,
                entry.entry_id,
            ),
        },
        name=entry.title or osinfo.get("hostname"),
        manufacturer="MOS",
        model=mos.get("version"),
        sw_version=mos.get("build"),
        configuration_url=configuration_url if host else None,
    )


def server_device_info(entry: MOSConfigEntry, data: dict[str, Any] | None) -> DeviceInfo:
    """
    Describe the MOS server device.

    Args:
        entry: The config entry the server belongs to.
        data: Coordinator data, read for the MOS version and build.

    Returns:
        The ``DeviceInfo`` the server's own entities publish.

    """
    return DeviceInfo(**asdict(_server_device_fields(entry, data)))


@callback
def async_register_server_device(hass: HomeAssistant, entry: MOSConfigEntry) -> str:
    """
    Register the server device, so container devices have an id to link back to.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being set up.

    Returns:
        The device registry id of the server device.

    """
    fields = _server_device_fields(entry, entry.runtime_data.coordinator.data)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=fields.identifiers,
        name=fields.name,
        manufacturer=fields.manufacturer,
        model=fields.model,
        sw_version=fields.sw_version,
        configuration_url=fields.configuration_url,
    )
    return device.id
