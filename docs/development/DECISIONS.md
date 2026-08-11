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

### Defer the Home Assistant 2026.8 Move and Own the Files Coupled to It

**Date:** 2026-08-11

**Context:** Blueprint template sync #64 proposed a newer `pytest-homeassistant-custom-component` pin, a
`script/setup/seed-http-config` script and device registry guidance rewritten for Home Assistant 2026.8 — but not the
version bump itself, because `hacs.json` is listed in `.templatesyncignore` and can never arrive by sync. Merged as
proposed, the script would have aborted `script/develop` with a `ModuleNotFoundError` (it imports
`homeassistant.components.http.config`, which does not exist before 2026.8), and the new guidance would have directed
agents to `async_get_device_by_identifier()`, absent before 2026.8, against code that deliberately uses `via_device`
and `async_get_device()`.

**Decision:** Keep `hacs.json` at `2026.4.0` for now, close #64 unmerged, and take ownership of the files coupled to
the version: `requirements_test.txt` permanently, and the four rewritten `blueprint.*.instructions.md` files
temporarily. The move itself is planned as one deliberate change in
[HA_2026_8_MIGRATION.md](HA_2026_8_MIGRATION.md).

**Rationale:**

- `pytest-homeassistant-custom-component` pins one exact Home Assistant version, so it must track `hacs.json`.
  `.github/dependabot.yml` already says so and excludes both from automatic updates; a sync bypassed that policy.
- The 2026.8 device registry changes are deprecations, not breaks — `via_device` has a removal target of HA Core
  2027.8 — so there is runway to do this properly rather than under sync pressure.
- Replacing `via_device` with `via_device_id` needs the server device's registry id at a point where only identifiers
  are known. That is a design question, not a mechanical rename, and does not belong in a template sync.

**Consequences:**

- The four instruction files stay frozen until the move; unrelated blueprint improvements to them are missed
  meanwhile. The `TEMPORARY` block in `.templatesyncignore` names the removal condition.
- `requirements_test.txt` is bumped by hand from now on, together with `hacs.json`.
- `script/develop` and `script/setup/setup` stay synced, so a future sync can still propose the `seed-http-config`
  call sites. Until the move is done, a sync PR carrying them must not be merged — the migration checklist covers the
  correct order.

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
