"""Diagnostics support for mos.

Learn more about diagnostics:
https://developers.home-assistant.io/docs/core/integration_diagnostics
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_API_TOKEN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MOSConfigEntry

# Fields to redact from diagnostics - CRITICAL for security!
TO_REDACT = {
    CONF_API_TOKEN,
    "api_token",
    "token",
    "api_key",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: MOSConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client
    integration = entry.runtime_data.integration

    # Get device and entity information
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    # Find all devices for this integration
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_info = []
    for device in devices:
        entities = er.async_entries_for_device(entity_reg, device.id)
        device_info.append(
            {
                "id": device.id,
                "name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "sw_version": device.sw_version,
                "entity_count": len(entities),
                "entities": [
                    {
                        "entity_id": entity.entity_id,
                        "platform": entity.platform,
                        "original_name": entity.original_name,
                        "disabled": entity.disabled,
                        "disabled_by": entity.disabled_by.value if entity.disabled_by else None,
                    }
                    for entity in entities
                ],
            }
        )

    # Coordinator statistics
    now = time.monotonic()
    coordinator_info = {
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "data_keys": list(coordinator.data.keys()) if isinstance(coordinator.data, dict) else None,
        # Resources currently failing but still inside the grace period, with how
        # long and how often each has been failing, followed by those that have
        # exceeded it and whose entities are therefore unavailable. Together these
        # answer the two questions a "some of my entities went unavailable"
        # report raises: which resource, and for how long.
        "degraded_resources": {
            key: {"failures": streak.failures, "failing_for_seconds": round(now - streak.started_at)}
            for key, streak in coordinator._degraded_resources.items()  # noqa: SLF001
        },
        "stale_resources": sorted(coordinator.stale_resources),
    }

    # API client information (no sensitive data)
    api_info = {
        "base_url": client._base_url,  # noqa: SLF001
        "root_base_url": client._root_base_url,  # noqa: SLF001
        "has_token": bool(client._token),  # noqa: SLF001
        "token_permissions": coordinator.token_permissions,
        # Resources dropped because the server answered 403. The fastest way to
        # tell "my entities are missing" apart from "my token is too narrow".
        "forbidden_resources": sorted(coordinator.forbidden_resources),
    }

    # Integration information
    integration_info = {
        "name": integration.name,
        "version": integration.version,
        "domain": integration.domain,
        "documentation": integration.documentation,
        "issue_tracker": integration.issue_tracker,
    }

    # Config entry details (with redacted sensitive data)
    entry_info = {
        "entry_id": entry.entry_id,
        "version": entry.version,
        "minor_version": entry.minor_version,
        "domain": entry.domain,
        "title": entry.title,
        "state": str(entry.state),
        "unique_id": entry.unique_id,
        "disabled_by": entry.disabled_by.value if entry.disabled_by else None,
        "data": async_redact_data(entry.data, TO_REDACT),
        "options": async_redact_data(entry.options, TO_REDACT),
    }

    # Error information
    error_info = {
        "last_exception": str(coordinator.last_exception) if coordinator.last_exception else None,
        "last_exception_type": (type(coordinator.last_exception).__name__ if coordinator.last_exception else None),
    }

    # Current data sample: the full osinfo payload minus the large package list,
    # plus the other polled resources (no sensitive data in any of these)
    data_sample: dict[str, Any] = {}
    if isinstance(coordinator.data, dict):
        osinfo = dict(coordinator.data.get("osinfo") or {})
        base = osinfo.get("base")
        if isinstance(base, list):
            osinfo["base"] = [
                {key: value for key, value in entry_item.items() if key != "packages"}
                for entry_item in base
                if isinstance(entry_item, dict)
            ]
        data_sample = {
            "osinfo": osinfo,
            "services": coordinator.data.get("services"),
            "disks": coordinator.data.get("disks"),
            "pools": coordinator.data.get("pools"),
            "system_load": coordinator.data.get("system_load"),
            "lxc_containers": coordinator.data.get("lxc_containers"),
            "docker_containers": coordinator.data.get("docker_containers"),
            "vm_machines": coordinator.data.get("vm_machines"),
        }

    return {
        "entry": entry_info,
        "integration": integration_info,
        "coordinator": coordinator_info,
        "api": api_info,
        "devices": device_info,
        "data_sample": data_sample,
        "error": error_info,
    }
