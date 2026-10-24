# MOS NAS Card Architecture

This document describes the technical architecture of the MOS NAS Card in `frontend/`. How the
integration serves the built bundle is in [`ARCHITECTURE.md`](ARCHITECTURE.md) ("Bundled Card"); what
the card offers its users is in [`frontend/README.md`](../../frontend/README.md).

## Directory Structure

```text
frontend/src/
├── mos-card.ts                  # Main card element — LitElement subclass
├── devices.ts                   # Device registry subscription and model_id filtering
├── config.ts                    # Defaults, validation, editor/config conversions
├── rows.ts                      # Tone, order, row cap, group counts, waiting power buttons
├── gauge.ts                     # Ring geometry and its fixed severity scale
├── history.ts                   # Sparkline readings: recorder answer, live samples, SVG path
├── history-loader.ts            # One recorder query per entity, continued from live states
├── render.ts                    # States, figures, rings, chips and the server tiles, shared
├── overview.ts                  # What the overview card condenses a server into
├── overview-card.ts             # The overview card element — custom:mos-overview-card
├── overview-editor.ts           # Its visual editor
├── editor.ts                    # Visual editor — implements LovelaceCardEditor
├── types.ts                     # Card config interface
├── action-handler-directive.ts  # Lit directive: tap / hold / double-tap gestures
└── localize/
    ├── localize.ts              # i18n helper
    └── languages/
        ├── de.json              # German strings
        └── en.json              # English strings
frontend/tests/                  # Vitest suites over the logic modules
custom_components/mos/www/
└── mos-card.js                  # Build output, committed — the file the integration serves
```

`config.ts` and `rows.ts` hold the logic that needs no DOM, no `hass` and no render. It sits there
rather than on the component for two reasons: `CARD_DEFAULTS` is read by both `setConfig` and the
editor's form data, so the card and its editor cannot disagree about what an untouched option does,
and pure functions can be tested without driving a live Home Assistant.

## The `model_id` Contract

Everything the card renders comes out of the Home Assistant **device registry**, filtered on
`model_id`. This is a deliberate, documented contract on the integration side. The authority is
[`ARCHITECTURE.md`](ARCHITECTURE.md) ("Base Entity") and the decision log entry _Container Devices
Carry Their Kind in `model_id`_ in [`DECISIONS.md`](DECISIONS.md). Read those before changing how
matching works; this file describes only the card's side of it.

| `model_id`         | Rendered as       | Has power switch |
| ------------------ | ----------------- | ---------------- |
| `docker_container` | Docker containers | yes              |
| `compose_stack`    | Compose stacks    | yes              |
| `lxc_container`    | LXC containers    | yes              |
| `virtual_machine`  | Virtual machines  | yes              |
| `disk`             | Disks             | no               |
| `storage_pool`     | Storage pools     | no               |
| `ups`              | UPS               | no               |

Two properties follow from anchoring here rather than anywhere else.

**It survives renames and refactors.** `model_id` is machine-readable by contract. A device's
`identifiers` carry an internal format the integration reserves the right to change, and the
display name belongs to the user. Matching either would break on a rename; matching `model_id`
does not. The card matches neither, ever.

**Lifecycle comes for free.** The integration adds and removes these devices at runtime through
`async_setup_dynamic_entities`, so following the registry means a deleted container disappears from
the card, a new one shows up, and a container behind a failing MOS endpoint keeps its row and
merely reports unavailable. There is nothing to refresh by hand, and no manual refresh logic should
be added that fights this.

The MOS **server** device deliberately carries no `model_id` of its own. It is derived instead: any
device that is the `via_device_id` parent of a device with a MOS kind is by definition a MOS
server. That is what `findServerDevices()` does, and it is why the card can scope a dashboard to
one server without the integration having to label the server.

A device whose `via_device_id` names no such server — because the link is missing, or points at a
device the registry no longer has — belongs under no server heading. `selectUnassignedMosDevices()`
collects exactly those, and the card gives them a section of their own rather than dropping them:
a row that is silently absent is the worst way for the card to be wrong, because there is nothing
left to notice. With no server resolvable at all every device is unassigned, which is the same
single unheaded section the card showed before.

The `filter` option is the one deliberate exception to matching on `model_id` alone. It matches the
name a row is _displayed_ under — which `deviceDisplayName()` derives by trimming the
server-and-kind prefix the integration writes, since a card already grouped by server and kind
repeats it — and it narrows an already-selected list rather than deciding what is on it. A renamed
device therefore changes what the filter matches, which is correct: the user renamed the thing they
are filtering on.

