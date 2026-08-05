# MOS NAS

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Home Assistant integration for a [MOS](https://mos-official.net/) server: monitors the system, its storage, containers and VMs — and lets you start and stop them.

## Prerequisites

- MOS **0.5.1-beta** or later recommended — older versions work, but from 0.5.1-beta on the integration can see up front what a restricted token is allowed to read
- Create an [API token](https://docs.mos-official.net/docs/API/MOS-API-Overview)

## Features

- **Easy setup** — configured entirely through the UI, no YAML
- **System monitoring** — version, build, kernel, architecture, CPU, live CPU load/temperature, memory and swap, plus how much RAM Docker, LXC, VMs and the cache each hold
- **Storage** — usage, free/used/total space, health and scrub/balance/parity status per pool; power/temperature status, SMART warnings, model and size per disk
- **Services** — Docker, VM, SSH, Samba, NFS, Tailscale and Netbird status
- **LXC, Docker and VMs** — per-item CPU/memory, versions, update-available, autostart, plus a switch to start/stop it
- **Hardware sensors** — fan speed/percentage, temperature and voltage readings, one entity per reading
- **UPS** — on its own device: status, load, battery and voltage readings, plus one binary sensor per NUT status flag; created once a UPS answers, so a server without one gets none
- **One room for the whole server** — set the area on the server device and its pools, disks, containers, VMs and UPS follow, including ones that appear later; move a single device somewhere else and it stays put
- **Token permissions respected** — every write action checks your API token's scope first
- **Selective categories** — every category can be turned off entirely

Entities are spread across three platforms:

- **`sensor`** — system info and health, pool usage and space, disk power/temperature/model/size, LXC/Docker/VM resources, hardware sensors, UPS readings
- **`binary_sensor`** — service status, pool health and maintenance operations, disk SMART, container/VM state, UPS power/battery flags
- **`switch`** — LXC container, Docker container and VM power

**Entities only appear for what your MOS version can answer.** Each MOS release adds endpoints, and the integration asks for all of them. A server that doesn't have one yet says so, which counts as an answer rather than a failure: those entities are left out, the log names them once, and nothing else is affected. The request goes out on every poll anyway, so after a MOS update the matching entities appear on their own within a poll or two — no version numbers to look up, nothing to reload. Switch the category off in the options if you would rather it stopped asking.

## Installation

**MOS NAS** is in the HACS default store, so no custom repository is needed:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-badge]][hacs-repo-link]

1. Open HACS, search for **MOS NAS** and click **Download** — or use the button above to go straight there
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

Home Assistant follows the form with a list of every device it just created, each with an area picker. You can fill in the **first row only** — the server itself — and skip the rest: the other devices take that area from it, and so does anything that appears later. Nothing there is mandatory, so skipping all of it is fine too.

Connection details can be changed later via **⋮** → **Reconfigure**, without removing the integration.

## Configuration

Click **Configure** on the integration to change these anytime — the integration reloads itself:

- **Update interval** — how often to poll the MOS API, between 30 and 3600 seconds; 30 seconds by default
- **Enable disks / pools / services / LXC / Docker / VMs / hardware sensors / UPS** — create entities for that category; each can be toggled on its own and all are on by default

System info and system health (CPU, memory, swap) are always enabled. A disabled category isn't fetched at all — useful if you don't run LXC or VMs, or just want a shorter entity list.

The default of 30 seconds suits container and VM states you want to react to; 5–30 minutes is plenty if you only watch slow-moving values like disk temperature or pool usage. Start/stop switches don't wait for the next poll — the new state shows immediately.

## Security

**Give the token only the access it needs.** MOS tokens come in three modes. **Full** grants far more than this integration touches. **Read-only** blocks writes. **Custom** sets the level per resource and is the best fit:

| Resource | Level             | Needed for                                          |
| -------- | ----------------- | --------------------------------------------------- |
| `mos`    | `read`            | System info, services, hardware sensors — required  |
| `system` | `read`            | CPU load, memory and swap — required                |
| `disks`  | `read`            | Disk entities, if the category is enabled           |
| `pools`  | `read`            | Pool entities, if the category is enabled           |
| `lxc`    | `read` or `write` | LXC entities — `write` only for the power switch    |
| `docker` | `read` or `write` | Docker entities — `write` only for the power switch |
| `vm`     | `read` or `write` | VM entities — `write` only for the power switch     |
| `nut`    | `read`            | UPS entities, if the category is enabled            |

A row can be missing on an older server: a resource only appears in this list once that MOS version has the matching endpoint. There is nothing to grant and nothing to fix then — the missing endpoint is handled as described [above](#features), and the row shows up in the token dialog once MOS is updated.

Everything else stays at `none` — `auth`, `iscsi`, `users`, `shares`, `cron`, `terminal`. `auth` included: MOS lets a token read its own permission scope whatever its `auth` level says. Entities are only created for what the token can read, so a narrow token costs nothing beyond the categories you left out; `mos` or `system` at `none` leaves nothing to show at all.

**Prefer HTTPS.** Plain HTTP is the default, and it sends the API token in clear text with every poll. Turn on **Use HTTPS** during setup or later via **⋮** → **Reconfigure**, and leave **Verify TLS certificate** on unless the server presents a self-signed certificate.

**Diagnostics are redacted, but not anonymous.** The download strips the API token, the hostname, API URLs, disk serials and UUIDs, IP and MAC addresses, and the token's own ID and name. Container, VM and pool names, disk and CPU models, MOS version, entity IDs, your own device names and the area each device is assigned to remain, as do the port and TLS settings — connection problems can't be diagnosed without them. Skim the file before attaching it to a public issue.

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

**A switch reports missing permissions.** The API token has no write access to that resource. Create one with write access to `lxc`, `docker` or `vm` and enter it via **⋮** → **Reconfigure**.

**Diagnostics.** **Settings** → **Devices & Services** → **MOS NAS** → **⋮** → **Download diagnostics** writes a JSON file with connection settings, coordinator status, the token's permissions and the created devices and entities. Credentials and identifying details are redacted — [Security](#security) says what is and isn't.

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
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/anym001/ha-mos.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40anym001-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/anym001/ha-mos.svg?style=for-the-badge
[releases]: https://github.com/anym001/ha-mos/releases
[user_profile]: https://github.com/anym001
