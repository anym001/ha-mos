# Configuration Reference

Every setting the MOS integration offers, and what it does. For installation and first setup, see [GETTING_STARTED.md](./GETTING_STARTED.md).

## Connection Settings

Asked during setup, changeable later via **⋮** → **Reconfigure** on the integration.

| Option                     | Type    | Required | Default             | Description                                            |
| -------------------------- | ------- | -------- | ------------------- | ------------------------------------------------------ |
| **Name**                   | string  | Yes      | –                   | Friendly name for this server; becomes the device name |
| **Host**                   | string  | Yes      | –                   | Hostname or IP address of the MOS server               |
| **API token**              | string  | Yes      | –                   | Admin API token, created in the MOS web UI             |
| **Port**                   | integer | No       | 80 (HTTP)/443 (TLS) | Port the MOS API listens on                            |
| **Use HTTPS**              | boolean | No       | off                 | Connect via TLS                                        |
| **Verify TLS certificate** | boolean | No       | on                  | Turn off only for a self-signed certificate you trust  |

Create the API token in the MOS web UI under **User Settings → Admin API Tokens**. A read-only token is enough for monitoring; starting and stopping containers or VMs needs write access to the respective resource.

## Options

Click **Configure** on the integration to change these at any time. The integration reloads itself, so changes take effect immediately.

| Option                       | Type              | Default | Description                                        |
| ---------------------------- | ----------------- | ------- | -------------------------------------------------- |
| **Update interval**          | integer (seconds) | 30      | How often to poll the MOS API (30–3600 seconds)    |
| **Enable disks**             | boolean           | on      | Create entities for physical disks                 |
| **Enable storage pools**     | boolean           | on      | Create entities for storage pools                  |
| **Enable services**          | boolean           | on      | Docker, VM, SSH, Samba, NFS, Tailscale, Netbird    |
| **Enable LXC containers**    | boolean           | on      | Create entities and switches for LXC containers    |
| **Enable Docker containers** | boolean           | on      | Create entities and switches for Docker containers |
| **Enable VMs**               | boolean           | on      | Create entities and switches for virtual machines  |

System info and system health (CPU load and temperature, memory, swap) are always enabled and have no toggle.

Turning a category off means it is not fetched at all — useful if you don't run LXC or VMs, or want to keep the entity list short.

### Polling Behavior

The integration polls; there is no push from the server.

- **Minimum:** 30 seconds — anything faster mostly adds load without adding information
- **Default:** 30 seconds, a good fit for container and VM states you want to react to
- **Longer intervals** (5–30 minutes) are fine if you only track slow-moving values like disk temperature or pool usage

Start/stop switches don't wait for the next poll: the new state is shown immediately and confirmed by the following update.

## Behavior When the Server Is Unreachable

If the MOS server doesn't answer, entities become **unavailable** and the integration keeps retrying. Nothing needs to be done — the entities come back on their own.

The same holds when a restarting server briefly rejects the API token: the integration rides that out for about five minutes before it asks you to re-authenticate. Only a token that stays rejected — expired, revoked, deleted — leads to a reauthentication prompt under **Settings** → **Devices & Services**.

## Entities

### Renaming, Icons, Areas

Entities are customized like any other Home Assistant entity: **Settings** → **Devices & Services** → **Entities**, click the entity, then the gear icon to change entity ID, name, icon or area.

### Disabling Individual Entities

Entities you don't need can be disabled in the same dialog via **Enabled**. Disabled entities are no longer updated. To remove a whole category at once, use the options above instead.

Disks, pools, containers and VMs appear and disappear on their own as they change on the server — no reload needed.

## Multiple Servers

Add the integration more than once to monitor several MOS servers. Each server becomes its own device with its own entities; the name you give during setup keeps the entity IDs apart.

## Diagnostics

**Settings** → **Devices & Services** → **MOS** → **⋮** → **Download diagnostics** produces a JSON file containing:

- Config entry data (host, port, TLS settings — the API token is redacted)
- Coordinator status: last update successful, update interval, fetched resource categories
- The token's permission scope
- Devices and entities created by the integration, including disabled ones
- Integration and Home Assistant version

**Privacy note:** the file contains host names and your container, VM, pool and disk names. The API token is redacted, but review the file before posting it publicly.

## Troubleshooting

### Integration Won't Load

1. Is the MOS server reachable from Home Assistant at the configured host and port?
2. Is the API token still valid in the MOS web UI?
3. Check the log — enable debug logging as described in the [README](../../README.md#troubleshooting)

### A Switch Reports Missing Permissions

The API token has no write access to that resource. Create a token with write access to `lxc`, `docker` or `vm` in the MOS web UI and enter it via **⋮** → **Reconfigure**.

### Options Don't Save

Check the value range (update interval 30–3600 seconds) and the log for validation errors.

## Related Documentation

- [Getting Started](./GETTING_STARTED.md) — installation and initial setup
- [Examples](./EXAMPLES.md) — automation and dashboard examples
- [GitHub Issues](https://github.com/anym001/ha-mos/issues) — report problems
