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

### Container Devices Carry Their Kind in `model_id`

**Date:** 2026-08-16

**Context:** A dashboard card — in its own repository, not this one — wants to render "every Docker container on this
server" and to follow the list as containers come and go. The lifecycle half already works:
`async_setup_dynamic_entities` adds and removes entities and their devices as MOS's own lists change. The selection
half did not. Nothing on a container device said what kind of thing it was: `manufacturer` is `"MOS"` for all of them,
`model` was unset, and the only discriminator was the shape of the device `identifiers`
(`{entry_id}_docker_{name}` versus `_lxc_`, `_vm_`, `_disk_`, `_pool_`) or the English prefix in the display name.
Both are internal — one is a format we reserve the right to change, the other is the user's to rename.

**Decision:** Add a `MOSDeviceKind` enum in `const.py` and write its value to each container device's `model_id`:
`docker_container`, `compose_stack`, `lxc_container`, `virtual_machine`, `disk`, `storage_pool`, `ups`. Every platform
that builds entities for a device (sensor, binary_sensor, switch) passes the same kind through the new `device_kind`
argument on `MOSEntity`. The kinds MOS provides itself additionally get a human-readable `model` from
`DEVICE_KIND_MODEL_NAMES` ("Docker Container", "Compose Stack", "LXC Container", "Virtual Machine", "Storage Pool").
The server device is untouched — it is the MOS server and needs nothing to tell it apart.

**Rationale:**

- `model_id` is the one field on a device that is machine-readable by contract. `model` is a display string, the name
  is the user's, and `identifiers` carry a format that is ours alone. Home Assistant serializes `model_id` into the
  device registry's `dict_repr`, so it reaches the frontend in the `config/device_registry/list` call a card makes
  anyway, and `device_attr(id, 'model_id')` reaches it from a template.
- Splitting display name from identifier is the reason both fields exist. A card matching `model_id` is immune to
  `model` being reworded or localized later.
- Labels were the alternative and were rejected. They are not part of `DeviceInfo`, so an integration setting them
  means imperative label-registry writes in the dynamic-add path — the one place that currently performs no registry
  writes at all. Worse, labels are the _user's_ namespace: re-applying one the user deleted fights them on every
  reload, while applying it only once silently skips every container created afterwards, which is exactly the
  auto-sync property this was for. `label_id` also derives from a user-renamable name, making it a weaker anchor
  than `model_id`. Users remain free to label these devices themselves, on top.
- This does not reopen the rejected mapping from _Docker Template Metadata Rides on the Container State Sensor_.
  What was dropped there was putting a container's `repo` and image tag in `model`/`sw_version` — mutable per-container
  data in fields read once at entity construction. A kind is fixed for the life of the device.

**Consequences:**

- The `model_id` values are a public contract from here on. A card or template matching on them breaks if a value
  changes, so they are fixed once released; the `MOSDeviceKind` docstring says so.
- `DEVICE_KIND_MODEL_NAMES` deliberately omits `DISK` and `UPS`. Both are real hardware and `model` belongs to their
  actual model: the UPS fills it from its NUT driver (`MOSDeviceHardware`) and leaves it blank when the driver reports
  nothing, which `test_ups_device_omits_hardware_the_driver_does_not_report` pins down — a blanket `"UPS"` would
  destroy that "not reported" signal. A disk's real model is a sensor today and its device `model` stays empty; moving
  it onto the device would also drop `manufacturer: MOS`, which is wrong for third-party hardware anyway.
- `model` is not translatable — `DeviceInfo` can translate a device's name but not its model, matching how Home
  Assistant treats models everywhere else. The English strings are shown as-is.
- Every entity sharing a device must pass the same kind. They all describe one device, so a disagreement would be
  resolved by whichever entity registered last.

---

### Compose Stack Usage Has Its Own Option and Its Own Sum

**Date:** 2026-08-29

**Context:** A Compose stack is a device like a Docker container, and a dashboard covering both wants the same CPU and
memory fields from each. MOS reports neither for a stack. The figures exist only in the Docker Engine's stats
endpoint, which answers for one container at a time and takes about a second per call, and a stack's members are
generated containers (`compose_<stack>-<service>-1`) that appear only in the raw engine list.