## How a Row Is Composed

A row is anchored on one entity — the state sensor the integration documents for exactly this
purpose — and picks up the rest from the other entities on the same device.

- **Icon** — resolved in the order Home Assistant itself uses: the state sensor's `entity_picture`
  (for Docker containers, Compose stacks, LXC guests and VMs, the icon MOS shows), then its `icon`
  attribute, then what the integration declares in its `icons.json`, then the per-kind MDI icon in
  `KIND_INFO`.

  The third step needs a fetch. Since ha-mos moved its icons into `icons.json`, they are resolved in
  the frontend from the entity's `translation_key` and never appear as a state attribute — every MOS
  entity now reports no `icon` at all. `fetchIntegrationIcons()` asks for them over the same
  websocket command the frontend uses (`frontend/get_icons`), once per card, and a failure falls
  through to `KIND_INFO` rather than failing the card. Without this the card silently ignores the
  icons the integration declares: disks would draw `mdi:harddisk` where `icons.json` asks for
  `mdi:power`, and pools `mdi:database` where it asks for `mdi:harddisk`.

- **State** — the sensor's state through `hass.formatEntityState`, so enum states read in the user's
  language and units match the rest of Home Assistant.
- **Link** — the `web_ui_url` attribute of the Docker or Compose state sensor, falling back to the
  device's configuration URL. The integration omits the attribute entirely for containers and
  stacks without a web interface, so its presence is the test; a container without one gets no button rather than a
  dead one. `isLinkableUrl()` then checks the scheme against the same set Home Assistant validates
  `configuration_url` against — `http`, `https`, `homeassistant`, with a host. `web_ui_url` is an
  ordinary state attribute that nothing validates on the way, and a `javascript:` URL in an `href`
  runs in the dashboard's own context when clicked.
- **Power** — the single `switch` entity on the device. Each of the four guest kinds contributes
  exactly one — a stack's starts and stops every service in it, MOS exposing no per-service call —
  so matching the domain is enough and does not depend on the switch's name. It is
  drawn as a start/stop button rather than a toggle: a toggle states a setting, and what a guest is
  doing right now is not one.
- **Measurements** — the sensors named per kind in `KIND_INFO.metrics`, shown beside the state when
  `secondary_info` asks for them. `auto` takes the kind's own list, `cpu` and `memory` take one
  named metric and resolve to nothing on the kinds that have none. A metric reporting unavailable
  is dropped rather than printed.

  A `MetricRef` may name a total through `over`, which `resolveMetrics()` resolves alongside it and
  the row prints as one figure — `3/5`. That is what a Compose stack leads with under `auto`, since
  its two counters say nothing apart; a device missing the total keeps the count. Its CPU and memory
  follow, summed by the integration over the stack's member containers. Those two exist only while
  the integration's `enable_compose_stats` option is on, so a stack row falls back to the counter
  alone rather than to nothing.

- **Badges** — a fault badge and an update badge, both drawn on the icon. The update badge reads
  the kind's `update_available` binary sensor; only Docker containers and Compose stacks have one. The fault badge is
  not looked up by name at all: `findProblemCandidates()` returns every binary sensor on the
  device and the caller keeps those whose state carries Home Assistant's `problem` device class.
  Which of an integration's binary sensors mean "something is wrong" is not this card's judgement
  to make, and the consequence is that a fault the integration adds later is badged without the
  card being taught about it.
- **Server summary** — `SERVER_METRICS` read off the server device, which carries no `model_id` and
  is therefore never a row. These belong to the heading above the rows, not to any row.

### Waiting for the server

A start or a stop is answered by the NAS, not by the click, so the button records the switch's
state at the moment it was pressed and draws itself as waiting until something else arrives.
`settledPending()` ends a wait as soon as the switch reports anything different — including
unavailable, which is an answer of a kind — and `willUpdate` runs it before the render so the
button never flickers through a frame of spinner it no longer needs.

`PendingTimers` ends a wait nobody answered after 20 seconds. It is separate from the map of
waiting switches because the two fail differently: the map is state Lit has to see change, while a
timeout is a side effect that has to be cancelled — on an answer, and on the card being torn down,
which happens on every dashboard edit. A leaked timeout fires against a detached element.

### Layout

`getCardSize()` answers the masonry view in grid units — one per row plus one for the card's own
chrome, with a floor of 3 while the registry is still in flight so the card does not visibly jump.
The sections view asks `getGridOptions()` instead, which declares full width and content-driven
height. Only `min_columns: 6` does something on its own: it stops a dashboard from squeezing the
card to a width where every name is ellipsis.

