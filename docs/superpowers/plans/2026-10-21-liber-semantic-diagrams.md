# Liber Semantic Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate 0–3 Mermaid semantic diagrams with each Liber report, show them only in the Artifact rail (browser-like strip + fullscreen), allow PNG download — never inject into PDF/DOCX.

**Architecture:** Same LLM JSON call gains `diagrams[]`. Parse/validate in `parse_output.py`, persist in `figures.json`, expose on run result. Liber renders Mermaid client-side; PNG via SVG→canvas. Document tabs (Preview|PDF|Source) stay unchanged; a second Diagram strip switches `railSurface`.

**Tech Stack:** Python (FastAPI pipeline), Mermaid.js in Vite React, Framer Motion (existing rail), soft-premium CSS tokens.

**Spec:** [`docs/superpowers/specs/2026-10-21-liber-semantic-diagrams-design.md`](../specs/2026-10-21-liber-semantic-diagrams-design.md)

## Global Constraints

- Diagrams are **UI-only**; no TeX slots, no inject, no PDF/DOCX pages.
- Soft-fail: bad Mermaid drops that diagram; pipeline still `ok`.
- Cap default **2**, Settings **0–3**; env `CASE3_MAX_DIAGRAMS`.
- Type whitelist: `flowchart` | `sequence` | `mindmap` | `timeline` | `stateDiagram`.
- No purple neon Mermaid theme; match Liber soft-premium tokens.
- Do not put diagram chrome in left Sidebar (New/History/Settings only).
- IDs unique across figures + charts + diagrams.

## File map

| Path | Responsibility |
|------|----------------|
| `prompt/system_tex.md` | `diagrams[]` schema + when-to-emit |
| `src/case3/parse_output.py` | parse/validate diagrams |
| `src/case3/diagrams.py` | NEW: sanitize helpers, whitelist, fence strip |
| `src/case3/generate.py` | write `diagrams` into figures.json |
| `src/case3/pipeline.py` | meta `diagrams_planned` / counts (no render stage) |
| `src/case3/api.py` | run body `max_diagrams`; payload `diagrams` |
| `web/src/App.tsx` | RunResult.diagrams; railSurface; openDiagram |
| `web/src/ArtifactRail.tsx` | DiagramStrip + DiagramPane host |
| `web/src/DiagramStrip.tsx` | NEW: chip tabs |
| `web/src/DiagramPane.tsx` | NEW: toolbar + MermaidView |
| `web/src/MermaidView.tsx` | NEW: mermaid.render → SVG |
| `web/src/DiagramFullscreen.tsx` | NEW: portal overlay |
| `web/src/downloadDiagramPng.ts` | NEW: SVG→PNG helper |
| `web/src/ArtifactCard.tsx` | optional «Схема» chips |
| `web/src/SettingsModal.tsx` | max diagrams 0–3 |
| `web/src/styles.css` | strip / pane / fullscreen |
| `web/package.json` | add `mermaid` dependency |
| `tests/…` | parse_output / diagrams unit tests |
| `.agents/knowledge/KI-*.md` | update after ship |
| `docs/adr/0003-…` or `0007-…` | short decision note |

---

### Task 1: Backend sanitize + parse

**Files:**
- Create: `src/case3/diagrams.py`
- Create: `tests/test_diagrams.py` (or under existing test layout)
- Modify: `src/case3/parse_output.py`

- [ ] **Step 1: Write failing tests** for fence strip, type whitelist, size cap, empty mermaid drop, id pattern.

