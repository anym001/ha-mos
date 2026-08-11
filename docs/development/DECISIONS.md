# Architectural and Design Decisions

This document records significant architectural and design decisions made during the development of this integration.

## Format

Each decision is documented with:

- **Date:** When the decision was made
- **Context:** Why this decision was necessary
- **Decision:** What was decided
- **Rationale:** Why this approach was chosen
- **Consequences:** Expected impacts and trade-offs

---

## Decision Log

### Use DataUpdateCoordinator for All Data Fetching

**Date:** 2025-11-29 (Template initialization)

**Context:** The integration needs to fetch data from an external API and share it with multiple entities. Home Assistant provides several patterns for this.

**Decision:** Use `DataUpdateCoordinator` from `homeassistant.helpers.update_coordinator` as the central data management component.

**Rationale:**

- Provides built-in support for update intervals and error handling
- Automatic retry with exponential backoff
- Shared data access prevents duplicate API calls
- Standard pattern recommended by Home Assistant
- Entities automatically become unavailable when coordinator fails

**Consequences:**

- All entities must inherit from `CoordinatorEntity`
- Single update interval applies to all entities
- Data is fetched even if no entities are enabled
- Coordinator manages entity lifecycle and availability

---

### Separate API Client from Coordinator

**Date:** 2025-11-29 (Template initialization)

**Context:** The coordinator needs to fetch data, but business logic should be separated from data transport.

**Decision:** Implement API communication in separate `api/client.py` module, coordinator only orchestrates updates.

**Rationale:**

- Separation of concerns: transport vs. orchestration
- Easier to test API client in isolation
- Simpler to swap API implementation if needed
- Clearer error handling boundaries

**Consequences:**

- Additional abstraction layer
- Coordinator depends on API client
- API client raises custom exceptions for error translation

---

### Platform-Specific Directories

**Date:** 2025-11-29 (Template initialization)

**Context:** Integration supports multiple platforms (sensor, binary_sensor, switch, etc.).

**Decision:** Each platform gets its own directory with individual entity files.

**Rationale:**

- Clear organization as integration grows
- Easier to find specific entity implementations
- Supports multiple entities per platform cleanly
- Follows Home Assistant Core pattern

**Consequences:**

- More files/directories than single-file approach
- Platform `__init__.py` must import and register entities
- Slightly more initial setup overhead

---

### EntityDescription for Static Metadata

**Date:** 2025-11-29 (Template initialization)

**Context:** Entities have static metadata (name, icon, device class) that doesn't change.

**Decision:** Use `EntityDescription` dataclasses to define static entity metadata.

**Rationale:**

- Declarative and easy to read
- Type-safe with dataclasses
- Recommended Home Assistant pattern
- Separates static configuration from dynamic behavior

**Consequences:**

- Each entity type needs an EntityDescription
- Dynamic entities need custom handling
- Static and dynamic properties clearly separated

---

### Move to Home Assistant 2026.8, Keeping `via_device` Until 2027.8

**Date:** 2026-08-11

**Context:** Blueprint template sync #64 proposed a newer `pytest-homeassistant-custom-component` pin, a
`script/setup/seed-http-config` script and device registry guidance rewritten for Home Assistant 2026.8 — but not the
version bump itself, because `hacs.json` is listed in `.templatesyncignore` and can never arrive by sync. Merged as
proposed, the script would have aborted `script/develop` with a `ModuleNotFoundError` (it imports
`homeassistant.components.http.config`, which does not exist before 2026.8), and the new guidance would have directed
agents to `async_get_device_by_identifier()`, absent before 2026.8. #64 was closed unmerged and the move made here
instead, in one piece.

**Decision:** Raise `hacs.json` to `2026.8.0` and `pytest-homeassistant-custom-component` to `0.13.354` together;
drop the `http:` block from `config/configuration.yaml` in favour of `script/setup/seed-http-config`; adopt the
entry-scoped registry lookups; and keep `via_device` for now. `requirements_test.txt` stays maintainer-owned in
`.templatesyncignore`; the four instruction files were adopted and no longer are.

**Rationale:**

- `pytest-homeassistant-custom-component` pins one exact Home Assistant version, so it must track `hacs.json`.
  `.github/dependabot.yml` already says so and excludes both from automatic updates.
- Since 2026.8 a device belongs to exactly one config entry, and identifiers are unique only within one.
  `async_get_device_by_identifier(identifier, config_entry_id)` cannot be ambiguous, so the lookups moved over
  unconditionally, as did `DeviceEntry.config_entry_id` in place of the deprecated plural `config_entries`.
- `via_device` did not. Its replacement `via_device_id` wants the server device's _registry id_, which does not exist
  yet when container devices declare their `DeviceInfo` — both are built in the same setup pass. Home Assistant
  resolves the identifier at registration and prefers a match in the same config entry, so the link is unambiguous
  here and logs no deprecation warning. Converting it means restructuring entity construction, which is a change worth
  making on its own rather than inside a version bump.
- Python needed no change: the project already required `>=3.14`, which is what 2026.8 wants.

**Consequences:**

- `via_device` is removed in HA Core 2027.8. Before then, either resolve the server device first and pass
  `via_device_id`, or accept the link breaking. `AGENTS.md` records this as a deliberate deviation from
  `blueprint.entities.instructions.md`, which says never to use it.
- `requirements_test.txt` is bumped by hand from now on, together with `hacs.json`.
- Fresh environments get their dev network settings from `script/setup/seed-http-config` rather than
  `configuration.yaml`. On an instance that has already booted, the script leaves an existing
  `config/.storage/http` alone — change those settings in Settings → System → Network.
- The device registry migrates itself to storage version 3.2 on first 2026.8 boot, splitting pre-migration composite
  devices. Existing installations are migrated by Home Assistant, not by this integration.
- Generated entity IDs now start with the area name: 2026.8 defaults `entity_id_parts` to area + device + entity.
  Only IDs generated from then on are affected — entities already in the registry keep theirs — so it shows up
  precisely where this integration files a new device into the server's area, e.g. a pool added later becomes
  `binary_sensor.office_sirius_pool_later_problem`. Tests must therefore find such devices by identifier rather than
  by a hardcoded entity ID.

---

## Future Considerations

### State Restoration

**Status:** Not yet implemented

Consider implementing state restoration for switches and configurable settings to maintain state across Home Assistant restarts when the external device is unavailable.

### Multi-Device Support

**Status:** Not yet implemented

Current architecture assumes single device per config entry. If multi-device support is needed, coordinator data structure will need redesign to map device ID → data.

### Polling vs. Push

**Status:** Uses polling

Currently implements polling-based updates. If the API supports webhooks or WebSocket, consider implementing push-based updates for real-time responsiveness.

---

## Decision Review

These decisions should be reviewed periodically (suggested: quarterly or when major features are added) to ensure they still serve the integration's needs.