`columns: 2` is a container query on the card's own width, not the window's — the same card is wide
in one dashboard column and narrow in three, and only a container query can tell the difference.
Below 440 px it falls back to one column. Two is the ceiling because Home Assistant gives a card
about 500 px on a default install; three were offered once and rendered as two, which is an option
that lies about what it does.

## Styling

A Lovelace card renders into its own shadow root, so none of Home Assistant's stylesheets reach it —
only CSS custom properties inherit across the boundary. Every card therefore ships its own CSS, and
the convention that matters is not _how much_ but _which values_: shape and layout belong to the
card, colours and surfaces come from the theme.

So every colour here is a `var(--…)` against a Home Assistant theme variable, and every literal hex
value in the file is the last link of a fallback chain. Those chains are not decorative:
`--ha-card-background` is unset in a stock install, and the card would render transparent rows
without the `--card-background-color` fallback behind it.

Tints are computed with `color-mix()` on the resolved colour rather than through the `--rgb-*`
duplicates a theme also exposes. Those duplicates are maintained separately and drift — a stock
install reports `--primary-text-color: #141414` alongside `--rgb-primary-text-color: 33, 33, 33`.

### Rings and sparklines

The server heading draws percentages as a 270° ring around the metric's icon, and each row draws a
percentage measurement as a ring at icon size in front of its figure. Both are plain SVG rendered by
the card itself rather than a custom element of their own: an element would be one more tag to
register, with the same registry-timing and double-load concerns as the card's own (see
`src/register.ts`), for something that has no state of its own.

The ring's colour is a fixed scale — green, amber, orange, red at 50, 75 and 90 % — on Home
Assistant's palette variables (`--green-color` and so on) rather than the theme's accent. It says
how loaded something is, which a theme has no business recolouring. Everything else, the track
included, stays on theme variables.

`show_history` costs one `history/history_during_period` query per card for the last hour of the
server's CPU load and memory usage, with `minimal_response` and `no_attributes`. After that the line
is continued from the states `hass` delivers anyway, so there is no polling and no history
subscription. The readings live on the element and survive a detach, so a card hidden and shown
again does not ask twice. Only percentages are drawn, on a fixed 0–100 scale: a sparkline scaled to
its own minimum and maximum would turn noise into drama.

The design follows AzAel76's ha-mos-card-addons (MIT); nothing is imported from it.

### The overview card

`custom:mos-overview-card` ships in the same bundle: `mos-card.ts` imports it, so one install
brings both and the picker lists both. It is a card of its own rather than a layout of the list
card because the two share almost no options — the list card's are about rows, the overview's
about sections — and one editor switching half its fields on and off would serve neither.

What the two draw alike lives in `render.ts`: state formatting, figures, rings, chips and the
server tiles, uptime and services, with their styles. `overview.ts` condenses a server into
plain values — per kind the counts, the summed guest CPU and the server's memory total for the
kind; the disks as one line; the pools and the UPS as they are — and lists every entity it read,
which is what the card's re-render check watches. The card only draws what comes out of it.

### Tones

Each row carries a `tone-*` class that the CSS maps onto a theme variable, so a state nobody
anticipated lands on the neutral one instead of on nothing. `TONES` is declared in the order
`sort: state` lists them in — one list rather than two, so what reads as "up" is what sorts to the
top.

Only kinds whose state says something about _running_ are coloured: a disk reporting `active` is
naming its ATA power mode and a pool reports how full it is, and colouring those drowns out the
containers.

Home Assistant's own tile internals (`ha-tile-icon`, `ha-tile-info`, `state-badge`) are registered
globally and would have saved this CSS. They are deliberately not used: they are internal elements
with no compatibility promise, and a core refactor would break the card silently for every user.
Only the long-stable public elements — `ha-card`, `ha-icon`, `ha-switch` — are relied on.

### Finding the state entity

`findStateEntity()` uses a three-step fallback, in this order:

1. `translation_key` equal to the kind's key (`docker_state`, `compose_state`, `lxc_state`,
   `vm_state`, `disk_power_status`, `pool_usage`, `ups_status`). This is the integration's own name for the
   entity and survives renames and `entity_id` changes.
2. A `sensor.` entity whose `unique_id` ends in the kind's description key. Older Home Assistant
   cores do not serialize `translation_key` into the `config/entity_registry/list` payload, and
   this covers them.
