# Architecture Overview

This document describes the technical architecture of the MOS NAS custom component for Home Assistant.

## Directory Structure

```text
custom_components/mos/
├── __init__.py              # Integration setup and unload
├── config_flow.py           # Config flow entry point
├── const.py                 # Constants and configuration keys
├── coordinator/             # Data update coordinator package
│   ├── __init__.py          # Exports MOSDataUpdateCoordinator
│   ├── base.py              # Main coordinator class
│   └── docker_templates.py  # Per-container template cache and web link resolution
├── data.py                  # Runtime data classes and type definitions
├── diagnostics.py           # Diagnostic data for troubleshooting
├── manifest.json            # Integration metadata
├── api/                     # External API communication
│   ├── __init__.py          # Exception hierarchy and exports
│   └── client.py            # API client implementation
├── config_flow_handler/     # Config flow implementation
│   ├── __init__.py          # Package exports
│   ├── handler.py           # Shared handler base
│   ├── config_flow.py       # Main config flow (user, reauth, reconfigure)
│   ├── options_flow.py      # Options flow
│   ├── schemas/             # Voluptuous schemas
│   │   ├── config.py        # Config flow schemas
│   │   └── options.py       # Options flow schemas
│   └── validators/          # Input validation
│       └── credentials.py   # Credential validation
├── entity/                  # Base entity package
│   ├── __init__.py          # Exports MOSEntity
│   └── base.py              # Base entity class implementation
├── entity_utils/            # Entity helper utilities
│   ├── device_area.py       # Container devices follow the server device's area
│   ├── dynamic_entities.py  # Add/remove entities as server resources change
│   ├── nut_status.py        # UPS payload access and status-flag decoding
│   └── permissions.py       # API token permission checks
├── utils/                   # Generic helpers
│   ├── string_helpers.py    # Naming and slug helpers
│   └── validators.py        # Value validation
├── brand/                   # Integration icons
├── translations/            # Localization files
│   └── en.json              # English translations
└── <platform>/              # sensor, binary_sensor, switch
    ├── __init__.py          # Platform setup
    └── <resource>.py        # Entities per resource type (disks, pools, lxc, …)
```

The integration ships no `services.yaml`, no `repairs.py` and no service
actions — it is monitoring plus switches, driven entirely by the coordinator.

## Core Components

### Data Update Coordinator

**Directory:** `coordinator/`

The coordinator package manages periodic data fetching from the external API and distributes
updates to all entities. It is organized as a package with separate modules for different concerns:

**Package structure:**

- `base.py` - Main coordinator class (`MOSDataUpdateCoordinator`)
- `docker_templates.py` - Caches each Docker container's MOS template, the only
  source for its icon and for the port mapping a stopped container's web link
  needs. Keyed by container id: MOS recreates a container when its template is
  edited, so the id already in the poll's payload invalidates the cache and the
  steady state issues no requests

**Core functionality:**

- Configurable update interval (default: 30 seconds, 30–3600 via the options flow)
- Shared data access for all entities
- Automatic retry on transient failures
- Per-resource failure handling: a transient 429 or communication error on an
  optional resource keeps last-known-good data instead of tearing down entities,
  while the rest of the poll is applied normally. A rejected token or a failure
  on an always-fetched resource still fails the whole cycle
- Scope denials are permanent rather than transient: a 403 naming the resource
  is recorded in `forbidden_resources` (`_absorb_scope_denials`), which stops it
  being requested again for the life of the entry and covers every resource
  sharing that scope. The data is kept but reported stale, so the entities go
  unavailable without leaving the registry. This is the only way to learn about
  a permission MOS enforces but omits from the token's own scope list - 0.5.x
  does exactly that with `nut`
- A cap on that retention: once a resource has been failing for both
  `RESOURCE_STALE_GRACE_PERIOD` and `RESOURCE_STALE_MIN_FAILURES`, it is listed
  in `stale_resources` and the entities backed by it report themselves
  unavailable (`MOSEntity.available`). The data is still retained, so nothing is
  removed from the registry and recovery needs no reload. Because the
  coordinator runs with `always_update=False`, a change to that set explicitly
  notifies listeners - a stale resource's data is unchanged by definition, so
  Home Assistant's own change comparison would otherwise suppress the update

