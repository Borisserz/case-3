# Liber Semantic Diagrams (UI-only) — Design

**Date:** 2026-10-21  
**Status:** approved (implementing / shipped in-repo)  
**Decision:** diagrams live **only in Liber UI**; optional **Download PNG**; **not** injected into PDF/DOCX.

## Goal

Together with each report, when Source/Intent has a **structural** story (process, architecture, decision tree, org, cause→effect, timeline of steps — not raw numbers), Liber generates **1–3 Mermaid diagrams** and shows them in the Artifact rail as browser-like tabs. User can open fullscreen and download PNG.

## Non-goals (v1)

- No `%CASE3_DIAG` TeX slots, no `\includegraphics` for diagrams, no PDF/DOCX pages.
- No Mermaid edit/restyle sheet (charts already have Apply).
- No Graphviz/PlantUML second language.
- No Mary-style mindmap IA in left Sidebar.
- No `requestFullscreen` API (portal overlay instead).

## Why not PDF

User choice: UI exploration + PNG export is enough. Keeps ADR-0001: **PDF = print truth** for charts/photos only. Diagrams are Liber companion artifacts (like LiveChart interactivity, but without a print twin).

## Approaches considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **A. Same LLM JSON + client Mermaid** | One call; soft-fail; mirrors charts schema; PNG on demand in browser | LLM may emit invalid Mermaid; need sanitize | **Chosen** |
| B. Third media kind → Playwright PNG → inject | Reuses chart pipeline | User rejected PDF; wastes TeX/inject | Rejected |
| C. Second LLM call after TeX | Cleaner TeX prompt | Extra latency/cost; two failure modes | Rejected for v1 |

## Architecture

```text
LLM (system_tex)
  └─ JSON: figures[] + charts[] + diagrams[]   ← NEW
       diagrams: [{ id, title, type, mermaid }]
  └─ TeX: unchanged (no diagram slots)

parse_output → validate Mermaid (fence-strip, type whitelist, size caps)
figures.json (or diagrams key inside) → out/
API result payload: diagrams[]
Liber: DiagramStrip + MermaidView (client) + PNG download
```

**Invariant:** diagram failure never fails the pipeline (same soft-fail spirit as charts). Invalid Mermaid → drop that id + warning; PDF still builds.

## Data model

```json
{
  "diagrams": [
    {
      "id": "dia_01",
      "title": "Процесс согласования",
      "type": "flowchart",
      "mermaid": "flowchart TD\n  A[Заявка] --> B{ОК?}\n  B -->|да| C[Готово]\n  B -->|нет| A"
    }
  ]
}
```

| Field | Rules |
|-------|--------|
| `id` | `^dia_[a-z0-9_]+$` or `^[a-z][a-z0-9_]*$`; unique across figures+charts+diagrams |
| `title` | RU short, ≤80 chars; shown in strip + fullscreen |
| `type` | whitelist: `flowchart` \| `sequence` \| `mindmap` \| `timeline` \| `stateDiagram` |
| `mermaid` | plain source, **no** ``` fences; ≤6 KB; only allowed diagram kinds |

Cap: `CASE3_MAX_DIAGRAMS` (default **2**, UI Settings 0–3). `0` = skip diagrams entirely.

## When the LLM should emit diagrams

**Default-on:** if `max_diagrams ≥ 1`, emit **≥1** diagram whenever Source has any structure (steps, roles, branches, architecture, timeline, or ≥3 topical sections). Skip only if budget 0, Intent says «без схем», or Source is pure numbers with no structure.

Prefer **1** strong diagram. Numbers + process → charts **and** one diagram.

Validation: type↔first-line header; `graph` → `flowchart`; soft-drops in `diagrams_dropped`.

## Pipeline / API

| Piece | Change |
|-------|--------|
| `prompt/system_tex.md` | `diagrams[]` schema + when-to-emit + type whitelist |
| `parse_output.py` | parse/validate `diagrams`; strip fences; drop bad |
| `generate.py` | persist `diagrams` in `figures.json` |
| `pipeline.py` | `diagrams_planned` in meta; **no** render/inject stage |
| `api.py` `_run_result_payload` | `diagrams: [...]` |
| `GET /api/runs/{id}/diagrams/{id}` | optional; or ship full list in status payload only (v1: **payload is enough**) |
| `POST …/diagrams/{id}/png` | **not** in v1 — client exports PNG |

Dry-run: empty `diagrams` or stub one if Settings > 0 (match chart dry-run style — prefer empty + skip).

## Liber UX

### Tab model (two strips)

Do **not** add a fourth peer of Preview|PDF|Source.

1. **Document strip** (unchanged): Preview · PDF · Source  
2. **Diagram strip** (new, only if `diagrams.length > 0`): chip tabs `title` / `D1…`, closable focus, browser-like

State on report artifact:

```ts
railSurface: "document" | "diagram";
activeDiagramId: string | null;
// diagrams come from RunResult.diagrams
```

Click diagram chip → `railSurface: "diagram"`. Click Preview/PDF/Source → `railSurface: "document"` (strip stays; selection remembered).

### Surfaces

| Surface | Content |
|---------|---------|
| Diagram pane | title, Mermaid SVG, toolbar: Fullscreen · Download PNG |
| Fullscreen | portal to `document.body` (reuse lightbox patterns): Esc / ×; Download PNG |
| Chat | compact chip(s) «Схема: {title}» under ArtifactCard → opens rail diagram surface |

### PNG download

Client-only: rendered SVG → canvas → `toBlob('image/png')` → download `{id}.png`. Scale 2× for retina. Soft-premium tokens for Mermaid theme (no purple neon).

### Left Sidebar

Unchanged. Diagrams are **not** Sidebar windows — user “side window” = Artifact rail.

## Settings

- Slider/stepper **Схемы (0–3)** next to chart/image limits in `SettingsModal`.
- Passed as FormData / run body → `max_diagrams` → prompt `{{MAX_DIAGRAMS}}`.

## Error / empty states

- 0 diagrams → no strip, no chips (silent).  
- Invalid Mermaid after parse → omitted + `warnings[]` entry.  
- Client render fail → pane shows «Не удалось отрисовать схему» + raw Mermaid collapsible (debug), still no PDF impact.

## Testing

- Unit: parse valid/invalid mermaid, fence strip, cap, id collision.  
- Prompt dry fixture: Source with process → diagrams non-empty (manual or golden).  
- UI: strip appears; fullscreen Esc; PNG download smoke (Playwright or manual).  
- Regression: PDF build unchanged when diagrams present.

## Docs to update after ship

- KI-liber-ui, KI-pipeline  
- ADR-0003 short amendment (rail hosts UI-only diagrams)  
- Optional ADR-0007 if we want a numbered decision

## Open for later (not v1)

- Server PNG for email/share  
- Diagram in Preview TeX as non-print callout  
- Edit Mermaid in rail  
- Persist strip across reload beyond session history payload