3. The first `sensor.` on the device, so a row still renders if the integration grows a kind this
   card has not been taught about.

**Which branch actually fires has not been observed against a live instance.** Only the first has
been reasoned about against the integration source.

`findMetricEntity()` and `findUpdateEntity()` use the same first two steps and deliberately stop
there. The last resort is right for the state entity, where a wrong guess costs a row that renders
something instead of nothing; it is wrong for these, where it would print a number that means
something else, or light up an update badge on a device that has no update.

### Re-render gating

`hass` is replaced on every state change anywhere in Home Assistant. `shouldUpdate()` therefore
compares only the entities this card displays, collected by `trackedEntityIds()` from the
registries and the config — deliberately not from the rendered rows, because `hide_unavailable`
drops rows based on state and a hidden row's entity still has to be watched for it to come back.

The set grows with the config: each row's state sensor and power switch always, its metric sensors
when `secondary_info` asks for one, its binary sensors when `show_problem` is on, and the server's
own metrics when `show_server_summary` is.
The sparkline readings are `@state`, so a recorder answer re-renders the card on its own. It is memoized on the identity of the two registries and
the config, all of which are replaced wholesale rather than mutated, so a reference check is enough
to know the list still holds.

## Build Setup

The build stays on **Rollup**. Vite's hot reload buys nothing for a Home Assistant card, because HA
loads the built bundle from a URL rather than from a dev server. Rollup produces that single bundle
directly, so the dev loop and the shipped artifact are the same thing.

`rollup.config.js` is production only and writes `custom_components/mos/www/mos-card.js`;
`rollup.config.dev.js` is what `yarn start` runs, writes `frontend/dist/` and serves it on port 5000.

Every command runs in `frontend/`:

| Command            | Description                                                                         |
| ------------------ | ----------------------------------------------------------------------------------- |
| `yarn install`     | Dependencies; the pre-commit hooks come from the repository root                    |
| `yarn check`       | Everything CI runs: lint, typecheck, test, lint:md, lint:format, lint:dedupe, build |
| `yarn build`       | Lint + production bundle (minified, ES2022 output)                                  |
| `yarn rollup`      | Production bundle only (skips lint)                                                 |
| `yarn start`       | Development watcher with rebuild on save                                            |
| `yarn lint`        | ESLint across all `src/` files                                                      |
| `yarn typecheck`   | `tsc --noEmit`                                                                      |
| `yarn lint:md`     | markdownlint                                                                        |
| `yarn lint:format` | `prettier --check`                                                                  |
| `yarn lint:dedupe` | `yarn.lock` holds a single copy of `home-assistant-js-websocket`                    |

`frontend/` keeps its own Node toolchain (Yarn 4, its own Prettier and markdownlint config). The
repository root's npm tooling and its Prettier and markdownlint hooks leave `frontend/` alone, and
`.pre-commit-config.yaml` runs the card's own hooks there instead.

> [!IMPORTANT]
> A green `yarn build` is **not** a green type check. `@rollup/plugin-typescript` reports type
> errors as warnings and still emits a bundle, so `yarn build` exits 0 on code that does not
> type-check. `yarn typecheck` is the only command that fails on one.

Rollup and Terser both target ES2022. Do not lower those targets: Lit 3 uses native `class`
syntax, and transpiling to ES5 produces `TypeError: Class constructor cannot be invoked without
'new'` at runtime.

### The committed bundle

HACS installs the repository as it is, so the built bundle is committed. A change under
`frontend/src/` therefore comes with a rebuilt `custom_components/mos/www/mos-card.js` in the same
commit. The build is deterministic — the same source and lockfile give the same bytes — and the
`Card` workflow relies on that: it rebuilds and fails when the result differs from the committed
file. The bundle is minified, so review the source diff, not the bundle diff.

The card carries no version of its own. It is released with the integration, and the integration's
version is the one Home Assistant shows.

## Tests

`yarn test` runs Vitest over `frontend/tests/`, in a plain node environment with no DOM.

What is covered is the files that hold logic rather than rendering:

- `src/devices.ts` — the `model_id` selection, the two-step entity lookups, the per-kind metric map
  and the name filter. This is the part with a contract to keep, the one documented on the
  integration side.
- `src/config.ts` — validation, defaults, and the conversions between the editor's filter lines and
  the stored `filter` key. `CARD_DEFAULTS` is read by both the card's `setConfig` and the editor's
  form data, so the two cannot disagree about what an untouched option does, and `TOGGLES` sits
  beside it so a boolean without a switch fails a test.