**Key class:** `MOSDataUpdateCoordinator` (exported from `coordinator/__init__.py`)

**Design rationale:**

The coordinator is structured as a package rather than a single file to support future extensibility:

- **Separation of concerns**: Core logic, error handling, and data processing are isolated
- **Easy extension**: New features (caching, metrics, webhooks) can be added as new modules
- **Maintainability**: Each module stays focused on a single concern
- **Testability**: Each module can be tested independently

### API Client

**Directory:** `api/`

Handles all communication with external APIs or devices. Implements:

- Async HTTP requests using `aiohttp`
- Connection management and timeouts
- Authentication handling
- Request pacing (`_RateLimiter`) to stay under the server's per-token rate
  limit, applied to reads, writes and config-flow validation alike
- Error translation to custom exceptions. The auth split follows the response
  body, not the status code: MOS answers 403 both for a token it does not know
  and for a resource that token may not read, and only ever answers 401 when no
  credentials arrive at all. `_raise_for_forbidden` tells the two apart

**Key class:** `MOSApiClient`

### Config Flow

**Directory:** `config_flow_handler/`

Implements the configuration UI for adding and configuring the integration. The package
is organized modularly to support complex flows without becoming monolithic.

**Structure:**

- `config_flow.py`: Main flow (user setup, reauth, reconfigure)
- `options_flow.py`: Options flow for post-setup configuration
- `schemas/`: Voluptuous schemas for all forms
- `validators/`: Validation logic separated from flow logic

**Supported flows:**

- Initial user setup with validation
- Options flow for post-setup configuration
- Reauthentication flow for a rejected API token
- Reconfigure flow for changing host, port and TLS settings

**Key classes:**

- `MOSConfigFlowHandler` (main flow)
- `MOSOptionsFlow` (options)

### Base Entity

**Package:** `entity/`

Provides common functionality for all entities in the integration:

- Device information
- Unique ID generation
- Coordinator integration
- Availability tracking

**Key class:** `MOSEntity` (in `entity/base.py`)

## Platform Organization

Each platform (sensor, binary_sensor, switch, etc.) follows this pattern:

```text
<platform>/
├── __init__.py              # Platform setup: async_setup_entry()
└── <entity_name>.py         # Individual entity implementation
```

Platform entities inherit from both:

1. Home Assistant platform base (e.g., `SensorEntity`)
2. `MOSEntity` for common functionality

## Data Flow

```text
┌─────────────────┐
│  Config Entry   │ ← Created by config flow
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Coordinator   │ ← Fetches data from API every scan_interval (default 30 s)
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │  Data   │ ← Stored in coordinator.data
    └────┬────┘
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌─────────┐
│ Sensor  │         │ Switch  │ ← Entities read from coordinator
└─────────┘         └─────────┘
```

## AI Agent Instructions

Coding agents read `AGENTS.md` for project-wide rules and the path-specific
`.github/instructions/*.instructions.md` files for per-file-type patterns; each
of those declares its own scope in an `applyTo` frontmatter glob. Keep
`AGENTS.md` high-level and put detailed patterns in the instruction files.

## Key Design Decisions

See [DECISIONS.md](./DECISIONS.md) for architectural and design decisions made during development.

## Extension Points

To add new functionality:

### Adding a New Platform

1. Create directory: `custom_components/mos/<platform>/`
2. Implement `__init__.py` with `async_setup_entry()`
3. Create entity classes inheriting from platform base + `MOSEntity`
4. Add platform to `PLATFORMS` in `const.py`

### Modifying Data Structure

1. Update the coordinator data type in `coordinator/base.py`
2. Adjust API client response parsing in `api/client.py`
3. Update entity property implementations to match new structure

## Testing Strategy

- **Unit tests:** Test individual functions and classes in isolation
- **Integration tests:** Test coordinator with mocked API
- **Fixtures:** Shared test fixtures in `tests/conftest.py`

Tests mirror the source structure under `tests/`.

## Dependencies

Core dependencies (see `manifest.json`):

- `aiohttp` - Async HTTP client
- Home Assistant 2026.8.0+ (see `hacs.json`) - Platform requirements

Development dependencies (see `requirements_dev.txt`, `requirements_test.txt`).
