# Home Assistant 2026.8 migration

**Status:** planned, not started.
**Current target:** `hacs.json` declares `2026.4.0`, so `script/setup/bootstrap` installs the latest 2026.4 patch.

This document is the checklist for moving the integration to Home Assistant 2026.8. It exists because the blueprint
template sync (#64) started proposing the _consequences_ of that move — a newer test pin, an HTTP config seeding
script, rewritten device registry guidance — without the move itself. `hacs.json` is listed in `.templatesyncignore`,
so the version bump can never arrive by sync; it has to be made here, deliberately, in one piece.

## Why this is one change and not several

Four things are pinned to each other. Changing one alone leaves the repository inconsistent:

| Item                                                              | Today                                       | After                                                |
| ----------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------------------- |
| `hacs.json` → `homeassistant`                                     | `2026.4.0`                                  | `2026.8.0`                                           |
| `requirements_test.txt` → `pytest-homeassistant-custom-component` | `0.13.325` (pins `homeassistant==2026.4.4`) | `0.13.354` (pins `homeassistant==2026.8.0`)          |
| `config/configuration.yaml` → `http:` block                       | in use                                      | removed, replaced by `script/setup/seed-http-config` |
| `.github/instructions/blueprint.*` device registry rules          | held back in `.templatesyncignore`          | adopted                                              |

`.github/dependabot.yml` already encodes the first two belonging together: it excludes both `homeassistant` and
`pytest-homeassistant-custom-component` from automatic updates, with the note that they are bumped by hand together
with `hacs.json`. Note that `script/setup/bootstrap` installs `homeassistant==${HA_VERSION}` _after_
`requirements_test.txt`, so the `hacs.json` value wins in the venv regardless of what the test pin says — bumping only
one of them produces a venv that silently disagrees with the test dependency.

## Checklist

### 1. Version pins

- [ ] `hacs.json`: `"homeassistant": "2026.4.0"` → `"2026.8.0"`
- [ ] `requirements_test.txt`: `pytest-homeassistant-custom-component==0.13.325` → `==0.13.354`
- [ ] Rebuild the environment so the venv is recreated: `script/setup/bootstrap` detects the version change via
      `$VENV_PATH/.ha-version` and rebuilds automatically
- [ ] Optionally refresh the `2026.4` examples in `.devcontainer/.env`, `.devcontainer/.env.local.example` and
      `script/.lib/ha_version.sh` comments (cosmetic; `.devcontainer/.env` is sync-ignored, the other two are not)

### 2. HTTP configuration

Since 2026.8 the `http:` YAML block is imported into `config/.storage/http` on first boot and ignored on every boot
after that, with a Repairs warning asking for its removal. `config/` is sync-ignored, so the blueprint's own removal of
that block never reaches this repository — it has to be done by hand.

- [ ] Remove the `http:` block from `config/configuration.yaml` (currently lines 32–48: `server_host`,
      `ip_ban_enabled`, `use_x_forwarded_for`, `trusted_proxies`, `cors_allowed_origins`)
- [ ] Take `script/setup/seed-http-config` from the blueprint
- [ ] Take both of its call sites — `script/develop` and `script/setup/setup`

**Order matters.** The seeding script imports `homeassistant.components.http.config`, which does not exist before
2026.8, and both call sites run under `set -euo pipefail` without a guard. Adding the script or its calls while the
venv still holds 2026.4 breaks `script/develop` with a `ModuleNotFoundError` before Home Assistant even starts. Do
step 1 first, and verify the new venv is active.

Also note the script only writes `config/.storage/http` when that file does not already exist, so on an environment
that has booted 2026.8 once, the settings it seeds have to be changed in Settings → System → Network instead.

### 3. Device registry deprecations

Home Assistant 2026.8 assigns every device to exactly one config entry and at most one subentry. **None of this is a
hard break in 2026.8** — the old APIs still work — but each one is deprecated, and `via_device` has a stated removal
target of HA Core 2027.8. The registry storage also migrates itself to version 3.2 on first 2026.8 boot, rewriting
`via_device_id` links and splitting pre-migration composite devices; existing installations are migrated by Home
Assistant, not by this integration.

Call sites in this repository:

| Location                                                     | Today                                                      | Replacement                                                                |
| ------------------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| `custom_components/mos/entity/base.py:132`                   | `via_device=(entry.domain, entry.entry_id)`                | `via_device_id=<server device id>`                                         |
| `custom_components/mos/entity_utils/device_area.py:86`       | `async_get_device(identifiers={(DOMAIN, entry.entry_id)})` | `async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)` |
| `custom_components/mos/entity_utils/device_area.py:83`       | `entry.entry_id not in device.config_entries`              | compare against `device.config_entry_id`                                   |
| `custom_components/mos/entity_utils/dynamic_entities.py:132` | `async_get_device(identifiers={device_identifiers})`       | `async_get_device_by_identifier(identifier, entry.entry_id)`               |
| `tests/` (7 files)                                           | `async_get_device(identifiers=...)`                        | entry-scoped lookup, asserting ownership by `config_entry_id`              |

- [ ] Replace the lookups — `async_get_device_by_identifier(identifier, config_entry_id)` takes a single identifier
      tuple, not a set, and is unambiguous by construction
- [ ] Replace `device.config_entries` with `device.config_entry_id` in `device_area.py`
- [ ] Decide on `via_device`. The replacement `via_device_id` needs the _registry id_ of the server device, which is
      not known when `DeviceInfo` is built in `entity/base.py`; container devices are created before or alongside the
      server device. Either resolve the server device first and pass its id, or keep `via_device` until closer to
      2027.8 and record that choice here. This is the one item with real design content — the rest is mechanical.
- [ ] Update the device docstrings in the six sensor modules that describe the `via_device` link
      (`sensor/docker.py`, `sensor/vm.py`, `sensor/nut.py`, `sensor/pools.py`, `sensor/disks.py`, `sensor/lxc.py`) and
      in `entity_utils/device_area.py`

### 4. Template sync ownership

- [ ] Remove the four `.github/instructions/blueprint.{config_flow,entities,python,tests}.instructions.md` lines from
      `.templatesyncignore`, together with the `TEMPORARY` comment block above them
- [ ] Let the next sync bring those files in, or fetch them now with
      `git checkout blueprint/main -- <path>` — `script/compare-blueprint` shows what differs
- [ ] Leave `requirements_test.txt` in `.templatesyncignore`: it stays maintainer-owned because of the pin coupling
      described above, and is bumped by hand as part of step 1

### 5. Verification

- [ ] `script/check` (type-check, lint, spell)
- [ ] `script/test` — the device registry assertions in `tests/entity/test_base.py`, `tests/sensor/test_nut.py`,
      `tests/entity_utils/test_device_area.py`, `tests/test_diagnostics.py` and the three `tests/binary_sensor/`
      modules are the ones most likely to move
- [ ] `script/hassfest`
- [ ] `script/develop` — confirm Home Assistant starts, no Repairs warning about the `http:` block, and the dev
      instance is still reachable through the Codespaces/DevContainer proxy
- [ ] In the running instance: container, VM, pool, disk and UPS devices still appear under the server device, and
      area inheritance still works

## Reference: what changed in 2026.8

Verified against `home-assistant/core` at tag `2026.8.0`:

- `homeassistant/components/http/config.py` is new in 2026.8 (absent in 2026.4), providing `HTTP_STORAGE_SCHEMA`,
  `STORAGE_KEY`, `STORAGE_VERSION` and `STORAGE_MINOR_VERSION`
- `DeviceRegistry.async_get_device_by_identifier(identifier, config_entry_id)` and the matching
  `async_get_device_by_connection()` are new; `async_get_device()` still exists but resolves ambiguity heuristically
  when several config entries share an identifier
- `DeviceInfo.via_device` is marked deprecated in favour of `via_device_id`, with removal announced for HA Core 2027.8
- `DeviceEntry.config_entries` and `DeviceEntry.config_entries_subentries` are deprecated compatibility properties;
  `DeviceEntry.config_entry_id` is the single-owner replacement
- Device registry storage moves to version 3.2, which rewrites `via_device_id` links across split composite devices
- `UnitOfDensity` is new; `CONCENTRATION_MICROGRAMS_PER_CUBIC_METER` is what 2026.4 has. This integration uses
  neither, so the change is documentation-only here
- `DeviceEntry.suggested_area` is deprecated with removal announced for 2026.9. This integration does not use it, but
  `entity_utils/device_area.py` works in the same area, so re-read it when moving past 2026.8
