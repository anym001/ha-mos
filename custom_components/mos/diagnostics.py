"""Diagnostics support for mos.

Learn more about diagnostics:
https://developers.home-assistant.io/docs/core/integration_diagnostics
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.redact import REDACTED, async_redact_data

from .const import CONF_API_TOKEN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MOSConfigEntry

# Fields to redact from diagnostics - CRITICAL for security!
#
# Applied to the *whole* diagnostics payload, not just the config entry, because
# a dump is something users attach to public GitHub issues (the bug report
# template asks for one by name). Two classes of field are covered:
#
# 1. The credential itself. Non-negotiable.
# 2. Identifiers that locate the machine or its hardware - hostname, the host
#    part of the API base URLs, disk serials, container addresses. None of these
#    are secrets, but together they describe someone's private network to
#    whoever reads the issue, and none of them are needed to debug the
#    integration: the entry's `port`, `ssl` and `verify_ssl` stay visible, which
#    is what connection triage actually needs.
#
# Redaction is by key name and recurses into nested dicts and lists, so a key
# listed here is covered wherever it appears in a payload.
TO_REDACT = {
    CONF_API_TOKEN,
    "api_token",
    "token",
    "api_key",
    # Host / connection identity
    CONF_HOST,
    "hostname",
    "base_url",
    "root_base_url",
    # A Docker container's resolved web interface link. Unlike the raw
    # ``mos.webui`` label it is built from, the placeholders are gone by the time
    # it reaches the dump and the configured host is spelled out in it.
    "web_ui_url",
    # Network addresses (e.g. an LXC container's `network` block, which is
    # nothing but addresses)
    "network",
    "ip",
    # Docker spells it uppercase in a container's published-port list, and the
    # redaction matches key names exactly. A container bound to one interface
    # rather than 0.0.0.0 carries that interface's address here.
    "IP",
    "ipv4",
    "ipv6",
    "ip_address",
    "ipAddress",
    "mac",
    "mac_address",
    "macAddress",
    # Hardware identity
    "serial",
    "serial_number",
    "serialNumber",
    "uuid",
    "wwn",
}

# Redacted from the token permission payload only.
#
# `GET /auth/admin-tokens/me` returns the token's `id` and `name` next to the
# permission scope. Neither is the secret, but both identify the specific
# credential on the server. They are handled here rather than in TO_REDACT
# because "id" and "name" are far too common elsewhere in the payload - putting
# them in the global set would blank out every device, container and pool name
# in the dump.
TOKEN_IDENTITY_TO_REDACT = {
    "id",
    "name",
}


def _scrub_host(text: str | None, host: str | None) -> str | None:
    """
    Replace the configured host inside a free-form string with the redaction marker.

    ``async_redact_data`` works on key names, so it cannot help with a value
    that merely *contains* the host - and the coordinator's last exception
    routinely does: aiohttp's connection errors carry "Cannot connect to host
    10.0.1.30:80" in their message. Blanking the whole field instead would take
    the single most useful line for triage with it.

    Args:
        text: The free-form text to scrub, if any.
        host: The configured host to look for, if any.

    Returns:
        `text` with every occurrence of `host` replaced, or `text` unchanged
        when there is nothing to do.

    """
    if not text or not host:
        return text
    return text.replace(host, REDACTED)


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
                # The name the user gave the device, and the area it sits in.
                # Neither is set by this integration, which is exactly why they
                # belong in a dump: Home Assistant derives an entity_id from
                # `name_by_user or name` at the moment an entity is first
                # registered and then freezes it. A device renamed part-way
                # through its life therefore ends up with entity_ids carrying a
                # name that appears nowhere else - the older ones from before
                # the rename, the newer ones from after it. Without these two
                # fields such a dump reads as if the integration had invented
                # the prefix itself, and the area is the first thing suspected
                # when it happens to match the room the server sits in.
                "name_by_user": device.name_by_user,
                "area_id": device.area_id,
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
        # Endpoints this server's MOS version does not have. Answers the other
        # half of "why do I not have these entities" - too old a server, rather
        # than too narrow a token (which is `forbidden_resources` below).
        "unsupported_resources": sorted(coordinator.unsupported_resources),
    }

    # API client information. The token is reduced to "is one configured at
    # all"; the base URLs and the token's identity fields are redacted on the
    # way out (see TO_REDACT / TOKEN_IDENTITY_TO_REDACT).
    api_info = {
        "base_url": client._base_url,  # noqa: SLF001
        "root_base_url": client._root_base_url,  # noqa: SLF001
        "has_token": bool(client._token),  # noqa: SLF001
        "token_permissions": (
            async_redact_data(coordinator.token_permissions, TOKEN_IDENTITY_TO_REDACT)
            if coordinator.token_permissions is not None
            else None
        ),
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
        "data": entry.data,
        "options": entry.options,
    }

    # Error information. The message is free-form text rather than a keyed
    # field, so the host has to be scrubbed out of it explicitly.
    error_info = {
        "last_exception": _scrub_host(
            str(coordinator.last_exception) if coordinator.last_exception else None,
            entry.data.get(CONF_HOST),
        ),
        "last_exception_type": (type(coordinator.last_exception).__name__ if coordinator.last_exception else None),
    }

    # Current data sample: the full osinfo payload minus the large package list,
    # plus the other polled resources. These are raw server payloads and do
    # carry host identifiers (hostname, disk serials, container addresses); the
    # redaction pass at the end of this function is what keeps them out.
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
            "sensors": coordinator.data.get("sensors"),
            "nut": coordinator.data.get("nut"),
        }

    # One redaction pass over everything, rather than per-section: a dump is
    # only as safe as the section someone forgot to wrap, and new sections get
    # added over time.
    return async_redact_data(
        {
            "entry": entry_info,
            "integration": integration_info,
            "coordinator": coordinator_info,
            "api": api_info,
            "devices": device_info,
            "data_sample": data_sample,
            "error": error_info,
        },
        TO_REDACT,
    )
