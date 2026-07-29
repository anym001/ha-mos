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
│   └── data_processing.py   # Data validation and transformation
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
│   ├── dynamic_entities.py  # Add/remove entities as server resources change
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
- `data_processing.py` - Data validation, transformation, and caching utilities

**Core functionality:**

- Configurable update interval (default: 5 minutes)
- Shared data access for all entities
- Automatic retry on transient failures
- Per-resource failure handling: transient 401/403/429 keep last-known-good
  data instead of tearing down entities
- Data validation and transformation before distribution

**Key class:** `MOSDataUpdateCoordinator` (exported from `coordinator/__init__.py`)

**Design rationale:**

The coordinator is structured as a package rather than a single file to support future extensibility:

- **Separation of concerns**: Core logic, error handling, and data processing are isolated
- **Easy extension**: New features (caching, metrics, webhooks) can be added as new modules
- **Maintainability**: Individual modules stay focused and manageable (<400 lines)
- **Testability**: Each module can be tested independently

### API Client

**Directory:** `api/`

Handles all communication with external APIs or devices. Implements:

- Async HTTP requests using `aiohttp`
- Connection management and timeouts
- Authentication handling
- Request pacing (`_RateLimiter`) to stay under the server's per-token rate
  limit, applied to reads, writes and config-flow validation alike
- Error translation to custom exceptions

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
│   Coordinator   │ ← Fetches data from API every 5 min
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
- Home Assistant 2026.4.0+ (see `hacs.json`) - Platform requirements

Development dependencies (see `requirements_dev.txt`, `requirements_test.txt`).