**Decision:** Sum the running members' figures into per-stack `cpu_usage`, `memory_usage` and `memory_percent`
sensors, behind `enable_compose_stats` — a second option, off by default, separate from `enable_docker_stats`. Which
stacks are measured follows from `ComposeStatsContext`, the stack counterpart of `DockerStatsContext`. The percentage
is reported only when every measured member reports the same memory limit.

**Rationale:**

- The two options measure different amounts of work. A Docker container costs one request per device; a stack costs
  one per running service, so a handful of large stacks costs more than a long list of containers. Folding them into
  one toggle would sign a user up for the second bill on accepting the first.
- The engine stats endpoint answers for a generated member name exactly as it does for a MOS-managed container, so
  the collector needs no new client call — only a caller that decides which members are running, which the engine
  list already in the poll supplies.
- Only running members are measured. Docker answers for a stopped container with zeroes, which would read as an idle
  service rather than an absent one.
- CPU and used bytes add up because both are absolute amounts on the same host. A percentage does not: it needs a
  single budget, and members share one only when they are limited alike — the usual case, since Docker reports an
  unconstrained container as limited to the host's entire RAM. Where they differ there is no denominator, and the
  sensor reads unknown rather than authoritative-looking nonsense.

**Consequences:**

- A stack's stats sensors read unknown for one poll after a start or reload: the first refresh runs before any entity
  registers a context.
- Nothing is carried forward. A poll without the engine list, or one where every member's request fails, blanks the
  figures instead of holding the previous ones, which a reader cannot tell from live values.
- `enable_compose_stats` is a released option name from here on; renaming it silently resets the setting.

---

### Container Usage Is Read From MOS, and Reported as CPU and Bytes Only

**Date:** 2026-08-30

**Context:** MOS answers `/docker/mos/containers` and `/docker/mos/compose/stacks` with a `performance` block when
asked with `?performance=true`, carrying CPU and memory for each container and each stack. The alternative source,
the Docker Engine stats endpoint, charges one request per running container and reports on Docker's own scale, where
one fully-busy core is 100% and a four-core host tops out at 400%. MOS reports against the whole machine, so its
figure for the same container is smaller by the core count, and it sends no memory limit at all.

**Decision:** Prefer the `performance` block wherever a payload carries one and take its CPU figure unmodified. Report
memory as bytes only, with no percentage and no limit. The Engine path stays as the fallback for a server whose API
predates the parameter, selected per payload rather than by version.

**Rationale:**

- Docker CPU now reads on the same scale as the LXC and VM sensors beside it on the same device page, which take
  MOS's figure already. The integration reported two different scales before, which is not defensible once both are
  visible in one dashboard.
- Scaling MOS's figure back up by the core count would preserve the old values, but it encodes a guess about a
  formula the integration does not own; a change on the MOS side would silently distort every reading.
- A memory percentage needs a budget to divide by, and MOS reports none for any kind. Host RAM is the only denominator
  available, and against it every container on a NAS with room to spare reads as a fraction of a percent — a flat line
  that says less than the byte figure beside it. Portainer and Proxmox both ship a percentage, but both divide by the
  budget of the guest itself and expose that limit as its own sensor; neither shape is reachable here.
- Home Assistant ships the same reading for Supervisor add-ons, which are Docker containers, and disables it by default
  (`hassio/sensor.py`). A figure whose own source turns it off is a weak reason to keep an entity alive.
- An old server degrades on its own: the parameter is ignored rather than rejected, and the absent block selects the
  fallback per container, so no minimum MOS version has to be declared.

**Consequences:**

- Docker and Compose CPU values drop by the host's core count at the upgrade, and recorded history has a step in it.
- The `memory_percent` sensors are gone from Docker and Compose, along with their history.
  `async_remove_retired_entities` deletes the registry rows, without which Home Assistant would keep publishing them
  as unavailable forever.
- Should MOS ever report a per-guest memory limit, the sensor comes back against that limit rather than against host
  RAM, and all four kinds can carry it.
- Two sources have to be kept working for as long as the fallback exists, and `DOCKER_STATS_FIELDS` is the seam
  between them.
- `enable_docker_stats` and `enable_compose_stats` no longer guard any request cost on a current server. They still
  decide whether the sensors exist, which is now their only job.

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
