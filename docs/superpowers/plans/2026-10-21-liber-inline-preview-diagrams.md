# Liber Inline Preview Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Place Mermaid diagrams inline in Liber Preview via `%CASE3_DIAG:id%` TeX markers; strip markers before PDF; size-gate large diagrams into chips that open the Схема rail.

**Architecture:** Reuse FIG/CHART slot contract for position only. `inject` / `strip_orphan_slots` always delete DIAG. `tex_preview` emits `type: "diagram"` blocks; `ReportView` renders compact Mermaid or a chip based on `diagramSize` heuristics. Rail/fullscreen/PNG stay as in ADR-0007.

**Tech Stack:** Python (parse/inject/preview), Vite React + existing MermaidView, pytest; frontend helpers via `npm run test:helpers` (tsx).

**Spec:** [`docs/superpowers/specs/2026-10-21-liber-inline-preview-diagrams-design.md`](../specs/2026-10-21-liber-inline-preview-diagrams-design.md)

**Refactor note (2026-10-21):** Liber desk split — types/helpers live outside `App.tsx`. This plan targets the **post-refactor** layout below. Do **not** re-introduce `DiagramStrip.tsx` (deleted); diagram focus is Artifact tab `"diagram"` + `activeDiagramId`.

## Global Constraints

- PDF/DOCX: **never** inject diagram images; DIAG slots always stripped.
- Soft-fail: bad/orphan DIAG never fails the run.
- Cap / types unchanged: `CASE3_MAX_DIAGRAMS` 0–3; whitelist flowchart|sequence|mindmap|timeline|stateDiagram.
- Inline chrome: Liber soft-green; no purple; subtle «Только в Liber · не в PDF».
- Missing slot → rail-only (no Preview block) is OK.
- Do not invent new env vars.
- ADR-0007 amended, not superseded.
- Keep `liberTypes.ts` / `liberRunHelpers.ts` as the single source for `RunResult` / `DiagramResult`.

## File map (post-refactor)

| Path | Responsibility |
|------|----------------|
| `src/case3/tex_preamble.py` | `strip_orphan_slots` includes `DIAG` |
| `src/case3/inject.py` | Always strip `%CASE3_DIAG:…%` (and figure shell if wrapped) |
| `src/case3/parse_output.py` | Collect/validate DIAG slots vs diagrams[]; strip orphans |
| `src/case3/tex_preview.py` | Parse DIAG tokens → diagram blocks; fill from figures.json |
| `src/case3/tex_prose.py` | Unrelated prose harden — **do not** mix DIAG logic here |
| `prompt/system_tex.md` | Teach DIAG slot placement (Preview-only); today still says «never DIAG» — flip in Task 4 |
| `src/case3/generate.py` / `api.py` | Nudge: slots Preview-only |
| `web/src/liberTypes.ts` | `DiagramResult` / `RunResult` already present — extend only if Preview needs shared types |
| `web/src/diagramSize.ts` | NEW: thresholds + `classifyDiagramSize(...)` |
| `web/src/InlineDiagram.tsx` | NEW: measure → inline Mermaid or chip |
| `web/src/ReportView.tsx` | `PreviewBlock` + `type: "diagram"`; prop `onOpenDiagram?: (id) => void` |
| `web/src/App.tsx` | Reuse existing `openDiagramArtifact(msgId, result, diagramId)` |
| `web/src/ArtifactRail.tsx` | Hosts Preview `ReportView` — pass `onOpenDiagram` into preview surface |
| `web/src/ChatMessages.tsx` | Already wires ArtifactCard `onOpenDiagram` — no change unless Preview path differs |
| `web/src/ArtifactCard.tsx` | Reference for chip → open pattern |
| `web/src/MermaidView.tsx` / `DiagramPane.tsx` | Reuse render; do not duplicate theme |
| `web/src/styles.css` | `.report-diagram-*` |
| `web/src/diagramSize.test.ts` | Prefer `tsx --test` like `liberRunHelpers.test.ts`; add script `test:diagram-size` or fold into `test:helpers` |
| `tests/test_inject_diagram_slots.py` | NEW |
| `tests/test_tex_preview.py` | Diagram blocks |
| `docs/adr/0007-liber-ui-only-diagrams.md` | Amendment |
| `.agents/knowledge/KI-liber-ui.md` | Preview DIAG + size-gate |

### Already shipped (do not rebuild)

- `src/case3/diagrams.py` + `tests/test_diagrams.py`
- Rail tab «Схема», `DiagramPane` / `DiagramZoomView` / `DiagramFullscreen` / PNG
- `openDiagramArtifact` in `App.tsx`
- Settings `max_diagrams` 0–3

---

### Task 1: Strip DIAG from print path

**Files:**
- Modify: `src/case3/tex_preamble.py` (`strip_orphan_slots`)
- Modify: `src/case3/inject.py`
- Test: `tests/test_inject_diagram_slots.py`

**Interfaces:**
- Consumes: TeX with `%CASE3_DIAG:id%`
- Produces: print TeX with **zero** DIAG lines

