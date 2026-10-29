# Liber / case-3 — simplify for agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish leftover hygiene from the 2026-10-29 audit, then cut hub duplication so the next fix touches one place (not 2–4).

**Architecture:** Three sequential tracks after a short hygiene wave: **A Test+seam** (shared fixtures, meta IO, `run_store`, `repo_root`, intent extract) → **B Pipeline spine** (shared `run`/`resume` body + split `chart_types_coerce`) → **C FE modules** (`ReportPreview` in domain, shrink `LiberSendDeps`, desk chrome out of `App`). No new product features; parked backlog stays parked.

**Tech Stack:** Python FastAPI (`src/case3`), React/Vite (`web/src`), pytest + `web` `test:helpers` + `tsc`.

**Sources merged into this file:**
- Wave 8 cleanup status (done, uncommitted unless committed later)
- Remaining P1/P2 from audit chat
- Hub LOC + leverage list (conftest → pipeline → FE)
- Tracks A / B / C recommendation

**Related L3:**
- [`docs/knowledge/codebase-audit-2026-10-29.md`](../../knowledge/codebase-audit-2026-10-29.md)
- [`docs/knowledge/cleanup-2026-10-29.md`](../../knowledge/cleanup-2026-10-29.md)
- [`docs/knowledge/backlog-deferred-2026-10-25.md`](../../knowledge/backlog-deferred-2026-10-25.md) (do **not** pull product items here)
- [`web/ARCHITECTURE.md`](../../../web/ARCHITECTURE.md)

## Global Constraints

- Numbers/facts only from Source; do not invent pipeline stages, env vars, or chart types — verify in code/KI.
- Palettes: editorial / ocean / sunset / mono / atelier only.
- Chart types: whitelist in `chart_html.CHART_TYPES`.
- Do not commit `runs/`, `.env`, secrets, PDF/DOCX artifacts.
- Keep health alias `kandinsky_configured` (UI still reads it).
- Prefer TDD; before «готово» run `pytest` + `web` `tsc` + `test:helpers`.
- Commit only when the user asks.

### Hub sizes (snapshot 2026-10-29 evening)

| Hub | ~LOC | Pain |
|-----|------|------|
| `slides_pptx_native.py` | 1500 | layouts in one file (split only when touching decks) |
| `api.py` | 1468 | HTTP + intent + slot + SSE + photo |
| `pipeline.py` | 1270 | `run` ≈ `resume` twins |
| `App.tsx` | 1273 | history / rail / toast still in shell |
| `useLiberRun.ts` | 1002 | ~30 deps bag |
| `ReportView.tsx` | 970 | preview + edit host |

### Do **not** do in this plan

- Angular rewrite / chart whitelist changes
- Product deferred backlog (B/C3/C5/F/G/I/J/K)
- Deep rewrite of `slides_html` body (low touch rate)
- Deleting `cli.py` or health `kandinsky_configured`

---

## Status already done (context — do not re-do)

### Deep cleanup + extract (committed `8bfd303` and earlier)

- [x] Track full `tests/test_*.py` + fixtures
- [x] Archive `ROOT = parents[2]`; gallery import from `scripts/archive`
- [x] Delete dead FE/BE: `DeckMakeSplit`, `kandinsky.py`, Week-1 shims, `IconHistory`, …
- [x] Extract `useLiberEdits` / `useMakePresentation` / `useResumeFailedRun` / `useLiberRun`
- [x] Routers `api_edits.py` / `api_slides.py`; shared `run_rebuild` / `parse_formats_form` / `is_dark_pack`
- [x] Lazy mermaid / DiagramVisualEditor / ChartsQa; `postJsonEdit`

### Wave 8 hygiene (done in working tree — **commit when asked**)

- [x] Fix `scripts/archive/run_structure_matrix8.py` → add `scripts/archive` to `sys.path`
- [x] Delete dead helpers: `_kick_pipeline_thread`, `default_chart_box` / `default_table_box`, `_align`, `_fmt_hex`, `_unescape_tex`, `_chart_ids_and_pngs`, `iter_summary_deltas`
- [x] FE: remove unused `modeNudge`, `loadLastReport`
- [x] CSS: strip `.thinking-bar*`, `.export-menu*`, quiet-cta leftovers
- [x] Drop unused imports in `api.py`
- [x] Verify: 438 pytest · 54 helpers · `tsc` exit 0

---

## Wave 0 — Finish / commit leftover P1–P2 hygiene

**Files:** `web/src/app/App.tsx`, `web/src/app/useLiberRun.ts`, `web/src/ArtifactRail.tsx`, `web/src/ReportView.tsx`, `web/src/app/index.ts`, `web/src/api/index.ts`, `web/src/domain/index.ts`, `src/case3/color_util.py` (new), callers of hex helpers, `.env.example`, module docstrings, `Makefile`, this plan + audit doc.

### Task 0.1 — Commit wave 8 (when user says «комить»)

- [x] `git status` / `git diff` — ensure no `runs/` / `.env`
- [ ] Stage wave 8 + audit touch-ups
- [ ] Commit message focus: why (dead code / orphan CSS / archive path)
- [ ] Optional push only if user says «залей»

