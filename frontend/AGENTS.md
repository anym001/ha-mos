# AI Agent Instructions — MOS NAS Card

This document provides guidance for AI coding agents working in `frontend/`, the Lovelace card the
MOS NAS integration ships. The codebase is TypeScript + Lit and builds with Rollup.

It adds to the repository's [`AGENTS.md`](../AGENTS.md), which still applies — above all its commit
rules. They are agent-independent: anything tool-specific belongs in that tool's own file, not here.

## Quick reference

### Core commands

Run in `frontend/`:

```bash
npm ci                # dependencies; pre-commit hooks come from the repository root
npm run check         # everything below except `start`, in one command
npm start
npm run build
npm run lint          # ESLint, over src and tests
npm run typecheck     # tsc --noEmit
npm test              # Vitest, once
npm run test:watch    # Vitest, watching
npm run lint:format   # prettier --check
```

### Primary files

- `src/mos-card.ts` — main card implementation
- `src/devices.ts` — device registry subscription, `model_id` filtering, per-kind facts
- `src/editor.ts` — visual editor (`LovelaceCardEditor`)
- `src/types.ts` — card config and type definitions
- `src/config.ts` — defaults, validation and the editor's filter conversions, shared by both
- `src/rows.ts` — tone, ordering, row capping and the pending power buttons
- `src/action-handler-directive.ts` — tap/hold/double-tap directive
- `src/localize/localize.ts` — localization helper
- `src/localize/languages/de.json` and `src/localize/languages/en.json` — translation files
- `tests/` — Vitest suites over the pure logic in `src/devices.ts`, with `tests/fixtures.ts`
  holding registry entries shaped like the ones a live instance sends
- `rollup.config.js` and `rollup.config.dev.js` — production and dev build config
- `../custom_components/mos/www/mos-card.js` — the built bundle, committed
- [`../docs/development/CARD.md`](../docs/development/CARD.md) — this card's technical
  documentation; [`README.md`](README.md) is for users

## The `model_id` contract (read this before touching device selection)

The card discovers what to render from the Home Assistant **device registry**, not from a
hand-maintained entity list. The integration writes a `model_id` onto every container device it
creates, and that field is the only supported anchor:

- Valid values: `docker_container`, `compose_stack`, `lxc_container`, `virtual_machine`, `disk`,
  `storage_pool`, `ups`.
- The MOS **server** device deliberately carries no `model_id`. Container devices hang off it via
  `via_device_id`, which is how the card scopes a dashboard to one server.
