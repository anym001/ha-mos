# MOS

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

## ✨ Features

- **Easy Setup**: Simple configuration through the UI - no YAML required
- **System Monitoring**: MOS/OS version, build, kernel, architecture, and CPU info
- **Storage Pools**: Usage, free space, health, and scrub/balance/parity status per pool
- **Physical Disks**: Power status, temperature status, and SMART warnings per disk
- **Services**: Docker, VM, SSH, Samba, NFS, Tailscale, and Netbird status
- **System Health**: Live CPU load/temperature, memory usage, and swap usage
- **LXC Containers**: Per-container CPU/memory usage, autostart, and a power switch to start/stop the container
- **Docker Containers**: Per-container installed/latest version, update-available status, and autostart (no start/stop control yet - MOS has no single-container endpoint for Docker)
- **Selective Categories**: Turn disks, pools, services, LXC, or Docker containers on/off entirely via the options flow
- **Reconfigurable**: Change connection details anytime without removing the integration
- **Reauthentication**: Prompted automatically if the API token is rejected
- **Diagnostics**: Download a full diagnostics report for troubleshooting

Disks and storage pools live on the single MOS server device — there's no per-disk or per-pool device clutter; each pool/disk simply gets its own name folded into its entity ID (e.g. `sensor.mos_server_tank_usage`). LXC and Docker containers, on the other hand, each get their own device (linked back to the server device via `via_device`, named `<server> LXC <container>` / `<server> Docker <container>` to stay unique across multiple configured servers and disambiguate same-named LXC/Docker containers), since there can be many of them and you may want to enable/disable individual containers from their own device page.

**This integration sets up the following platforms.**

| Platform        | Description                                                                                             |
| --------------- | --------------------------------------------------------------------------------------------------------- |
| `sensor`        | System info, system health, storage pool usage/free space, disk power/temperature, LXC/Docker container info |
| `binary_sensor` | Service status, pool health/maintenance operations, disk SMART status, LXC/Docker container state        |
| `switch`        | LXC container power (start/stop the container on the MOS server)                                        |

## 🚀 Quick Start

### Step 1: Install the Integration

This integration is not yet in the HACS default store. Add it as a custom repository:

1. In HACS, open the **⋮** menu → **Custom repositories**
2. Add `https://github.com/anym001/ha-mos` as an **Integration**
3. Find **MOS** in HACS and click **Download**
4. **Restart Home Assistant** (required after installation)

<details>
<summary><strong>Manual Installation (Advanced)</strong></summary>

If you prefer not to use HACS:

1. Download the `custom_components/mos/` folder from this repository
2. Copy it to your Home Assistant's `custom_components/` directory
3. Restart Home Assistant

</details>

### Step 2: Add and Configure the Integration

**Important:** You must have installed the integration first (see Step 1) and restarted Home Assistant!

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for "MOS"
4. Fill in the connection details:
   - **Name**: A friendly name for this MOS server (becomes the device name)
   - **Host**: The MOS server's IP address or hostname
   - **API token**: Create one in the MOS web UI under **User Settings → Admin API Tokens**
   - **Port**, **Use HTTPS**, **Verify TLS certificate**: Optional, defaults usually work

### Step 3: Adjust Settings (Optional)

After setup, click **Configure** on the integration to adjust:

- **Update interval**: How often to poll the MOS API (10–3600 seconds, default 30)
- **Enable disks / storage pools / services / LXC / Docker**: Turn any of these entity categories off entirely if you don't want them (e.g. no LXC containers configured, so hide the LXC entities)

Changing an option reloads the integration automatically.

You can also **Reconfigure** the connection details (host, token, port, TLS) anytime without removing the integration.

### Step 4: Start Using!

Find all entities in **Settings** → **Devices & Services** → **MOS** → click on the device.

## Available Entities

### Sensors

- **System info**: MOS version, update channel, build, API version, frontend version, running/recommended kernel, architecture, CPU, base OS, boot time
- **System health**: CPU load (%), CPU temperature, memory usage (%), memory used, swap usage (%)
- **Storage pools** (per pool): Usage (%), free space
- **Physical disks** (per disk): Power status, temperature status
- **LXC containers** (per container): CPU usage (%), memory usage
- **Docker containers** (per container): Installed version, latest version

### Binary Sensors