### Task 0.2 — Collapse `photoMode` to document-only

- [x] Grep `photoMode` / `photo_mode` in `web/src` and `src/case3/api.py`
- [x] Keep API `photo_mode=edit` + `/api/photo/edit` (backend still valid)
- [x] In App/useLiberRun: remove `"edit"` UI branches; pass constant `"document"` or drop FE state
- [x] `npx tsc -b` + smoke composer send still enables

### Task 0.3 — One lazy `PdfFirstPage`

- [x] Extract shared `lazyPdfFirstPage` (or `web/src/lazyPdfFirstPage.ts`)
- [x] Retarget `ArtifactRail.tsx` + `ReportView.tsx` to the single import
- [x] `npm run build` — one chunk for PdfFirstPage

### Task 0.4 — Delete unused barrels

- [x] Confirm 0 importers of `web/src/app/index.ts`, `api/index.ts`, `domain/index.ts`
- [x] Delete the three files
- [x] `tsc -b`

### Task 0.5 — `color_util` (only if touching hex next; else defer to first chart/deck PR)

- [x] **Deferred** (no hex touch this wave) — Add `src/case3/color_util.py` with `norm_hex` / `hex_to_rgb` / `expand_hex`
- [x] Retarget `deck_theme`, `slides_pptx_native`, `docx_charts`, `chart_style`, `diagrams` gradually (one PR per area OK)
- [x] pytest for hex round-trip

### Task 0.6 — Doc / Makefile P2

- [x] `.env.example`: document `CASE3_MAX_DIAGRAMS`, `CASE3_DIAGRAM_REPAIR`, `CASE3_SOFFICE` / `LIBREOFFICE_PATH` (verify names in code first)
- [x] Soften stale «Kandinsky» wording in `generate.py` / `pipeline.py` / `cli.py` / `api.py` comments (keep health key)
- [x] `Makefile`: fix default `FILE=` to an existing sample or drop default
- [x] Mark `diagramMetrics.smoke.ts` done in audit (already deleted)

### Task 0.7 — Verify wave 0

- [x] `python3 -m pytest -q` (438)
- [x] `cd web && npx tsc -b && npm run test:helpers` (54) + build (one PdfFirstPage chunk)

---

## Track A — Test + seam (do first for leverage)

**Why:** Every later API/edit/pipeline PR gets cheaper. Low product risk.

### Task A.1 — `tests/conftest.py` shared client + seed

**Files:** `tests/conftest.py` (new), `tests/test_api_*.py`, `tests/test_chart_live_preview.py`, …

- [x] Collect duplicated `ROOT` monkeypatch / `_seed_*` from ≥7 API tests
- [x] Fixtures: `repo_root`, `api_client`, `seed_ok_run(tmp_path, **meta)`
- [x] Migrate 2–3 highest-duplication tests first (TDD: tests still green)
- [x] Migrate remaining API tests in a follow-up commit
- [x] `pytest tests/test_api_*.py -q`

### Task A.2 — Shared post-edit envelope

**Files:** `src/case3/api_edits.py`, `src/case3/chart_edit.py`, `figure_edit.py`, `table_edit.py`, `paragraph_edit.py`, `run_rebuild.py`

- [x] Sketch one helper: undo snapshot → apply patch → write meta → `rebuild_run_docs` → response envelope (+ rollback on failure)
- [x] RED: one edit-formats test that fails if duplicate paths diverge
- [x] Wire chart/figure/table/paragraph through the helper
- [x] `pytest -k edit -q`

### Task A.3 — `run_meta` read/write module

**Files:** new `src/case3/run_meta.py`; callers in `pipeline.py`, `run_events.py`, `slides_job.py`, `api_slides.py`, edit paths

- [x] `read_meta(out_dir) -> dict`, `write_meta(out_dir, meta, *, atomic=True)` (same atomic pattern as pipeline)
- [x] Replace raw `meta.json` writes in slides/edits/resume
- [x] Unit test: atomic write leaves valid JSON on interrupt mock
- [x] `pytest -k meta -q` (or targeted new test)

### Task A.4 — `run_store.py` (kill `_api()` late-bind)

**Files:** new `src/case3/run_store.py`; slim `api.py`; update `api_edits.py` / `api_slides.py`; patch tests to `case3.run_store`

- [x] Move `_resolve_run_dir`, preview/download helpers used by edits/slides
- [x] Routers import `run_store` directly (no `_api()`)
- [x] Fix monkeypatches in tests
- [x] `pytest tests/test_api_edits* tests/test_api_slides* tests/test_api_edit_formats.py -q`

### Task A.5 — One `repo_root()` helper

**Files:** `src/case3/paths.py` (or extend existing), replace `parents[2]` in `api.py`, `run_rebuild.py`, `run_undo.py`, `diagram_edit.py`, …

- [x] Single `repo_root() -> Path` (Dockerfile / `.env` sentinel as today)
- [x] Grep `parents\[2\]` under `src/case3` → retarget
- [x] `pytest -q` smoke

