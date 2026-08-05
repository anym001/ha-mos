"""
Custom types for mos.

This module defines the runtime data structure attached to each config entry.
Access pattern: entry.runtime_data.client / entry.runtime_data.coordinator

The MOSConfigEntry type alias is used throughout the integration
for type-safe access to the config entry's runtime data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import MOSApiClient
    from .coordinator import MOSDataUpdateCoordinator


type MOSConfigEntry = ConfigEntry[MOSData]


@dataclass
class MOSData:
    """Runtime data for mos config entries.

    Stored as entry.runtime_data after successful setup.
    Provides typed access to the API client and coordinator instances.
    """

    client: MOSApiClient
    coordinator: MOSDataUpdateCoordinator
    integration: Integration


@dataclass(frozen=True, kw_only=True)
class MOSDeviceHardware:
    """The maker of a container device, for the ones MOS did not make itself.

    Container devices are MOS's own by default - a pool, an LXC container, a
    VM exist because MOS provides them, so "MOS" is the honest manufacturer.
    A UPS is not one of those: it is third-party hardware MOS merely talks to
    over NUT, and labelling it MOS would put the wrong name on the device page
    while its real maker sat in a sensor row underneath.

    Fields left empty are simply omitted rather than guessed at: not every NUT
    driver reports all three.

    Lives here rather than next to MOSEntity because both the entity base and
    the UPS helper that fills it in need it, and entity_utils is imported by
    the coordinator - importing the entity package from there would close a
    cycle.
    """

    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
