# Liber frontend modules — Design

**Date:** 2026-10-25  
**Status:** approved · **Week 1 landed** (`api/` `domain/` `app/` + shims + `web/ARCHITECTURE.md`)  
**ADR:** (optional follow-up) link when module layout lands  
**Related:** ADR-0003 · ADR-0006 · KI-liber-ui · KI-liber-deck

## Goal

Make Liber `web/` readable to someone who did not write it, safe to refactor for ~1 month of React work, and easy to map onto an **Angular rewrite** afterward.

Not a visual redesign. Not a state-library rewrite. Structure + boundaries.

## Constraints

- Keep shipping features on React for ~1 month; no freeze.
- Avoid React-only frameworks that throw away badly (no Redux/Zustand “for everything”, no heavy Context tree).
- CSS Quiet Mono split (`styles/tokens|shell|chat|…`) stays; do not reshuffle tokens for structure.
- Strangler: new code lands in target folders; old files move when touched (or in dedicated small PRs).

## Non-goals

- Micro-frontends / Nx / monorepo tooling.
- Pixel-perfect Angular preview in this phase.
- Changing Liber UX modes or API contracts.

## Target tree

```text
web/src/
  app/                 # composition root: App shell, layout, wiring hooks
  api/                 # HTTP + SSE + poll helpers — no JSX
  domain/              # types, modes, phrases, history, rail width — no JSX
  features/
    chat/              # composer, messages, thinking, in-chat cards glue
    rail/              # ArtifactRail shell + tab chrome
    report/            # ReportView, live charts, table/chart/image edit sheets
    diagram/           # Mermaid pane, visual editor, legend, PNG download
    deck/              # style sheet, templates, canvas, presentation pane
    settings/          # Sidebar history chrome + SettingsModal
  shared/              # icons, focus trap, lightMd, tiny presentational bits
  styles/              # existing CSS files (unchanged meaning)
```

Each `features/<name>/` exposes a small public surface via `index.ts`.  
Cross-feature imports are forbidden; only `app/` (and `shared/`) may compose features.

## Layer rules

| Layer | May contain | Must not |
|-------|-------------|----------|
| `api/` | `fetch`, `EventSource`, FormData builders, status/slides poll loops as pure async | React, CSS, DOM UI |
| `domain/` | types, `liberModes`, phrases, history storage keys, pure formatters | React, network I/O (prefer `api/`) |
| `features/*` | components + feature-local hooks | import another feature |
| `app/` | state ownership, `send`/`edit*` wiring, layout | chart/deck business details |
| `shared/` | dumb UI / utils used by ≥2 features | feature-specific run logic |

**App size target:** orchestration under ~400–600 lines (logic in `app/useLiberRun.ts` or equivalent), not a 2k-line god file.

## Mapping today → tomorrow

| Current (flat) | Target |
|----------------|--------|
| `App.tsx` | `app/App.tsx` + run/edit hooks |
| `liberRunHelpers.ts`, poll/SSE bits | `api/` + thin `domain/` formatters |
| `liberTypes.ts`, `liberModes.ts`, `liberConstants.ts`, `pipelinePhrases.ts`, `reportHistory.ts`, `railWidth.ts` | `domain/` |
| `ChatMessages`, `ChatComposer`, `ThinkingFold`, `ArtifactCard` (chat face) | `features/chat/` |
| `ArtifactRail`, `SourcePane`, rail width UI | `features/rail/` |
| `ReportView`, `LiveChart`, `Chart*`, `TableEditSheet`, `ImageEditModal` | `features/report/` |
| `Diagram*`, `MermaidView`, `diagramIr.ts`, … | `features/diagram/` |
| `Deck*`, `Presentation*`, `deckStyle.ts`, `deckTypes.ts`, … | `features/deck/` |
| `Sidebar`, `SettingsModal` | `features/settings/` |
| `icons.tsx`, `useFocusTrap.ts`, `lightMd.tsx` | `shared/` |

Exact file lists may adjust; **folder ownership** is the contract.

## Angular handoff (intent)

| React | Angular later |
|-------|----------------|
| `api/` | injectable services |
| `domain/` | models / pure TS (often shared) |
| `features/X` | feature module / standalone routes or components |
| `app/` | `AppComponent` + facade services |

Document the desk flows once in `web/ARCHITECTURE.md` (one screen): modes → `POST /api/run` → poll → SSE summary → rail tabs → edit endpoints → slides job. That file is the onboarding + port checklist.

## Migration order (strangler, ~4 weeks)

1. **Week 1 — foundations:** create `api/`, `domain/`, `app/` scaffolding; move pure helpers; add `web/ARCHITECTURE.md`. Behavior unchanged.
2. **Week 2 — isolated products:** `features/deck`, `features/diagram` (largest, least entangled with report TeX).
3. **Week 3 — report surface:** `features/report`, `features/rail`.
4. **Week 4 — chat shell:** `features/chat`, `features/settings`; shrink `app/` to wiring only.

Rule: if a PR touches a flat file that belongs to a feature, prefer moving it in the same PR when cost is low; otherwise leave a `// TODO(liber-modules): → features/…` only when move is blocked.

## PR / risk policy

- Prefer vertical slices (one feature folder per PR) over “move everything”.
- No `--force` / broad renames without `tsc -b` + smoke Liber paths (report send, diagram, deck).
- Keep Vite entry `main.tsx` importing styles as today until a deliberate CSS entry cleanup.

## Success criteria

1. Newcomer finds send → poll → rail → edit from `ARCHITECTURE.md` in ≤30 minutes.
2. `api/` + `domain/` have zero React imports.
3. No `features/A` → `features/B` imports (lint or documented exception list empty by default).
4. `App` orchestration measurably thinner; feature work does not require editing unrelated folders.
5. Team can sketch Angular modules by copying folder names 1:1.

## Out of scope (later)

- ESLint `no-restricted-imports` enforcement (nice follow-up once folders exist).
- Formal ADR if layout becomes permanent before Angular (optional ADR-0009).
- Automated e2e; helper unit tests stay in place and move with files.

## Open questions

None blocking. Optional: whether `PresentationPane` lives under `deck/` only (yes, default) vs shared with `rail/` tab host (rail hosts; pane owns UI).