- [ ] **Step 1: Write failing test** — `strip_orphan_slots` / inject remove DIAG

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Extend regex** `FIG|CHART|DIAG`; inject always deletes DIAG (drop figure shell if only DIAG inside)

- [ ] **Step 4: Run — expect PASS → Commit** `strip CASE3_DIAG slots before PDF`

---

### Task 2: Parse — keep valid DIAG, strip orphans

**Files:**
- Modify: `src/case3/parse_output.py`
- Test: `tests/test_diagrams.py` or `tests/test_parse_diag_slots.py`

**Interfaces:**
- Valid diagram id + slot → slot kept until inject
- Orphan slot → stripped in parse
- Diagram without slot → OK (rail-only); **do not** auto-append DIAG (unlike charts)

- [ ] **Step 1–4: TDD** as above → Commit `parse: keep valid CASE3_DIAG, strip orphans`

---

### Task 3: Preview blocks from DIAG slots

**Files:**
- Modify: `src/case3/tex_preview.py`
- Modify: `tests/test_tex_preview.py`

**Interfaces:**
- `build_report_preview` → `{type:"diagram", id, title, diagramType, mermaid}`

- [ ] **Step 1–5: TDD** tokenize DIAG before paragraph flush; fill from `figures_json["diagrams"]`; skip missing → Commit `preview: diagram blocks from CASE3_DIAG`

---

### Task 4: Prompt + API nudge

**Files:**
- Modify: `prompt/system_tex.md` — replace «never `%CASE3_DIAG`» with Preview-only placement rules
- Modify: `src/case3/generate.py` / `src/case3/api.py` nudge bullets

- [ ] **Step 1–3:** Document slot after explaining paragraph; never `\begin{figure}`; PDF strips → Commit `prompt: CASE3_DIAG for Liber Preview`

---

### Task 5: Size classifier (pure TS)

**Files:**
- Create: `web/src/diagramSize.ts`
- Create: `web/src/diagramSize.test.ts`
- Modify: `web/package.json` — extend `test:helpers` or add `test:diagram-size`

**Interfaces:**

```ts
export type DiagramSizeMode = "inline" | "chip";
export function classifyDiagramSize(input: {
  source: string;
  bbox?: { width: number; height: number };
}): DiagramSizeMode;
```

Thresholds (spec): height>280 · width>520 · nodes≥8 · lines≥28 → chip

- [ ] **Step 1–3: TDD** → `npm run test:helpers` (or new script) PASS → Commit

---

### Task 6: InlineDiagram + ReportView

**Files:**
- Create: `web/src/InlineDiagram.tsx`
- Modify: `web/src/ReportView.tsx` — extend `PreviewBlock`; render branch; `onOpenDiagram?: (id: string) => void`
- Modify: `web/src/styles.css`

**Interfaces:**
- Reuse `MermaidView` / theme tokens from DiagramPane
- Inline: compact frame + «Открыть»
- Chip: button → `onOpenDiagram(id)`

- [ ] **Step 1–5:** implement + `cd web && npm run build` → Commit `web: inline/chip diagrams in Preview`

---

### Task 7: Wire Preview Open → Artifact rail

**Files:**
- Modify: `web/src/ArtifactRail.tsx` — where Preview mounts `ReportView`, pass  
  `onOpenDiagram={(id) => onSelectDiagram?.(id)}` (or existing setter that sets `tab: "diagram"` + `activeDiagramId`)
- Modify: `web/src/App.tsx` only if rail callback missing — prefer **reuse** `openDiagramArtifact` / `setActiveArtifact` path already used by `ChatMessages` → `ArtifactCard`

**Do not** put open logic in `ChatMessages` for Preview (Preview lives in rail).

- [ ] **Step 1–3:** smoke Open from inline/chip → Схема tab + correct id → Commit

---

### Task 8: Docs memory

**Files:**
- `docs/adr/0007-liber-ui-only-diagrams.md` — Amendment: Preview inline/chip; print still strips
- `.agents/knowledge/KI-liber-ui.md` — DIAG slots + size-gate
- Spec status → approved after implement

- [ ] Commit `docs: ADR-0007 amendment Preview inline diagrams`

---

### Task 9: Verification gate

- [ ] `.venv/bin/python -m pytest tests/test_diagrams.py tests/test_tex_preview.py tests/test_inject_diagram_slots.py -q`
- [ ] `cd web && npm run build && npm run test:helpers`
- [ ] Optional live: process Source → Preview shows inline or chip; PDF has no schema page
- [ ] Do not claim done until pytest + build green

---

## Out of scope

- Mermaid editor / Apply  
- Diagram PNG in PDF  
- New Mermaid types  
- Auto-append DIAG when model forgets slots  
- Touching `tex_prose.py` for DIAG

## Pre-flight (repo state after Liber refactor)

Verified before this plan revision:

- `tests/test_diagrams.py` (+ related) green  
- `web` `npm run build` green  
- Types: `DiagramResult` in `liberTypes.ts`; open path `App.openDiagramArtifact` + `ChatMessages`  

Inline Preview feature itself is **not** implemented until Tasks 1–9 run.
