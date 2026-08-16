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

### Docker Template Metadata Rides on the Container State Sensor

**Date:** 2026-08-14

**Context:** A Docker container's MOS template carries things no other endpoint answers: an icon URL, a web interface
link that survives the container being stopped, and — via the container's labels — the standard OCI image title,
description and source. None of it is a measurement, all of it describes the container, and the point of collecting it
was that a dashboard row (icon, name, state, link) should come from a single entity instead of a template.

**Decision:** Hang it off the per-container **state sensor**: the icon as `entity_picture`, the rest as
`extra_state_attributes` (`web_ui_url`, `repo`, `network_mode`, `image_title`, `image_description`, `image_source`).
The container device additionally gets the web link as its `configuration_url`. The icon URL is handed to the frontend
as-is, so the browser rendering the dashboard fetches it, not Home Assistant.

**Rationale:**

- The device registry has no icon or picture field — only `manufacturer`, `model`, `sw_version`,
  `configuration_url` and friends. Device level is therefore not an option for the icon at all, while `entity_picture`
  is a documented common property of every entity, not an improvisation.
- The state sensor is the recorder-cheap host. Attributes are written alongside state changes, and this sensor moves
  only when the container starts or stops. The same attributes on `cpu_usage` would ride along on every poll.
- One entity per descriptive field (title, description, source, repo, network mode) would add five to six entities per
  container — a few hundred on a well-stocked server — none of which has history worth keeping. The pattern to avoid is
  putting _measurements_ in attributes; static descriptive strings are the case attributes exist for.
- An `image` entity per container would make Home Assistant itself fetch every icon from a public CDN on the server
  side. Letting the browser do it keeps that cost and that third-party contact where the user can see it.
- Mapping `repo` to the device's `model` and the tag to `sw_version` was considered and dropped: device info is read
  when the entity is added, and the installed version already has its own sensor that stays current.
- Putting the picture on the power switch instead was dropped for the reason the state sensor exists at all — the
  switch collapses the state to on/off.

**Consequences:**

- `entity_picture` points at a third-party CDN (GitHub raw, jsDelivr). Every dashboard viewer's browser contacts it,
  and the picture stays blank for a browser without internet access. `resolve_icon` therefore accepts nothing but
  plain `http(s)` URLs.
- The attributes are not individually historized or graphable; anyone wanting that has to template them out.
- Which labels may reach an entity is an allow-list in `const.py` (`DOCKER_LABELS_KEPT`), because coordinator data ends
  up in the diagnostics download. A new label has to be added there deliberately.
- The device's `configuration_url` is read once, when the entity is first added: a container whose web interface moves
  to a different port updates the `web_ui_url` attribute immediately, but the device page's link follows on the next
  reload.

---

### Server-Hosted Guest Icons, Confirmed with a HEAD Probe

**Date:** 2026-08-15

**Context:** MOS ships the artwork it shows for Docker, LXC and VM guests as plain static files under its own web
root (`/docker_icons`, `/os_icons`, `/lxc_custom`), outside `/api/v1` and needing no token. Docker already surfaced an
icon via its MOS template, but that URL points at a public CDN a dashboard without internet access cannot load. LXC
and VMs had no icon at all. Which file a guest points at is a property of the guest (`custom_icon`/`distribution` for
LXC, `customIcon`/`icon` for VMs, camelCase), reported only by `/lxc/containers` and `/vm/machines` - neither field
appears on the `/usage` endpoints the coordinator already polls.

**Decision:** Add `coordinator/guest_icons.py` (`GuestIconCache`), which fetches the two configuration endpoints
separately from the regular poll, resolves each guest's candidate icon path, and confirms it with a HEAD request
before handing a URL to the frontend. Docker's `icon_url` now prefers this server-hosted copy over the template's CDN
URL, which stays as the fallback. The resolved URL rides the state sensor's `entity_picture`, the same place Docker's
existing icon already lived (see "Docker Template Metadata Rides on the Container State Sensor" above).

**Rationale:**

- A guest with no artwork answers 404, and an `entity_picture` that 404s renders as a broken image on every card
  showing that entity - visibly worse than no picture at all. The HEAD probe is what keeps a missing icon invisible
  instead of broken.
- Both halves of the lookup are cached, and for different reasons: which file a guest points at changes only when the
  guest is edited, while whether that file exists changes only when artwork is uploaded. A miss is re-checked after an
  hour so newly uploaded artwork appears without restarting Home Assistant; a hit is never re-checked, since a file
  the server already confirmed cannot stop existing in a way that matters here.
- The configuration endpoints are fetched rarely rather than folded into the regular poll: nothing on them changes
  every 30 seconds, and a guest the endpoint has not listed yet is retried at a floored rate rather than on every
  single poll, so a server that never lists a guest cannot turn into a request storm.
- A failed configuration fetch or a transport error on a probe never raises - it is reported as "no icon" and the
  previous cached configuration is kept. An icon is not worth taking a poll down over.
- _Which_ failure it was still decides what happens next, following the same split the coordinator applies to the
  resources it polls (see the exception hierarchy in `api/__init__.py`): a scope denial is permanent and the endpoint
  is dropped for the life of the entry, a 404 stays in the rotation so a MOS update needs no reload but loses the
  early-refetch trigger, and everything else is transient. Collapsing the three would leave a doomed request
  repeating at the 60-second floor forever - the exact outcome `forbidden_resources` exists to prevent.

**Consequences:**

- `MOSApiClient.root_url` now exists alongside the existing `/api/v1`-scoped base URLs, since the icon directories are
  addressed relative to the server's origin, not to either API base.
- A guest's resolved `icon_url` carries the configured host once it points at the server's own web root - unlike the
  Docker template fallback, which stays a public CDN URL. Diagnostics redacts it the same way as `web_ui_url`.
- LXC and VM sensors gained a `picture_fn` on their `EntityDescription`, mirroring the pattern `value_fn` already
  established, so only the state sensor (the one `picture_fn` is set on) carries a picture.
- These two endpoints sit outside the coordinator's `forbidden_resources`/`unsupported_resources` bookkeeping, which
  drives what gets polled and which entities go unavailable - no entity is backed by them, so joining it would be
  wrong. `guest_icon_sources` reports the same two facts for them in diagnostics instead.

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
