# Liber frontend modules — Week 1 Implementation Plan

> **For agentic workers:** COMPLETE ALL TASKS. Foundations only — no feature folder moves.

**Goal:** `api/` + `domain/` + `app/` scaffolding, pure helpers relocated, `web/ARCHITECTURE.md`, behavior unchanged via re-export shims.

**Status:** done (2026-10-25) — `npm run test:helpers` 27/27 · `tsc --noEmit` ok · `npm run build` ok.

**Spec:** `docs/superpowers/specs/2026-10-25-liber-frontend-modules-design.md`

**Tech:** Vite/React; verify with `npm run test:helpers` + `npx tsc -b` / `npm run build`.

## Tasks

### Task 1: Move domain modules + shims

Move into `web/src/domain/` (fix internal imports):
- `liberTypes.ts`, `liberModes.ts`, `liberConstants.ts`, `pipelinePhrases.ts`, `reportHistory.ts`, `railWidth.ts`
- run helpers except SSE → `domain/runHelpers.ts`

Leave root shims: `export * from "./domain/…"`.

### Task 2: Create `api/summaryStream.ts`

Move `openSummaryStream` from helpers. Shim from `liberRunHelpers`.

### Task 3: Move App to `app/App.tsx`

`main.tsx` imports `./app/App`. Root `App.tsx` re-exports.

### Task 4: Docs

`web/ARCHITECTURE.md` — one-screen desk map. Point MEMORY/KI if needed.

### Task 5: Verify

```bash
cd web && npm run test:helpers && npx tsc --noEmit -p tsconfig.json && npm run build
```

No UX/API behavior change.
