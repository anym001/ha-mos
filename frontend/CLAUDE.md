# Claude Code Instructions — MOS NAS Card

The card's instructions are in [`AGENTS.md`](AGENTS.md); the repository's
[`CLAUDE.md`](../CLAUDE.md) and [`AGENTS.md`](../AGENTS.md) still apply, above all the commit rules.

## Quick Reference

- **Card types:** `custom:mos-card`, `custom:mos-overview-card`
- **Main code:** `src/mos-card.ts`, `src/overview-card.ts`, device selection in `src/devices.ts`
- **Technical docs:** [`../docs/development/CARD.md`](../docs/development/CARD.md)
- **Validate:** `npm run check` in `frontend/` (lint + typecheck + test + lint:format + build)
- **Careful:** a green `npm run build` is not a green type check — run `npm run typecheck`
- **Bundle:** commit the rebuilt `custom_components/mos/www/mos-card.js` with every source change
- **Commit scope:** `card`
- **Never match** devices on `identifiers` or names — only `model_id` (see `AGENTS.md`)
