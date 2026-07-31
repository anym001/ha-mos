# MOS NAS

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Home Assistant integration for a [MOS](https://mos-official.net/) server: monitors the system, its storage, containers and VMs — and lets you start and stop them.

## Prerequisites

- MOS **0.5.1-beta** or later — earlier versions don't return permission information on the API token, which this integration relies on
- Create an [API token](https://docs.mos-official.net/docs/API/MOS-API-Overview)

## Features

- **Easy setup** — configured entirely through the UI, no YAML
- **System monitoring** — version, build, kernel, architecture, CPU, live CPU load/temperature, memory and swap, plus how much RAM Docker, LXC, VMs and the cache each hold
- **Storage** — usage, free/used/total space, health and scrub/balance/parity status per pool; power/temperature status, SMART warnings, model and size per disk
- **Services** — Docker, VM, SSH, Samba, NFS, Tailscale and Netbird status
- **LXC, Docker and VMs** — per-item CPU/memory, versions, update-available, autostart, plus a switch to start/stop it
- **Hardware sensors** — fan speed/percentage, temperature and voltage readings, one entity per reading
- **Token permissions respected** — every write action checks your API token's scope first, and for custom-scoped tokens, entities are only created for categories the token can actually read
- **Selective categories** — turn disks, pools, services, LXC, Docker, VMs or hardware sensors off entirely

Entities are spread across three platforms:

- **`sensor`** — system info and health, pool usage and space, disk power/temperature/model/size, LXC/Docker/VM resources, hardware sensors
- **`binary_sensor`** — service status, pool health and maintenance operations, disk SMART, container/VM state
- **`switch`** — LXC container, Docker container and VM power

Disks, pools, containers and VMs appear and disappear automatically as they change on the server — no reload needed. Each disk, pool, container and VM gets its own device linked back to the server. Hardware sensor readings appear directly on the server device instead, since each one is already a single measurement rather than a physical item with several attributes.

## Installation

The integration is not in the HACS default store yet, so HACS has to be pointed at this repository:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-badge]][hacs-repo-link]

1. Open the repository with the button above and click **Download** — or add it by hand in HACS: **⋮** → **Custom repositories** → `https://github.com/anym001/ha-mos` as an **Integration**, then find **MOS NAS** and download it
2. **Restart Home Assistant**
3. **Settings** → **Devices & Services** → **+ Add Integration** → search for "MOS NAS", or use this button:

[![Open your Home Assistant instance and start setting up a new integration.][config-flow-badge]][config-flow-link]

To install without HACS, copy `custom_components/mos/` into your Home Assistant `custom_components/` directory and restart.

### What setup asks for

Required: **Name**, **Host** and **API token**. Everything else is optional:

- **Port** — 80 (HTTP) or 443 (TLS), depending on the setting below
- **Use HTTPS** — off by default
- **Verify TLS certificate** — on by default

The name becomes the device name and keeps entity IDs apart if you add several servers. Create the API token in the MOS web UI under **User Settings → Admin API Tokens** — see [Security](#security) for how to scope it.

Connection details can be changed later via **⋮** → **Reconfigure**, without removing the integration.

## Configuration

Click **Configure** on the integration to change these anytime — the integration reloads itself:

- **Update interval** — how often to poll the MOS API, between 30 and 3600 seconds; 30 seconds by default
- **Enable disks / pools / services / LXC / Docker / VMs** — create entities for that category; each can be toggled on its own and all are on by default

System info and system health (CPU, memory, swap) are always enabled. A disabled category isn't fetched at all — useful if you don't run LXC or VMs, or just want a shorter entity list.

The default of 30 seconds suits container and VM states you want to react to; 5–30 minutes is plenty if you only watch slow-moving values like disk temperature or pool usage. Start/stop switches don't wait for the next poll — the new state shows immediately.

## Security

**Give the token only the access you need.** MOS tokens come in three modes. **Full** is more than this integration ever uses. **Read-only** covers all monitoring, and the start/stop switches then refuse with a clear error instead of a cryptic one. **Custom** sets the level per resource and is the better fit — these are the only ones the integration touches:

| Resource | Level             | Needed for                                          |
| -------- | ----------------- | --------------------------------------------------- |
| `mos`    | `read`            | System info, services, hardware sensors — required  |
| `system` | `read`            | CPU load, memory and swap — required                |
| `auth`   | `read`            | Reading the token's own scope — recommended         |
| `disks`  | `read`            | Disk entities, if the category is enabled           |
| `pools`  | `read`            | Pool entities, if the category is enabled           |
| `lxc`    | `read` or `write` | LXC entities — `write` only for the power switch    |
| `docker` | `read` or `write` | Docker entities — `write` only for the power switch |
| `vm`     | `read` or `write` | VM entities — `write` only for the power switch     |

Everything else — `iscsi`, `users`, `shares`, `cron`, `terminal` — is never requested and can stay at `none`.

The integration reads the token's scope at setup and only creates entities for what the token can reach, so a narrow token costs nothing beyond the categories you deliberately left out. Without read access to `auth` it cannot do that: it still works, but it discovers each restriction through the server's refusal on the first poll instead of skipping the category up front.

**Prefer HTTPS.** The connection defaults to plain HTTP, and the API token then goes over the network in clear text with every poll — every 30 seconds by default. Within a trusted LAN segment that may be a fair trade for not having to deal with certificates; across VLANs, over Wi-Fi or through anything routed, it isn't. Turn on **Use HTTPS** during setup or later via **⋮** → **Reconfigure**, and leave **Verify TLS certificate** on unless the server presents a self-signed certificate.

**Diagnostics are redacted, but not anonymous.** The download strips the API token, the host and every identifier that would locate the machine or its hardware: hostname, API base URLs, disk serials and UUIDs, IP and MAC addresses, container network blocks, and the token's own ID and name. What remains is descriptive rather than identifying — container, VM and pool names, disk models and sizes, CPU model, MOS version, service status and entity IDs. Port, HTTPS and certificate-verification settings stay visible on purpose, because connection problems can't be diagnosed without them. Skim the file before attaching it to a public issue if any of your container or pool names are themselves revealing.

## Troubleshooting

**Entities went unavailable.** Usually the server is unreachable or restarting; the integration retries on its own and recovers without any action.

**Only _some_ entities went unavailable.** One endpoint has been failing on its own while the rest of the server answers fine. A short outage costs nothing — those entities keep their last values and the integration retries every poll. Once an endpoint has been failing for more than fifteen minutes _and_ across at least three polls, its entities switch to unavailable rather than go on showing readings that stopped updating then; the log names the resource. Nothing is deleted, so history, custom names and automations survive, and everything comes back on its own the moment the endpoint answers again. At long update intervals the threshold stretches — at the 3600 second maximum it is three failed polls, so about two hours.

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

**Diagnostics.** **Settings** → **Devices & Services** → **MOS NAS** → **⋮** → **Download diagnostics** writes a JSON file with connection settings, coordinator status, the token's permissions and the created devices and entities. Credentials and identifying details are redacted — [Security](#security) lists exactly what is and isn't.

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
[config-flow-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[config-flow-link]: https://my.home-assistant.io/redirect/config_flow_start/?domain=mos
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-repo-link]: https://my.home-assistant.io/redirect/hacs_repository/?owner=anym001&repository=ha-mos&category=integration
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/anym001/ha-mos.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40anym001-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/anym001/ha-mos.svg?style=for-the-badge
[releases]: https://github.com/anym001/ha-mos/releases
[user_profile]: https://github.com/anym001