- **Never** match on device `identifiers` (an internal format the integration reserves the right to
  change) or on display names (the user's to rename).

This is a released, public contract. It is documented on the integration side in
[`docs/development/ARCHITECTURE.md`](../docs/development/ARCHITECTURE.md) ("Base Entity") and in the
decision log entry _Container Devices Carry Their Kind in `model_id`_ in
[`docs/development/DECISIONS.md`](../docs/development/DECISIONS.md); the card side is in
[`docs/development/CARD.md`](../docs/development/CARD.md). Changing how the card matches means
re-reading them first — and a change on either side lands in the same pull request.

Because the integration adds and removes these devices at runtime
(`async_setup_dynamic_entities`), a card that follows the registry gets lifecycle for free:
removed containers disappear, new ones show up, and a container behind a failing endpoint stays
listed and merely reports unavailable. Do not add manual refresh logic that fights this.

## Architecture and patterns

- The custom element is `custom:mos-card`.
- Prefer Lit 3 patterns and idiomatic web component structure.
- Keep configuration shape centralized in `src/types.ts`.
- Keep editor schema and defaults aligned with runtime card behavior.
- Keep feature logic in small, readable helpers instead of long monolithic methods.
- Registry subscriptions belong in `connectedCallback` and must be torn down in
  `disconnectedCallback` — a card element is created and destroyed on every dashboard edit.

## TypeScript standards

- Use strict, explicit typing; avoid `any` unless there is no practical alternative.
- Use `import type` for type-only imports where appropriate.
- Validate and narrow optional config fields before use.
- Keep public API names stable unless explicitly requested to change them.

## Lit and component guidance

- Use `@property` for public reactive inputs and `@state` for internal state.
- Avoid direct DOM mutation when Lit reactivity can handle updates.
- Preserve existing card/editor lifecycle behavior.
- For card config, validate early in `setConfig` and throw actionable errors.
- Keep `getCardSize` deterministic and aligned with rendered density.

## Home Assistant integration

- Use Home Assistant helpers and conventions from `custom-card-helpers`.
- Ensure tap, hold, and double-tap actions are wired through existing action patterns.
- Support unavailable/loading/error states gracefully — an unreachable MOS endpoint is a normal
  state, not an error state.
- Keep Lovelace config compatibility in mind when changing schema or defaults.

## Localization and copy

- Do not hardcode user-facing strings when a localize key should be used.
- Add new translation keys to both language files (`de.json`, `en.json`) — a key present in one
  and missing in the other silently falls back to English.
- German follows the MOS integration's own wording, so the card and the integration read the
  same way: Docker-Container, LXC-Container, VMs, Festplatten, Speicherpools, USV, MOS-Server,
  and the du-form throughout.
- Keep copy concise, sentence case, and user-facing.
- Favor consistent terminology across card UI and editor labels.

## Styling and UX

- Respect Home Assistant theme variables and CSS custom properties.
- Avoid hardcoded colors when theme tokens can be used.
- Keep spacing and typography consistent with existing card styles.
- Ensure layouts work in both compact and wider dashboard widths.

## Build and quality expectations

- Keep `npm run lint` clean for changed code.
- Run `npm run check` before handing work back — it is the local equivalent of the CI gates.
- Do not read a green build as a green type check.
  `@rollup/plugin-typescript` reports type errors as warnings and still emits a bundle, so
  `npm run build` exits 0 on code that does not type-check. `npm run typecheck` is the only command
  that fails on one.
- Cover new pure logic with a test. Logic that does not need a DOM, a `hass` or a render belongs in
  `src/devices.ts`, `src/config.ts` or `src/rows.ts` rather than on the component, where it could
  only be checked by driving a live card. Component tests are deliberately absent: they would need
  a DOM shim and would mostly assert that Lit works.
- Defaults live once, in `CARD_DEFAULTS`. The card and the editor both read it, so a switch cannot
  show off while the card behaves as on — and `TOGGLES` sits beside it so a new boolean without a
  switch fails a test rather than shipping.
- Check a new test by breaking the code it covers and confirming it fails. Two tests in this
  repository passed against deliberately broken code before this was done: one because the fixture
  order let a fallback stand in for the branch under test, one because the expected value was read
  after the mutation and compared with itself.
- Write fixtures that match what Home Assistant actually sends, and check the shape of a test
  before trusting it. `findStateEntity` ends in a "first sensor on the device" last resort, so a
  fixture in registry order lets a test pass with the `unique_id` step deleted — the suite reverses
  the order on purpose to close that hole.
- Do not introduce unrelated refactors in focused changes.
- If updating build tooling, keep dev and prod Rollup configs consistent.
- The build stays on **Rollup**. Vite's hot reload buys nothing here: Home Assistant loads the
  built bundle from a resource URL, not from a dev server.

## Commits and the bundle

- Commit rules are the repository's, in [`AGENTS.md`](../AGENTS.md). The scope for a change here is
  `card`; a user-facing change is `feat(card): …` or `fix(card): …` and ships with the next
  integration release.
- A change under `src/` comes with the rebuilt `../custom_components/mos/www/mos-card.js` in the
  same commit: run `npm run build` and stage both. The `Card` workflow fails when the committed bundle
  is not what the source builds to.
- The card has no version of its own; do not add one.

## Safe change workflow

1. Read adjacent code before editing.
2. Implement the smallest viable change.
3. Run `npm run check` (or a targeted command while iterating) and stage the rebuilt bundle.
4. Update docs/README when behavior or config changes.
5. Summarize what changed and why.

## Pull request guidance

- Keep PRs focused to one logical change.
- Include screenshots or short clips for visible UI/editor changes.
- Document config changes and migration notes when applicable.
- Call out any follow-up work explicitly instead of bundling extra scope.

## Avoid these common issues

- Matching devices on `identifiers` or display names instead of `model_id`
- Breaking editor/card config parity
- Adding untyped dynamic config access
- Hardcoding text instead of localization keys
- Overriding theme behavior with fixed styles
- Changing output filenames or card tag without explicit request
- Committing a source change without the rebuilt bundle
