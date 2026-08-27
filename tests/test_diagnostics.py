"""Tests for the config entry diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mos.const import CONF_API_TOKEN
from custom_components.mos.diagnostics import async_get_config_entry_diagnostics
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr

REDACTED = "**REDACTED**"


async def test_api_token_is_redacted(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The API token never appears in diagnostics output."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert diagnostics["entry"]["data"][CONF_API_TOKEN] == REDACTED
    assert "test-token" not in str(diagnostics)


async def test_host_is_redacted_everywhere(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The configured host does not survive anywhere in the dump, base URLs included."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert diagnostics["entry"]["data"][CONF_HOST] == REDACTED
    assert diagnostics["api"]["base_url"] == REDACTED
    assert diagnostics["api"]["root_base_url"] == REDACTED
    assert "10.0.1.30" not in str(diagnostics)


async def test_container_bind_address_is_redacted(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_client: AsyncMock,
    mock_docker_engine_containers: list[dict],
) -> None:
    """A container published on one interface carries that address in its port list.

    Docker spells the key ``IP``, which does not match the lower-case ``ip``
    the rest of the payloads use - and the redaction compares key names exactly.
    """
    bound = {
        **mock_docker_engine_containers[0],
        "Ports": [{"IP": "192.168.178.42", "PrivatePort": 8080, "PublicPort": 8081, "Type": "tcp"}],
    }
    mock_client.async_get_docker_engine_containers.return_value = [bound, mock_docker_engine_containers[1]]
    await setup_integration.runtime_data.coordinator.async_refresh()

    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert "192.168.178.42" not in str(diagnostics)


async def test_guest_icon_url_is_redacted(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    setup_integration: MockConfigEntry,
) -> None:
    """A resolved icon URL is built from the host, exactly like ``web_ui_url``, and must not survive either."""
    mock_client.async_static_asset_exists.return_value = True
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    data_sample = diagnostics["data_sample"]
    assert all(container["icon_url"] == REDACTED for container in data_sample["lxc_containers"])
    assert all(machine["icon_url"] == REDACTED for machine in data_sample["vm_machines"])
    assert all(container["icon_url"] == REDACTED for container in data_sample["docker_containers"])
    assert "10.0.1.30" not in str(diagnostics)


async def test_connection_details_stay_visible(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Redacting the host must not cost the fields connection triage actually needs."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    entry_data = diagnostics["entry"]["data"]
    assert entry_data["port"] == 80
    assert entry_data["ssl"] is False
    assert entry_data["verify_ssl"] is True
    assert diagnostics["api"]["has_token"] is True


async def test_hardware_and_network_identifiers_are_redacted(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Hostname, disk serials and container addresses are stripped from the payloads."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)
    data_sample = diagnostics["data_sample"]

    assert data_sample["osinfo"]["hostname"] == REDACTED
    assert all(disk["serial"] == REDACTED for disk in data_sample["disks"])
    assert all(container["network"] == REDACTED for container in data_sample["lxc_containers"])
    # Nested blocks are reached too, not just top-level keys.
    assert data_sample["nut"]["data"]["serial"] == REDACTED
    # The address itself, not just the key holding it.
    assert "192.168.1.100" not in str(diagnostics)


async def test_last_exception_has_the_host_scrubbed(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The host is removed from the free-form error message, which keys cannot cover."""
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.last_exception = ConnectionError("Cannot connect to host 10.0.1.30:80 ssl:default")

    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    last_exception = diagnostics["error"]["last_exception"]
    assert "10.0.1.30" not in last_exception
    # The rest of the message survives - it is the most useful line for triage.
    assert "Cannot connect to host" in last_exception
    assert diagnostics["error"]["last_exception_type"] == "ConnectionError"


