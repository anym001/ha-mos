# MOS

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Home Assistant integration for a [MOS](https://mos-official.net/) server: monitors the system, its storage, containers and VMs — and lets you start and stop them.

## Features

- **Easy setup** — configured entirely through the UI, no YAML
- **System monitoring** — version, build, kernel, architecture, CPU, live CPU load/temperature, memory and swap
- **Storage** — usage, free space, health and scrub/balance/parity status per pool; power/temperature status and SMART warnings per disk
- **Services** — Docker, VM, SSH, Samba, NFS, Tailscale and Netbird status
- **LXC, Docker and VMs** — per-item CPU/memory, versions, update-available, autostart, plus a switch to start/stop it
- **Token permissions respected** — start and stop honor what your API token is allowed to do, and say so clearly instead of showing a cryptic server error when it isn't allowed
- **Selective categories** — turn disks, pools, services, LXC, Docker or VMs off entirely

| Platform        | Entities                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------- |
| `sensor`        | System info and health, pool usage/free space, disk power/temperature, LXC/Docker/VM resources |
| `binary_sensor` | Service status, pool health and maintenance operations, disk SMART, container/VM state         |
| `switch`        | LXC container, Docker container and VM power                                                   |

Disks, pools, containers and VMs appear and disappear automatically as they change on the server — no reload needed. Disks and pools are entities on the server device itself; each container and VM gets its own device linked back to the server.

## Installation

The integration is not in the HACS default store yet, so add it as a custom repository:

1. In HACS: **⋮** → **Custom repositories** → add `https://github.com/anym001/ha-mos` as an **Integration**
2. Find **MOS** in HACS and click **Download**
3. **Restart Home Assistant**
4. **Settings** → **Devices & Services** → **+ Add Integration** → search for "MOS"

To install without HACS, copy `custom_components/mos/` into your Home Assistant `custom_components/` directory and restart.

### What setup asks for

| Field                      | Required | Default             |
| -------------------------- | -------- | ------------------- |
| **Name**                   | yes      | –                   |
| **Host**                   | yes      | –                   |
| **API token**              | yes      | –                   |
| **Port**                   | no       | 80 (HTTP)/443 (TLS) |
| **Use HTTPS**              | no       | off                 |
| **Verify TLS certificate** | no       | on                  |

The name becomes the device name and keeps entity IDs apart if you add several servers. Create the API token in the MOS web UI under **User Settings → Admin API Tokens** — read-only is enough for monitoring, starting and stopping needs write access to the respective resource.

Connection details can be changed later via **⋮** → **Reconfigure**, without removing the integration.

## Configuration

Click **Configure** on the integration to change these anytime — the integration reloads itself:

| Option                                                            | Default | Description                              |
| ----------------------------------------------------------------- | ------- | ---------------------------------------- |
| Update interval                                                   | 30s     | How often to poll the MOS API (30–3600s) |
| Enable disks / pools / services / LXC / Docker / VMs (individual) | On      | Create entities for that category        |

System info and system health (CPU, memory, swap) are always enabled. A disabled category isn't fetched at all — useful if you don't run LXC or VMs, or just want a shorter entity list.

The default of 30 seconds suits container and VM states you want to react to; 5–30 minutes is plenty if you only watch slow-moving values like disk temperature or pool usage. Start/stop switches don't wait for the next poll — the new state shows immediately.

## Troubleshooting

**Entities went unavailable.** Usually the server is unreachable or restarting; the integration retries on its own and recovers without any action.

**Reauthentication prompt.** Appears once the server has rejected the token for at least five minutes _and_ on three consecutive polls — enter a new token under **Settings** → **Devices & Services**. Both conditions have to hold, so neither a brief rejection during a server reboot nor a couple of unlucky polls on a long update interval costs you a valid token. This holds while the integration is starting up too: it retries setup rather than asking for a token straight away.

**Some entities are missing.** Most likely the API token is scoped and cannot read that category. The integration skips what the token isn't allowed to read and keeps everything else working, and logs a warning naming the affected categories. Grant the token read access in the MOS web UI under **User Settings → Admin API Tokens**, then reload the integration. A missing permission never causes a reauthentication prompt — a new token with the same scope wouldn't change anything.

**Debug logging.**

```yaml
logger:
  default: info
  logs:
    custom_components.mos: debug
```

**A switch reports missing permissions.** The API token has no write access to that resource. Create one with write access to `lxc`, `docker` or `vm` in the MOS web UI and enter it via **⋮** → **Reconfigure**.

**Diagnostics.** **Settings** → **Devices & Services** → **MOS** → **⋮** → **Download diagnostics** writes a JSON file with connection settings, coordinator status, the token's permissions and the created devices and entities. The API token is redacted; host and container names are not, so review it before posting it publicly.

## Contributing

Contributions are welcome — issues and pull requests alike. The repository ships a complete dev environment (Home Assistant, Python 3.14, all tooling):

- **GitHub Codespaces:** **Code** → **Codespaces** → **Create codespace on main** — see [docs/development/CODESPACES.md](docs/development/CODESPACES.md)
- **Locally:** open the repository in VS Code with the Dev Containers extension → **Reopen in Container**
- Then: `script/develop` (Home Assistant on <http://localhost:8123>), `script/check`, `script/test`

Branching model, commit conventions and the release process are in [CONTRIBUTING.md](CONTRIBUTING.md); architecture and design decisions in [docs/development/](docs/development/).

> [!NOTE]
> **Transparency:** This integration was developed with the help of AI coding agents (GitHub Copilot, Claude and others). It follows Home Assistant Core standards, but AI-generated code may not be reviewed and tested to the same extent as hand-written code. If something behaves unexpectedly, please [open an issue](../../issues).

## License

MIT — see [LICENSE](LICENSE).

Maintained by [@anym001][user_profile].

[commits-shield]: https://img.shields.io/github/commit-activity/y/anym001/ha-mos.svg?style=for-the-badge
[commits]: https://github.com/anym001/ha-mos/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/anym001/ha-mos.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40anym001-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/anym001/ha-mos.svg?style=for-the-badge
[releases]: https://github.com/anym001/ha-mos/releases
[user_profile]: https://github.com/anym001
