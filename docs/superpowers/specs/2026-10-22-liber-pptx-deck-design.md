# Liber Presentation Deck (web + image PPTX/PDF) — Design

**Date:** 2026-10-22  
**Status:** approved (2026-10-22) · plan: [`../plans/2026-10-22-liber-pptx-deck.md`](../plans/2026-10-22-liber-pptx-deck.md)  
**Unparks:** [`docs/knowledge/parked-pptx.md`](../../knowledge/parked-pptx.md)  
**Related:** ADR-0002 (charts/Playwright), ADR-0003 / ADR-0006 (Liber UI), artifact rail + semantic diagrams specs  
**Doubt cycle:** frontend anti-slop (fail→cut themes), backend (pass-with-fixes), UI explore (diagram-pattern)

## Goal

On demand (not every report run), produce an **executive deck** from the same Source+Intent as the report:

1. **Web slideshow** in Liber Artifact rail — primary visual experience (Liber soft-premium, not a second brand).
2. **Export:** image-based **PPTX** (full-bleed PNG per slide) + **PDF of slides** (one page per slide).
3. **Editable PPTX** — explicitly **out of scope for v1** (revisit later).

Report PDF/DOCX remain print truth for the **document**. The deck is a separate executive artifact.

## Non-goals (v1)

- Dumping TeX / pandoc into slides.
- Extending `formats` / Docker TeX `render_tex` with PPTX.
- Embedding Presenton or PPTAgent runtime.
- Freeform LLM CSS / HTML as capture source of truth.
- Named alternate skins («Night Brief», «Data Pulse», …).
- Layouts beyond the v1 whitelist; layout «variants».
- Excel-native Office charts; KPI count-up as meaning; heavy motion.
- HTML zip / ODP / Keynote / MP4.
- Inline slide editing in chat (regenerate whole deck only).
- Auto-opening presentation when the report finishes (PDF-first).

## Product decisions (locked)

| Decision | Choice |
|----------|--------|
| Relation to report | Third artifact (executive summary), same Source |
| Visual priority | Liber web look; PPTX/PDF are **raster captures** of that look |
| PPTX editability | Non-editable image slides in v1 |
| Downloads | PPTX + deck PDF (not report PDF) |
| Trigger | Liber button after `meta.status == ok` |
| Variety | Layout **sequence** + Source content + run palette — not theme switching |

## Architecture

```text
Report ready (out/: figures.json, figures/, Source, Intent, palette)
        │
        ▼  ArtifactCard / rail CTA «Сделать презентацию»
POST /api/runs/{run_id}/slides  →  202
        │  BackgroundTasks + to_thread (same pattern as /api/run)
        ├─ Qwen + prompt/system_slides.md → slides/deck.json (IR)
        ├─ Validate IR (layouts, Source-bound numbers, limits)
        ├─ Per slide: static HTML frame (chart_frame-like) + Chart.js 16:9
        ├─ Playwright screenshot @ fixed 1920×1080 (DPR≥2 optional)
        ├─ python-pptx: blank 16:9 + full-bleed pictures → *_slides.pptx
        └─ PNG sequence → *_deck.pdf
        │
        ▼
meta.slides_* + downloads.pptx / downloads.deck_pdf
Liber: conditional tab «Презентация» + fullscreen; Export labels distinct
```

### Hard separation from report render

- **Do not** add `pptx` to `formats` or `render_tex`.
- Slides job must **not** overwrite report `meta.status` / `meta.stage`.
- Soft-fail: slides error leaves PDF/DOCX intact.

### Capture path (quality bar)

- Capture uses a **fixed offline canvas** (static HTML + local fonts/assets), same discipline as ADR-0002 charts — **not** a screenshot of the Artifact rail or live Vite UI.
- Liber React preview **reads the same IR** and should share CSS tokens / class names with the capture frame so preview ≈ export without requiring pixel identity of chrome.
- Motion (optional fade ≤200ms) must not carry hierarchy; a static PNG must look finished.

## Deck IR (`slides/deck.json`)

Conceptual schema (exact JSON Schema in implementation plan):

```json
{
  "version": 1,
  "aspect": "16:9",
  "palette": "atelier",
  "language": "ru",
  "slides": [
    {
      "id": "s01",
      "layout": "title",
      "title": "…",
      "subtitle": "…"
    },
    {
      "id": "s02",
      "layout": "chart_hero",
      "title": "…",
      "caption": "…",
      "chart_id": "cht_01"
    },
    {
      "id": "s03",
      "layout": "bullets",
      "title": "…",
      "bullets": ["…", "…"]
    },
    {
      "id": "s04",
      "layout": "closing",
      "title": "…",
      "bullets": ["…"]
    }
  ]
}
```

### Layout whitelist (v1) — exactly four

| Layout | Role |
|--------|------|
| `title` | Opening: title + optional subtitle |
| `chart_hero` | One chart + title + short caption |
| `bullets` | ≤5 bullets, short lines |
| `closing` | Next steps / closing |

Deferred: `agenda`, `kpi_row`, `chart_split`, `photo_quote`, variants.

### Validation rules