```python
# examples — adjust to project pytest style
assert sanitize_mermaid("```mermaid\nflowchart TD\nA-->B\n```").startswith("flowchart")
assert parse_diagrams([{"id": "dia_01", "title": "X", "type": "flowchart", "mermaid": "flowchart TD\nA-->B"}], max_diagrams=2)
assert parse_diagrams([{"id": "x", "type": "pie", "mermaid": "pie ..."}], max_diagrams=2) == []
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `diagrams.py`**
  - `DIAGRAM_TYPES = frozenset({...})`
  - `sanitize_mermaid(text) -> str`
  - `parse_diagrams(raw, *, max_diagrams) -> list[dict]`
  - Max body 6000 chars; title ≤80

- [ ] **Step 4: Wire into `parse_model_output` / JSON load**
  - Read `data["diagrams"]`
  - Merge salvage if you already salvage charts/figures (keep pattern)
  - Id collision check vs figures+charts
  - Return `diagrams` alongside figures/charts

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Commit** `feat(diagrams): parse and sanitize Mermaid JSON`

---

### Task 2: Prompt + generate persist + pipeline meta + API

**Files:**
- Modify: `prompt/system_tex.md`
- Modify: `src/case3/generate.py`
- Modify: `src/case3/pipeline.py`
- Modify: `src/case3/api.py`
- Modify: any RunRequest / FormData schema for `max_diagrams`

- [ ] **Step 1: Extend `system_tex.md`**
  - JSON schema adds `"diagrams": [ { id, title, type, mermaid } ]`
  - `{{MAX_DIAGRAMS}}`; if 0 → `"diagrams": []`
  - Section «When to add diagrams» (structural vs numeric)
  - Explicit: **no TeX slots for diagrams**; UI-only
  - IDs prefer `dia_NN`; unique across all media

- [ ] **Step 2: `generate_document` / figures.json**
  - Persist `"diagrams": [...]` in the same JSON file charts use
  - Dry-run: `diagrams: []`

- [ ] **Step 3: `pipeline.py`**
  - Accept `max_diagrams`
  - Meta: `diagrams_planned`, `diagrams_ok` (= len after parse)
  - **Do not** add a Playwright/inject stage

- [ ] **Step 4: `api.py`**
  - Accept `max_diagrams` (Form field, clamp 0–3)
  - `_run_result_payload`: include full `diagrams` list (`id`, `title`, `type`, `mermaid`)
  - Settings default from env `CASE3_MAX_DIAGRAMS` (default 2)

- [ ] **Step 5: Unit/smoke** — parse fixture with diagrams; payload keys present; TeX has no `%CASE3_DIAG`

- [ ] **Step 6: Commit** `feat(diagrams): prompt, persist, API payload (UI-only)`

---

### Task 3: Liber Mermaid render + PNG download

**Files:**
- Modify: `web/package.json` (+ lockfile)
- Create: `web/src/MermaidView.tsx`
- Create: `web/src/downloadDiagramPng.ts`
- Create: `web/src/DiagramPane.tsx`
- Create: `web/src/DiagramFullscreen.tsx`
- Modify: `web/src/styles.css`

- [ ] **Step 1: `npm install mermaid` in `web/`** (pin a recent 11.x if repo uses modern Vite)

- [ ] **Step 2: `MermaidView`**
  - `useEffect` → `mermaid.initialize({ startOnLoad: false, theme: "base", themeVariables: {…liber tokens} })`
  - `mermaid.render(id, source)` → set SVG HTML
  - Error boundary / fallback message

- [ ] **Step 3: `downloadDiagramPng(svgEl, filename)`**
  - Serialize SVG, draw on canvas @2x, trigger `<a download>`

- [ ] **Step 4: `DiagramPane` + `DiagramFullscreen`**
  - Toolbar: Fullscreen, Download PNG
  - Fullscreen: `createPortal` + Esc / × (mirror report lightbox)

- [ ] **Step 5: Manual smoke** with hardcoded mermaid string in a tiny QA route or Story — SVG paints; PNG downloads

- [ ] **Step 6: Commit** `feat(ui): Mermaid view, fullscreen, PNG download`

---

### Task 4: Artifact rail strip + App wiring + Settings + chat chips

**Files:**
- Create: `web/src/DiagramStrip.tsx`
- Modify: `web/src/ArtifactRail.tsx`
- Modify: `web/src/App.tsx`
- Modify: `web/src/ArtifactCard.tsx`
- Modify: `web/src/SettingsModal.tsx`
- Modify: `web/src/reportHistory.ts` (persist diagrams on RunResult)
- Modify: `web/src/styles.css`

- [ ] **Step 1: Extend types**
  - `RunResult.diagrams?: { id; title; type; mermaid }[]`
  - `ActiveArtifact` report kind: `railSurface?: "document" | "diagram"`; `activeDiagramId?: string | null`

- [ ] **Step 2: `DiagramStrip`**
  - Horizontal chips; active ink; click → `onSelect(id)`
  - Only render if `diagrams.length > 0`

- [ ] **Step 3: `ArtifactRail`**
  - Below document tabs: DiagramStrip
  - If `railSurface === "diagram"` → DiagramPane instead of Preview/PDF/Source body
  - Document tab click → `railSurface: "document"`

- [ ] **Step 4: `App.tsx`**
  - `openDiagram(msgId, diagramId)`
  - Pass `max_diagrams` in FormData from settings
  - Wire chips from ArtifactCard

- [ ] **Step 5: Settings** — «Схемы» 0–3 next to charts/images

- [ ] **Step 6: `npm run build` + manual: run with process-like Source → strip appears; fullscreen; PNG; PDF unchanged

- [ ] **Step 7: Commit** `feat(ui): diagram strip in Artifact rail + settings`

---

### Task 5: Docs + verification

**Files:**
- Modify: `.agents/knowledge/KI-liber-ui.md`
- Modify: `.agents/knowledge/KI-pipeline.md`
- Modify or create: `docs/adr/0007-liber-ui-only-diagrams.md` (or amend 0003)
- Modify: `docs/adr/README.md` if new ADR
- Spec status → approved

- [ ] **Step 1: Update KI** — entry points, invariant «diagrams UI-only / PNG client»
- [ ] **Step 2: Short ADR** — why UI-only; Mermaid not Chart.js; soft-fail
- [ ] **Step 3: Run** `verification-before-completion`: pytest diagrams + `npm run build`; one real or dry pipeline check that PDF path ignores diagrams
- [ ] **Step 4: Commit** `docs: KI + ADR for semantic diagrams`

---

## Out of scope (park)

- Server-side Mermaid→PNG for email
- Diagram edit Apply
- Embedding diagram thumbnail in chat bubble (chips only)
- Multi-document browser stack beyond diagram strip
- PPTX / HTML deck Mermaid (still parked)

## Success criteria

1. Process-heavy Source with `max_diagrams≥1` → ≥1 valid diagram in Liber rail.  
2. PDF/DOCX byte path identical in behavior (no new inject).  
3. Fullscreen + Download PNG work; Esc closes overlay.  
4. `max_diagrams=0` → no strip, empty array.  
5. Invalid Mermaid → warning, report still succeeds.