async def test_data_sample_includes_all_resources(
    *,
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_services: dict,
    mock_disks: list[dict],
    mock_pools: list[dict],
    mock_system_load: dict,
    mock_lxc_containers: list[dict],
    mock_docker_containers: list[dict],
    mock_vm_machines: list[dict],
    mock_sensors: dict[str, list[dict]],
    mock_nut: dict,
) -> None:
    """The data sample surfaces every polled resource alongside osinfo."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    data_sample = diagnostics["data_sample"]
    # Payloads carrying no redacted key come through untouched.
    assert data_sample["services"] == mock_services
    assert data_sample["pools"] == mock_pools
    assert data_sample["system_load"] == mock_system_load
    # ``icon_url`` is added by the coordinator, and is None here because
    # ``mock_client`` answers "no such file" for every icon probe.
    assert data_sample["vm_machines"] == [{**machine, "icon_url": None} for machine in mock_vm_machines]
    # Complete but for the UPS serial (see test_hardware_and_network_identifiers_are_redacted).
    assert data_sample["nut"] == {**mock_nut, "data": {**mock_nut["data"], "serial": REDACTED}}
    # sensors arrives flattened across its categories, one entry per reading.
    assert [item["id"] for item in data_sample["sensors"]] == [
        item["id"] for items in mock_sensors.values() for item in items
    ]
    # docker_containers has a "state" field merged in from the Docker Engine proxy.
    assert {c["name"] for c in data_sample["docker_containers"]} == {c["name"] for c in mock_docker_containers}
    assert all("state" in c for c in data_sample["docker_containers"])
    # The rest are present and complete; only their identifying fields are
    # redacted (see test_hardware_and_network_identifiers_are_redacted).
    assert [disk["name"] for disk in data_sample["disks"]] == [disk["name"] for disk in mock_disks]
    assert [c["name"] for c in data_sample["lxc_containers"]] == [c["name"] for c in mock_lxc_containers]
    assert data_sample["osinfo"]["mos"] == {
        "version": "0.5.0-stable",
        "channel": "stable",
        "build": "20260705-1111",
        "api": "1.4.0",
        "frontend": "1.4.0",
        "running_kernel": "6.1.0-mos",
        "recommended_kernel": "6.1.0-mos",
        "arch": "x86_64",
    }


async def test_token_permissions_are_included(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_token_permissions: dict,
) -> None:
    """The token's permission scope is surfaced, but not the token's identity."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    token_permissions = diagnostics["api"]["token_permissions"]
    # The scope itself is the point of the field and stays readable.
    assert token_permissions["permissions"] == mock_token_permissions["permissions"]
    assert token_permissions["role"] == mock_token_permissions["role"]
    assert token_permissions["isBootToken"] == mock_token_permissions["isBootToken"]
    # The id/name identify the specific credential on the server.
    assert token_permissions["id"] == REDACTED
    assert token_permissions["name"] == REDACTED
    assert mock_token_permissions["id"] not in str(diagnostics)


async def test_devices_and_entities_are_reported(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The server device plus one device per disk/pool/LXC/Docker/Compose/VM/UPS item are reported."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)

    # 1 server device + 2 disks + 2 pools + 2 LXC containers + 2 Docker containers
    # + 2 Compose stacks + 2 VMs + 1 UPS.
    assert len(diagnostics["devices"]) == 14
    for device in diagnostics["devices"]:
        assert device["entity_count"] > 0


async def test_a_renamed_device_is_reported_as_renamed(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A user-set device name and area are reported next to the integration's own name.

    Home Assistant freezes an entity_id at registration from
    ``name_by_user or name``, so a device renamed part-way through its life
    leaves entity_ids carrying a name that appears nowhere else in the dump.
    Reporting the override is what makes those entity_ids explicable - and
    reporting the area is what rules it out as the cause, since a room name
    that matches the rename looks like the culprit but never reaches an
    entity_id.
    """
    device_registry = dr.async_get(hass)
    server = device_registry.async_get_device_by_identifier(
        ("mos", setup_integration.entry_id), setup_integration.entry_id
    )
    area = ar.async_get(hass).async_create("Control room")
    device_registry.async_update_device(server.id, name_by_user="Control room Sirius", area_id=area.id)

    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)
    devices = {device["id"]: device for device in diagnostics["devices"]}

    assert devices[server.id]["name"] == "Sirius"
    assert devices[server.id]["name_by_user"] == "Control room Sirius"
    assert devices[server.id]["area_id"] == area.id
    # An untouched device reports the absence rather than leaving the reader to
    # guess whether the field was omitted or the override simply is not set.
    ups = next(device for device in diagnostics["devices"] if device["name"] == "Sirius UPS")
    assert ups["name_by_user"] is None
    # Its area is not untouched, though: the container devices follow the server
    # into a room (see async_setup_area_inheritance), so the dump showing them
    # all in the same area is the expected picture rather than a sign that the
    # user filed each one by hand.
    assert ups["area_id"] == area.id