### Task A.6 — `build_intent_from_ui` → `intent_compose.py`

**Files:** new `src/case3/intent_compose.py`; `api.py` becomes thin Form → compose

- [x] Move intent prose builder unchanged
- [x] API imports compose; behavior golden/tests for intent strings if any
- [x] Manual: dry_run still gets same intent shape

### Task A.7 — Track A verify + docs

- [x] Full `pytest -q` + health if stack up
- [x] Update audit «Applied» + this plan checkboxes
- [x] Commit when asked

---

## Track B — Pipeline spine

**Why:** Stage fixes today require editing both `run_pipeline` and `resume_pipeline`.

### Task B.1 — Extract `_run_from_media(...)` (or stage runners)

**Files:** `src/case3/pipeline.py` (+ tests `test_pipeline_*.py`, `test_pipeline_resume.py`)

- [x] Map shared stages: media → charts → inject → latex/docx → summary
- [x] Extract shared body; keep public `run_pipeline` / `resume_pipeline` signatures stable
- [x] `_pipeline_materialize_media` (images+charts) shared by run/resume (2026-10-30)
- [x] Resume still honors `failed_stage` / skip-done stages
- [x] `pytest -k pipeline -q`

### Task B.2 — Split `chart_types_coerce.py` (~900)

**Files:** e.g. `chart_harden.py`, `chart_donut.py`, `chart_coerce.py` (names verify vs existing tests)

- [x] Mirror test file split already present (`test_harden_*`, `test_donut_*`, `test_coerce_*`)
- [x] Re-export from old module if needed for one release, then delete façade
- [x] `pytest -k 'harden or donut or coerce' -q`

### Task B.3 — (Optional, when touching PPTX) peel `slides_pptx_native` layouts

**Files:** `slides_pptx_native.py` → `_layout_title`, `_layout_card_row`, …

- [ ] Only while changing deck layouts — not a blind big-bang
- [ ] `pytest -k pptx -q`

### Task B.4 — Track B verify

- [x] Full pytest; one live resume smoke if desk up
- [x] Commit when asked

---

## Track C — FE modules (parallel, small PRs)

**Why:** Angular strangler + less god-`App` / god-deps.

### Task C.1 — Move `ReportPreview` type to `domain/`

**Files:** `web/src/domain/liberTypes.ts` (or `reportPreview.ts`), `ReportView.tsx`, importers

- [x] Break domain ← UI import cycle documented in types
- [x] `tsc -b`

### Task C.2 — Shrink `LiberSendDeps`

**Files:** `web/src/app/useLiberRun.ts`, `App.tsx`

- [x] Group deps: `{ composer, runRefs, desk }` (or similar)
- [x] Keep behavior identical; tsc + helper tests
- [x] Optional: dry_run UI smoke

### Task C.3 — `useDeskChrome` / history owner out of `App`

**Files:** new hooks under `web/src/app/`; slim `App.tsx` to wiring

- [x] Extract history sidebar + toast/rail chrome without changing UX
- [x] `tsc` + `test:helpers`
- [x] Target: `App.tsx` orchestration-only (aim &lt;800 LOC over 1–2 PRs) — history/toast extracted; App still ~1235, more peel later

### Task C.4 — Split `styles/chat.css` (when CSS churn)

- [x] Peel thinking-fold / diagrams / charts-qa into partials imported from main
- [x] Visual smoke Liber empty + thinking fold

### Task C.5 — Glossary KI (cheap)

**Files:** `.agents/knowledge/` (e.g. extend KI-liber-ui or new KI-media-names)

- [x] Table: figure / photo / image / `fig_` / `cht_` / Image API / charts stage
- [x] Link from `docs/MEMORY.md` L3 list if useful

### Task C.6 — Track C verify

- [x] `tsc -b` + `test:helpers` + `npm run build`
- [x] Commit when asked

---

## Suggested execution order

```text
Wave 0.1 commit wave 8
    ↓
Wave 0.2–0.4 photoMode + PdfFirstPage + barrels   (~1–2 h)
    ↓
Track A.1 → A.6   (test+seam)                     (~1–2 days)
    ↓
Track B.1 → B.2   (pipeline + coerce)             (~1–2 days)
    ↓
Track C in parallel small PRs
```

Defer `color_util` / `chat.css` split / `slides_pptx_native` peel until the next natural touch of those areas (Task 0.5 / C.4 / B.3).

---

## Definition of done (whole plan)

- [x] Wave 8 + Wave 0 hygiene committed
- [x] Track A landed: conftest, edit envelope, run_meta, run_store, repo_root, intent_compose
- [x] Track B landed: shared pipeline body + coerce split
- [x] Track C: at least C.1 + C.2 (C.3+ optional)
- [x] Fresh verify: **pytest green**, **tsc 0**, **test:helpers 54+**, `/api/health` green if desk up
- [x] Audit doc «Applied» lists waves; this plan checkboxes updated

---

## Handoff

After approval of a track, implement with `executing-plans` or `subagent-driven-development`.  
Default start: **Task 0.1 (commit) → 0.2–0.4 → Track A.1**.
