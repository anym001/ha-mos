# MOS

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Home Assistant integration for a MOS server: monitors the system, its storage, containers and VMs — and lets you start and stop them.

## ✨ Features

- **Easy setup** — configured entirely through the UI, no YAML
- **System monitoring** — version, build, kernel, architecture, CPU, live CPU load/temperature, memory and swap
- **Storage** — usage, free space, health and scrub/balance/parity status per pool; power/temperature status and SMART warnings per disk
- **Services** — Docker, VM, SSH, Samba, NFS, Tailscale and Netbird status
- **LXC, Docker and VMs** — per-item CPU/memory, versions, update-available, autostart, plus a switch to start/stop it
- **Permission-aware writes** — start/stop checks the token's scope first and fails with a clear message instead of a raw 401/403
- **Selective categories** — turn disks, pools, services, LXC, Docker or VMs off entirely
- **Robust** — reconfigurable anytime, reauthentication only when the token is really gone, full diagnostics download

| Platform        | Entities                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------- |
| `sensor`        | System info and health, pool usage/free space, disk power/temperature, LXC/Docker/VM resources |
| `binary_sensor` | Service status, pool health and maintenance operations, disk SMART, container/VM state         |
| `switch`        | LXC container, Docker container and VM power                                                   |

Disks, pools, containers and VMs appear and disappear automatically as they change on the server — no reload needed. Disks and pools are entities on the server device itself; each container and VM gets its own device linked back to the server.

## 🚀 Installation

The integration is not in the HACS default store yet, so add it as a custom repository:

1. In HACS: **⋮** → **Custom repositories** → add `https://github.com/anym001/ha-mos` as an **Integration**
2. Find **MOS** in HACS and click **Download**
3. **Restart Home Assistant**
4. **Settings** → **Devices & Services** → **+ Add Integration** → search for "MOS"

You will need the server's host name or IP and an API token (MOS web UI → **User Settings → Admin API Tokens**). Port, HTTPS and certificate verification are optional; the defaults usually work.

To install without HACS, copy `custom_components/mos/` into your Home Assistant `custom_components/` directory and restart. Full walkthrough: [docs/user/GETTING_STARTED.md](docs/user/GETTING_STARTED.md).

## ⚙️ Configuration

Click **Configure** on the integration to change these anytime — the integration reloads itself:

| Option                                                            | Default | Description                              |
| ----------------------------------------------------------------- | ------- | ---------------------------------------- |
| Update interval                                                   | 30s     | How often to poll the MOS API (30–3600s) |
| Enable disks / pools / services / LXC / Docker / VMs (individual) | On      | Create entities for that category        |

System health (CPU, memory, swap) is always enabled. Connection details (host, token, port, TLS) can be changed via **⋮** → **Reconfigure**. More detail: [docs/user/CONFIGURATION.md](docs/user/CONFIGURATION.md).

## 🩺 Troubleshooting

**Entities went unavailable.** Usually the server is unreachable or restarting; the integration retries on its own and recovers without any action.

**Reauthentication prompt.** Appears once the server has rejected the token continuously for about five minutes — enter a new token under **Settings** → **Devices & Services**. Short rejections during a server reboot are ridden out instead, so a restart never costs you a valid token. Exception: a rejection while the integration is _starting up_ asks for reauthentication right away.

**Debug logging.**

```yaml
logger:
  default: info
  logs:
    custom_components.mos: debug
```

**Diagnostics.** **Settings** → **Devices & Services** → **MOS** → **⋮** → **Download diagnostics**.

## 🤝 Contributing

Contributions are welcome — issues and pull requests alike. The repository ships a complete dev environment (Home Assistant, Python 3.14, all tooling):

- **GitHub Codespaces:** **Code** → **Codespaces** → **Create codespace on main** — see [docs/development/CODESPACES.md](docs/development/CODESPACES.md)
- **Locally:** open the repository in VS Code with the Dev Containers extension → **Reopen in Container**
- Then: `script/develop` (Home Assistant on <http://localhost:8123>), `script/check`, `script/test`

Branching model, commit conventions and the release process are in [CONTRIBUTING.md](CONTRIBUTING.md); architecture and design decisions in [docs/development/](docs/development/).

> [!NOTE]
> **Transparency:** This integration was developed with the help of AI coding agents (GitHub Copilot, Claude and others). It follows Home Assistant Core standards, but AI-generated code may not be reviewed and tested to the same extent as hand-written code. If something behaves unexpectedly, please [open an issue](../../issues).

## 📄 License

MIT — see [LICENSE](LICENSE).

**Made with ❤️ by [@anym001][user_profile]**

[commits-shield]: https://img.shields.io/github/commit-activity/y/anym001/ha-mos.svg?style=for-the-badge
[commits]: https://github.com/anym001/ha-mos/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/anym001/ha-mos.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40anym001-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/anym001/ha-mos.svg?style=for-the-badge
[releases]: https://github.com/anym001/ha-mos/releases
[user_profile]: https://github.com/anym001
