# Liber Inline Preview Diagrams — Design

**Date:** 2026-10-21  
**Status:** draft (awaiting user review)  
**Parent:** ADR-0007 (UI-only Mermaid) · Spec `2026-10-21-liber-semantic-diagrams-design.md`

## Goal

Small Mermaid schemas appear **inline in Liber Preview** (next to the prose they explain), like chart/figure blocks. Large schemas stay an **app surface**: compact chip in Preview → Artifact tab «Схема» / fullscreen. **PDF/DOCX never gain diagram images** (ADR-0007 holds; slots are position markers only).

## Non-goals (this slice)

- No Playwright PNG / TeX `\includegraphics` for diagrams.
- No edit Mermaid sheet / Apply (charts-only for now).
- No new Mermaid types beyond existing whitelist.
- No auto-split of one huge diagram into multiple pages.
- No diagram inject when `CASE3_MAX_DIAGRAMS=0`.

## Decision summary

| Choice | Value |
|--------|--------|
| Placement | TeX marker `%CASE3_DIAG:id%` (same line-alone contract as FIG/CHART) |
| Print | Always **strip** DIAG slots before latexmk — empty in PDF |
| Preview | Marker → `preview.blocks[]` entry `type: "diagram"` |
| Size policy | Client **size-gate** after Mermaid SVG layout |
| Missing slot | Diagram still in rail only (current v1) — soft-fail |
| Orphan slot | No matching `diagrams[]` id → drop marker; no Preview block |

## Why slots (not JSON-only anchors)

Charts already teach the model “slot alone on a line next to the paragraph.” Reusing that contract gives **stable order** in Preview without a second placement language. Unlike charts, inject never replaces the slot with a float — Preview is the only consumer.

## Architecture

```text
LLM
  ├─ JSON diagrams[{ id, title, type, mermaid }]
  └─ TeX … prose …
         %CASE3_DIAG:dia_01%     ← position only
         … 

parse_output
  ├─ validate diagrams[] (unchanged)
  ├─ collect DIAG slots; strip orphans without JSON
  └─ keep valid DIAG slots in TeX until inject

inject / strip_orphan_slots
  └─ ALWAYS remove %CASE3_DIAG:…%  (never figure env)

tex_preview / build_report_preview
  └─ replace DIAG slot with block { type: "diagram", id, title, mermaid, dtype }

Liber ReportView
  └─ InlineDiagram
        ├─ measure SVG → mode: "inline" | "chip"
        ├─ inline: compact Mermaid (+ «Открыть» → rail)
        └─ chip: title + Open → Artifact tab diagram
```

## Data model

### TeX marker

```tex
%CASE3_DIAG:dia_01%
```

- Alone on a line (leading whitespace OK).
- Id: `^[a-z][a-z0-9_]{0,31}$` (same as FIG/CHART).
- Prefer `dia_NN`. Unique vs figures/charts/diagrams.
- **Do not** wrap in `\begin{figure}` (prompt forbids; if wrapped, strip whole shell like failed chart).

### Preview block

```json
{
  "type": "diagram",
  "id": "dia_01",
  "title": "Согласование договора",
  "diagramType": "flowchart",
  "mermaid": "flowchart TD\n  A-->B"
}
```

Built only when slot id exists in `figures.json` → `diagrams[]` after sanitize.

### Size-gate (client)

After `mermaid.render` → SVG in a temp/hidden measure or first paint:

| Signal | Threshold (v1) | Effect |
|--------|----------------|--------|
| SVG `getBBox().height` (CSS px) | `> 280` | chip |
| SVG `getBBox().width` | `> 520` | chip |
| Node/actor count (heuristic) | `≥ 8` | chip |
| Source lines (non-empty) | `≥ 28` | chip (pre-render fast path) |

Any one trigger → **chip**. Else **inline**.

Constants live in `web/src/diagramSize.ts` so tests can assert without DOM.

**Always offer** «Открыть» / click → focus Artifact «Схема» for that id (even when inline).

## Prompt changes (`system_tex.md`)

- Document `%CASE3_DIAG:id%` as **Preview position only** — not printed.
- When emitting a diagram that explains a nearby section, place the slot **after the paragraph** that introduces the process (same rhythm as charts).
- Prefer **one** inline slot for the primary diagram; second diagram may be rail-only (no slot) if Source is dense.
- Intent «без схем» / `MAX_DIAGRAMS=0` → no slots, empty `diagrams[]`.

## Pipeline / API

| Piece | Change |
|-------|--------|
| `parse_output.py` | Recognize DIAG slots; strip unknown; keep valid until inject |
| `inject.py` / `strip_orphan_slots` | Extend regex to `FIG\|CHART\|DIAG` — always delete DIAG |
| `tex_preview.py` | Tokenize `%CASE3_DIAG:id%` into diagram placeholder blocks; `build_report_preview` fills mermaid |
| `api.py` / payload | Unchanged diagrams list; preview blocks gain `type: "diagram"` |
| Soft-fail | Bad mermaid still dropped from JSON → orphan slot stripped |

No new env vars. Cap still `CASE3_MAX_DIAGRAMS`.

## Liber UX

### Inline mode

- Liber soft-green frame (reuse diagram pane tokens, compact).
- Caption row: title + type badge + «Открыть».
- No zoom chrome in-flow (keeps Preview calm); open rail for zoom/PNG.

### Chip mode

- Card ~1 line title + subtitle «Большая схема · открыть в Схема».
- Click → `onOpenDiagram(id)` (same as ArtifactCard chips).

### Rail

- Unchanged: full DiagramPane + fullscreen + PNG.
- Opening from Preview selects tab `diagram` + `activeDiagramId`.

### Empty / error

- Client render fail on inline → collapse to chip with «Не удалось отрисовать» + Open still works if rail can retry, or show raw collapsible (match DiagramPane).

## ADR

Amend **ADR-0007**: Preview may show diagrams **inline or as chips** via `%CASE3_DIAG` markers; print path still never injects diagram images. Status remains Accepted (amendment, not supersede).

## Risks

| Risk | Mitigation |
|------|------------|
| Model forgets slots | Rail-only fallback (already shipped) |
| Model wraps DIAG in figure | Strip shell in inject (mirror chart) |
| Inline too tall on mobile | Width/height gate + chip |
| Preview ≠ PDF more visible | Footer hint on inline: «Только в Liber · не в PDF» (subtle) |
| Double render cost | Measure once; chip skips second full zoom mount until open |

## Success criteria

1. Fixture TeX with `%CASE3_DIAG:dia_01%` + matching diagrams JSON → Preview block in correct order; PDF TeX has **no** DIAG slot and **no** diagram float.
2. Large fixture (sequence ≥8 messages) → chip in Preview; Open focuses rail.
3. Small flowchart (≤5 nodes) → inline SVG visible in Preview.
4. Orphan DIAG / missing JSON → no crash; slot gone; pipeline `ok`.
5. `max_diagrams=0` → no DIAG slots expected; any leftover stripped.

## Open follow-ups (out of this plan)

- Edit Mermaid + Apply.
- Opt-in diagram PNG in PDF (new ADR).
- `diagrams_dropped` surface in UI.