- **Services**: Docker running, VM running, SSH enabled, Samba enabled, NFS enabled, Tailscale online, Netbird online
- **Storage pools** (per pool): Problem (health issue - _Diagnostic_), scrub running, balance running, parity running (only the operations that apply to that pool's filesystem type)
- **Physical disks** (per disk): SMART warning (_Diagnostic_)
- **LXC containers** (per container): Autostart
- **Docker containers** (per container): Update available (_Diagnostic_), autostart

### Switches

- **LXC containers** (per container): Power - reflects whether the container is running, and starts/stops it on the MOS server when toggled

Disks, pools, and LXC/Docker containers appear/disappear automatically as they're added or removed on the MOS server - no reload needed.

## Configuration Options

### During Setup

| Name                   | Required | Description                                            |
| ---------------------- | -------- | ------------------------------------------------------ |
| Name                   | Yes      | Friendly name for this server; used as the device name |
| Host                   | Yes      | MOS server IP address or hostname                      |
| API token              | Yes      | Admin API token from the MOS web UI                    |
| Port                   | No       | Defaults to 80 (HTTP) or 443 (HTTPS)                   |
| Use HTTPS              | No       | Off by default                                         |
| Verify TLS certificate | No       | On by default                                          |

### After Setup (Options)

You can change these anytime by clicking **Configure**:

| Name                 | Default | Description                                                   |
| -------------------- | ------- | ------------------------------------------------------------- |
| Update interval      | 30s     | How often to poll the MOS API (10–3600s)                      |
| Enable disks         | On      | Create entities for physical disks                            |
| Enable storage pools | On      | Create entities for storage pools                             |
| Enable services      | On      | Create entities for Docker/VM/SSH/Samba/NFS/Tailscale/Netbird |
| Enable LXC containers   | On   | Create entities for each LXC container                        |
| Enable Docker containers | On  | Create entities for each Docker container                     |

System health (CPU load/temperature, memory, swap) is always enabled and has no toggle.

## Troubleshooting

### Reauthentication

If your API token expires or is revoked, Home Assistant will prompt you to reauthenticate:

1. Go to **Settings** → **Devices & Services**
2. Look for **"Reauthenticate"** on the MOS integration
3. Enter a new API token and submit

### Manual Reconfiguration

You can update the connection details anytime without waiting for an error:

1. Go to **Settings** → **Devices & Services**
2. Find **MOS**
3. Click the **3 dots menu** → **Reconfigure**
4. Update host, API token, port, or TLS settings

### Enable Debug Logging

To enable debug logging for this integration, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.mos: debug
```

### Common Issues

#### Authentication Errors

If you receive authentication errors:

1. Verify the API token is correct and hasn't been revoked in the MOS web UI
2. Check that the token has admin permissions
3. Wait for the automatic reauthentication prompt, or manually reconfigure

#### Server Not Responding

If the integration shows errors updating data:

1. Check that the MOS server is reachable at the configured host/port
2. Check the integration diagnostics (Settings → Devices & Services → MOS → 3 dots → Download diagnostics)

## 🤝 Contributing

Contributions are welcome! Please open an issue or pull request if you have suggestions or improvements.

You have two options to set up a development environment — expand below for full details.

<details>
<summary><strong>Development Setup</strong></summary>

Both options provide the same fully-configured environment with Home Assistant, Python 3.14, Node.js LTS, and all necessary tools.

### Option 1: GitHub Codespaces (Recommended) ☁️

Develop directly in your browser without installing anything locally!

1. Click the green **"Code"** button in this repository
2. Switch to the **"Codespaces"** tab
3. Click **"Create codespace on main"**
4. **Wait for setup** (2-3 minutes first time) — everything installs automatically
5. **Review and commit** your changes in the Source Control panel (`Ctrl+Shift+G`)

> [!TIP]
> Codespaces gives you **60 hours/month free** for personal accounts. When you start Home Assistant (`script/develop`), port 8123 forwards automatically.

### Option 2: Local Development with VS Code 💻

#### Prerequisites

You'll need these installed locally:

- **A Docker-compatible container engine** — see options by platform:

  | Option                                                                                                                   | 🍎 macOS | 🐧 Linux | 🪟 Windows | Notes                                                                                                                                                                                                                                     |
  | ------------------------------------------------------------------------------------------------------------------------ | :------: | :------: | :--------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | [Docker Desktop](https://www.docker.com/products/docker-desktop/)                                                        |    ✅    |    ✅    |     ✅     | **Easiest starting point for all platforms.** GUI-based, well-documented, one installer. Uses WSL2 as default backend on Windows (Hyper-V also available). Installation requires admin rights; daily use does not. Free for personal use. |
  | [OrbStack](https://orbstack.dev/) ⭐                                                                                     |    ✅    |    —     |     —      | **Recommended for macOS** once Docker Desktop feels slow. Starts in ~2s, much lighter on RAM/CPU, full Docker API compatibility. Free for personal use.                                                                                   |
  | [Docker CE](https://docs.docker.com/engine/install/) (native) ⭐                                                         |    —     |    ✅    |     —      | **Recommended for Linux.** Install directly via your package manager — no VM, no GUI, no overhead. Free.                                                                                                                                  |
  | [WSL2](https://learn.microsoft.com/windows/wsl/install) + [Docker CE](https://docs.docker.com/engine/install/ubuntu/) ⭐ |    —     |    —     |     ✅     | **Recommended for Windows** once you're comfortable with WSL2. Docker runs natively inside WSL2 — no GUI overhead. Requires one-time WSL2 setup. Free.                                                                                    |
  | [Rancher Desktop](https://rancherdesktop.io/)                                                                            |    ✅    |    ✅    |     ✅     | Open source by SUSE. GUI-based, uses WSL2 on Windows. Good alternative to Docker Desktop. Free.                                                                                                                                           |
  | [Colima](https://github.com/abiosoft/colima)                                                                             |    ✅    |    ✅    |     —      | CLI-only, very lightweight. Good for terminal-focused workflows. Free.                                                                                                                                                                    |

- **VS Code** with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- **Git** — macOS and Linux usually have it already; see below if not, or to get a newer version:
  - **🍎 macOS:** The system Git (`xcode-select --install`) works fine. Recommended: `brew install git` ([Homebrew](https://brew.sh/)) for a current version.
  - **🐧 Linux:** Usually pre-installed. If not: `sudo apt install git` (or your distro's equivalent).
  - **🪟 Windows + WSL2 ⭐:** Install Git _inside WSL2_ with `sudo apt install git`. Git on Windows itself is not needed — VS Code clones and operates entirely within WSL2.
  - **🪟 Windows + Docker Desktop:** Install via `winget install Git.Git` or download [Git for Windows](https://git-scm.com/download/win).
- **Hardware** — the devcontainer runs a full Home Assistant instance including Python tooling:

  |          | Minimum    | Recommended                           |
  | -------- | ---------- | ------------------------------------- |
  | **RAM**  | 8 GB       | 16 GB or more                         |
  | **CPU**  | 4 cores    | 8 cores or more                       |
  | **Disk** | 10 GB free | 20 GB free (SSD strongly recommended) |

> [!TIP]
> **Not sure which Docker option to pick?** Start with [Docker Desktop](https://www.docker.com/products/docker-desktop/) — it works on all platforms, has a GUI, and needs no extra setup. The ⭐ options are faster alternatives once you're comfortable. macOS and Linux offer the best devcontainer experience — containers run with no extra VM layer and file I/O is fast. Windows works well too; this integration uses named container volumes (files live inside WSL2, not on the Windows drive) to keep performance acceptable.

> [!NOTE]
> **New to Dev Containers?** See the [VS Code Dev Containers documentation](https://code.visualstudio.com/docs/devcontainers/containers#_system-requirements) for system requirements and how to install the extension. **Once the extension is installed, you're done** — this repository already ships a complete devcontainer configuration. You don't need to follow the rest of the VS Code guide; the setup steps below are all that's needed.

#### Setup Steps

1. **Clone in a Dev Container:**

   **🍎 macOS / 🐧 Linux:** Clone the repository and open the folder in VS Code → click **"Reopen in Container"** when prompted (or `F1` → **"Dev Containers: Reopen in Container"**).

   **🪟 Windows:** In VS Code, press `F1` → **"Dev Containers: Clone Repository in Named Container Volume..."** and enter the repository URL. This keeps files inside WSL2 for best I/O performance.

2. Wait for the container to build (2-3 minutes first time)

3. **Review and commit** changes in Source Control (`Ctrl+Shift+G`)

4. **Start developing**:

   ```bash
   script/develop  # Home Assistant runs at http://localhost:8123
   ```

> [!NOTE]
> Both Codespaces and local DevContainer provide the exact same experience. The only difference is where the container runs (GitHub's cloud vs. your machine).

</details>

---

## 🤖 AI-Assisted Development

> [!NOTE]
> **Transparency Notice:** This integration was developed with assistance from AI coding agents (GitHub Copilot, Claude, and others). While the codebase follows Home Assistant Core standards, AI-generated code may not be reviewed or tested to the same extent as manually written code. AI tools were used to generate boilerplate code, implement standard integration features (config flow, coordinator, entities), ensure code quality and type safety, and write documentation. If you encounter unexpected behavior, please [open an issue](../../issues) on GitHub.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by [@anym001][user_profile]**

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/anym001/ha-mos.svg?style=for-the-badge
[commits]: https://github.com/anym001/ha-mos/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/anym001/ha-mos.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40anym001-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/anym001/ha-mos.svg?style=for-the-badge
[releases]: https://github.com/anym001/ha-mos/releases
[user_profile]: https://github.com/anym001