- `src/rows.ts` — the tone a row is drawn in, the order rows come in, the row cap, which waiting
  power buttons the incoming states have answered, and the timeouts that end a wait nobody did.
  The timers are tested with `vi.useFakeTimers()`, which is the only exercise that path gets: on a
  live instance every start and stop came back well inside the window. `countGroup` behind the
  group headings sits here too.
- `src/gauge.ts` and `src/history.ts` — the severity scale, the ring geometry, reading the
  recorder's answer, continuing it from live states and drawing it as a path.

The last two exist because that logic used to sit on the component, where the only way to check it
was to render a card against a live Home Assistant.

What is deliberately not covered is the component. Rendering `mos-card` needs a DOM shim, a `hass`
stub and a Lit update cycle, and the resulting assertions are mostly that Lit works. The card's
visible behaviour is verified against a live Home Assistant instead, which is what the pull requests
record.

Check a new test by breaking the code it covers and confirming it fails. Two tests here passed
against deliberately broken code before that was done — see the fixture note below for one, and for
the other: `expect(second.kinds).toHaveLength(MOS_DEVICE_KINDS.length)` reads the expected length
_after_ the mutation, so a shared array is compared with itself and the test passes. Capture what
you expect before you disturb anything.

`tests/fixtures.ts` builds registry entries in the shape a live instance sends: device names carry
the server-and-kind prefix the integration writes, `unique_id`s carry the config entry id followed
by the entity description key, and the server device has no `model_id`. Two habits matter when
adding to them. Fixtures that drift from the real payload let tests pass on code that cannot read
the real thing. And fixture _order_ can hide a bug: `findStateEntity` ends in a "first sensor on the
device" last resort, so entities in registry order make the `unique_id` fallback untestable — the
suite reverses them for exactly that case.

## Continuous Integration

The `Card` workflow (`.github/workflows/card.yml`) runs on every pull request and every push to
`main`: `yarn install --immutable`, `yarn check`, then the bundle comparison above. It always runs,
rather than only on changes under `frontend/`, so it can be a required check without blocking pull
requests that never start it.

`custom-card-helpers` depends on its own `home-assistant-js-websocket` range. When Dependabot bumps
the direct pin, Yarn can keep the old version for `custom-card-helpers`, and the two `Connection`
types then fail the type check because `Auth` has a private field. `yarn lint:dedupe` reports that
cause directly; `yarn dedupe home-assistant-js-websocket` fixes it. The check is limited to this
one package because other duplicates in the lockfile are harmless and would fail every Dependabot
pull request.

A Dependabot update of a package that ends up in the bundle — Lit, `custom-card-helpers`, or a build
plugin that changes its output — fails the bundle comparison until someone runs `yarn build` on its
branch and commits the result. Such a commit is `fix(card): …`, so the new bundle reaches users with
the next release.

## Development Environment

| Tool           | Minimum version | Notes                                     |
| -------------- | --------------- | ----------------------------------------- |
| Home Assistant | 2026.8          | The integration's floor, from `hacs.json` |
| Node.js        | 24              | Required by `custom-card-helpers@2`       |
| Yarn           | 4               | Managed via Corepack                      |

```bash
cd frontend
corepack enable
yarn install
yarn check
```

To try a change in the development instance, run `yarn build` and restart Home Assistant
(`script/develop`). The integration reads the bundle's hash once at startup and puts it in the URL,
so a rebuilt bundle reaches the browser only after a restart.

## Commits and Releases

Commits follow the repository's rules in [`AGENTS.md`](../../AGENTS.md); `card` is the scope for a
change under `frontend/`. A user-facing card change is `feat(card): …` or `fix(card): …`, and it
reaches users with the next integration release like any other change — see
[`RELEASE.md`](RELEASE.md).

## Localization

The card ships German and English, the same two the MOS integration ships, and the German follows
the integration's own wording so the two read alike: Docker-Container, Compose-Stacks,
LXC-Container, VMs, Festplatten, Speicherpools, USV, MOS-Server, and the du-form throughout.

A key missing from one file falls back to English rather than showing a raw key, which makes a
partial translation safe but easy to miss — add new keys to both files.

To add a third language:

1. Copy `frontend/src/localize/languages/en.json` to `frontend/src/localize/languages/<lang>.json`.
2. Translate the values, keeping all keys identical.
3. Import and register the new translations in `frontend/src/localize/localize.ts`.