- `layout` ∈ whitelist; `palette` ∈ existing Liber palette IDs only (inherit run Intent by default; model must not invent hex).
- Chart types ∈ `CHART_TYPES`; prefer referencing chart/figure IDs already in the run; re-render Chart.js at 16:9 via existing style path.
- **Source-bound numbers:** any digit sequences in IR text must appear in Source (exact substring) or come from validated chart/table payloads already produced for the run; reject otherwise.
- Text limits (enforce in schema + prompt): title ≤80 chars; subtitle ≤120; bullet ≤72 chars; ≤5 bullets per `bullets`/`closing` slide.
- Slide count: target 6–12; hard max 12.

### Prompt

- New file: `prompt/system_slides.md` (or equivalent).
- **Do not** extend `prompt/system_tex.md`.

## Visual system (anti-slop)

**One skin = Liber soft-premium:** olive sage, DM Sans + Crimson, mist/sage backgrounds, existing chart palettes (`editorial` / `ocean` / `sunset` / `mono` / `atelier`).

Positive rules:

- One accent color per slide; hierarchy from scale and space.
- Generous margins; no wall of text; no emoji; no purple/indigo gradients; no neon glow; no glassmorphism pile-up; no badge/pill spam.
- Charts: reuse Liber chart CSS dialect; no second «deck chart» aesthetic.

Fonts in capture Chromium must load the same faces as Liber (bundle or guaranteed desk fonts); document fallback strategy in the plan so Windows desk does not silently substitute.

## API

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/api/runs/{run_id}/slides` | 202 if report `meta.status == ok`; else 409. Starts slides job. |
| `GET` | `/api/runs/{run_id}/status` | Existing poll; **add** `slides_status`, `slides_stage`, `slides_error`, `slides_artifacts` without clobbering report fields. |
| `GET` | `/api/runs/{run_id}/slides` | IR + artifact URLs when available. |

Suggested stages: `queued` → `llm` → `render` → `pptx` → `ok` | `error`.

### Artifact paths (under `runs/out/{run_id}/`)

```text
slides/deck.json
slides/slide_01.png … slide_N.png
slides/work/…          # optional HTML work dirs
{stem}_slides.pptx
{stem}_deck.pdf
```

Report `{stem}.pdf` / `{stem}.docx` untouched (write slide artifacts via temp + rename).

### Downloads payload

Extend result/downloads with **explicit keys** (fix suffix-only map that would collide on `.pdf`):

```json
{
  "pdf": "<report pdf>",
  "docx": "<report docx>",
  "pptx": "<slides pptx>",
  "deck_pdf": "<slides pdf>"
}
```

MIME for `.pptx` in download handler. Export UI labels:

- «PDF отчёта»
- «DOCX»
- «PPTX»
- «PDF презентации»

## Liber UI

Mirror **Схема** (conditional tab + card CTA), not always-on chrome.

1. CTA «Сделать презентацию» on `ArtifactCard` (and/or rail) when report ready and slides idle/missing.
2. Poll `/status` (~400ms) like existing run poll; show thinking / in-pane progress.
3. On success: show tab **«Презентация»**, optional pulse on Export; **do not** steal default PDF open on report ready.
4. Rail pane: mini-deck + **fullscreen** (DiagramFullscreen pattern) for 16:9 viewing.
5. Empty permanent tab forbidden.

Primary files (expected): `ArtifactRail.tsx`, `ArtifactCard.tsx`, `ExportMenu.tsx`, `App.tsx`, `liberTypes.ts`, new `PresentationPane.tsx` (+ fullscreen), `styles.css`.

## Dependencies

- Add `python-pptx` (and a chosen PNG→PDF helper, e.g. Pillow or img2pdf) to project deps.
- Playwright already present; serialize slides job with chart Playwright pool (avoid contention with chart edit).

## QA / acceptance

Before calling v1 «premium»:

1. Visual matrix: ≥3 real Source fixtures × 1 Liber skin × 4 layouts; static PNGs reviewed full-size.
2. PPTX and deck PDF open on Windows; slides are full-bleed, no letterboxing, fonts acceptable.
3. Report PDF/DOCX unchanged after a failed or successful slides job.
4. Export menu never shows two items both named only «PDF».
5. Invented numbers in IR rejected or stripped in tests.
6. Decks must not be interchangeable with generic Gamma-like defaults after a palette swap (human eyeball gate).

## Implementation phases (hint for plan)

1. IR schema + `system_slides.md` + validator + unit tests.  
2. Static slide HTML templates + Chart.js 16:9 + Playwright capture.  
3. PPTX + deck PDF builders + artifact keys.  
4. API slides job + meta fields.  
5. Liber CTA, tab, fullscreen, Export labels.  
6. Visual QA matrix on desk.

## Open follow-ups (post-v1)

- Editable PPTX (text boxes + chart PNGs).
- Extra layouts (`kpi_row`, …) after QA.
- Optional second tone only if Liber skin is proven.
- Vision review loop (PPTAgent-style) as optional gate.

## ADR / KI

- After implementation: short ADR (e.g. «deck IR + static capture → image PPTX») and KI card for slides subsystem.
- Update artifact-rail design note: presentation tab + Export keys (diagrams already extended the rail beyond the original 3 tabs).
