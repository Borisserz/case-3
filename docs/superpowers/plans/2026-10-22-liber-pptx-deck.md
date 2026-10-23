# Liber Presentation Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On-demand Liber executive deck from an existing report run: deck IR → static Liber-skinned slides → Playwright PNGs → image PPTX + deck PDF, with rail preview + Export.

**Architecture:** Separate async job `POST /api/runs/{id}/slides` (does not touch `formats` / Docker TeX). Qwen fills `slides/deck.json` via `prompt/system_slides.md`. Capture uses fixed 1920×1080 static HTML (same Playwright discipline as charts). Liber React reads the same IR for preview/fullscreen. Downloads use explicit keys `pptx` and `deck_pdf`.

**Tech Stack:** FastAPI, Qwen (`VISION_*`), Playwright, Chart.js (existing), `python-pptx`, Pillow (already in deps), Vite React Liber UI.

**Spec:** [`docs/superpowers/specs/2026-10-22-liber-pptx-deck-design.md`](../specs/2026-10-22-liber-pptx-deck-design.md)

## Global Constraints

- Do **not** extend `formats` or `render_tex` with PPTX.
- Do **not** modify `prompt/system_tex.md` for slides.
- One Liber skin only (olive sage, DM Sans + Crimson, run palette IDs). No Night Brief / Data Pulse themes.
- Layouts v1 only: `title` | `chart_hero` | `bullets` | `closing`.
- Image PPTX only (full-bleed PNGs); no editable text boxes in v1.
- Source-bound numbers; soft-fail slides must not corrupt report PDF/DOCX.
- Capture = static HTML canvas, not Artifact rail / Vite screenshot.
- Export labels: «PDF отчёта» / «DOCX» / «PPTX» / «PDF презентации».
- PDF-first on report ready — do not auto-open «Презентация».
- Commits only when the user explicitly asks (skip commit steps otherwise).

## File map

| Path | Responsibility |
|------|----------------|
| `prompt/system_slides.md` | NEW: LLM contract for deck IR |
| `src/case3/slides_ir.py` | NEW: layouts whitelist, parse/validate IR, Source number gate |
| `src/case3/slides_html.py` | NEW: IR → static slide HTML (Liber CSS tokens) |
| `src/case3/slides_render.py` | NEW: Playwright capture 1920×1080; chart re-render helpers |
| `src/case3/slides_export.py` | NEW: PNGs → PPTX + deck PDF |
| `src/case3/slides_job.py` | NEW: orchestrate LLM → validate → render → export; update meta |
| `src/case3/templates/slide_frame.html` | NEW: offline slide chrome + font hooks |
| `src/case3/templates/slide_chart_mount.html` | NEW or reuse chart_frame patterns for 16:9 chart PNGs |
| `src/case3/api.py` | `POST …/slides`, status fields, downloads keys, pptx MIME |
| `pyproject.toml` | add `python-pptx` |
| `tests/test_slides_ir.py` | NEW |
| `tests/test_slides_export.py` | NEW |
| `tests/test_api_slides.py` | NEW |
| `web/src/liberTypes.ts` | slides status + download keys + deck IR types |
| `web/src/ExportMenu.tsx` | four labeled downloads |
| `web/src/ArtifactCard.tsx` | CTA «Сделать презентацию» |
| `web/src/PresentationPane.tsx` | NEW: mini-deck + controls |
| `web/src/PresentationFullscreen.tsx` | NEW: 16:9 overlay (mirror DiagramFullscreen) |
| `web/src/ArtifactRail.tsx` | conditional tab «Презентация» |
| `web/src/App.tsx` | start slides job, poll `slides_*`, wire downloads |
| `web/src/styles.css` | Liber slide preview tokens (shared names with slide_frame) |
| `docs/knowledge/parked-pptx.md` | mark shipped when done |
| `docs/adr/0008-liber-deck-image-pptx.md` | NEW after ship |
| `.agents/knowledge/KI-liber-deck.md` | NEW after ship |

---

### Task 1: Deck IR parse + Source number gate

**Files:**
- Create: `src/case3/slides_ir.py`
- Create: `tests/test_slides_ir.py`
- Create: `prompt/system_slides.md` (stub schema matching validator)

**Interfaces:**
- Produces: `SLIDE_LAYOUTS: frozenset[str]`, `parse_deck_ir(data: dict, *, source: str, max_slides: int = 12) -> dict`, `DeckIrError`
- Consumes: `chart_style.PALETTE_IDS` / `normalize_palette_id`; `chart_html.CHART_TYPES` for chart refs

- [ ] **Step 1: Write failing tests**

```python
# tests/test_slides_ir.py
from case3.slides_ir import parse_deck_ir, DeckIrError

SOURCE = "Выручка 120 млн в 2024 году. Доля 35%."

def test_accepts_four_layouts_and_source_number():
    ir = parse_deck_ir(
        {
            "version": 1,
            "aspect": "16:9",
            "palette": "atelier",
            "language": "ru",
            "slides": [
                {"id": "s01", "layout": "title", "title": "Итоги", "subtitle": "2024"},
                {
                    "id": "s02",
                    "layout": "bullets",
                    "title": "Факты",
                    "bullets": ["Выручка 120 млн", "Доля 35%"],
                },
                {"id": "s03", "layout": "closing", "title": "Далее", "bullets": ["План"]},
            ],
        },
        source=SOURCE,
    )
    assert len(ir["slides"]) == 3

def test_rejects_unknown_layout():
    try:
        parse_deck_ir(
            {"version": 1, "palette": "atelier", "slides": [
                {"id": "s01", "layout": "kpi_row", "title": "X"}
            ]},
            source=SOURCE,
        )
        assert False
    except DeckIrError:
        pass

def test_rejects_invented_number():
    try:
        parse_deck_ir(
            {"version": 1, "palette": "atelier", "slides": [
                {"id": "s01", "layout": "bullets", "title": "X",
                 "bullets": ["Выручка 999 млрд"]}
            ]},
            source=SOURCE,
        )
        assert False
    except DeckIrError:
        pass
```

- [ ] **Step 2: Run** `pytest tests/test_slides_ir.py -v` — expect FAIL (module missing)

- [ ] **Step 3: Implement `slides_ir.py`**
  - Layouts: `title`, `chart_hero`, `bullets`, `closing`
  - Limits: title ≤80, subtitle ≤120, bullet ≤72, ≤5 bullets, max 12 slides
  - Number gate: extract digit-runs from slide text; each must appear as substring in `source` (normalize spaces); allow numbers that only appear inside referenced chart payloads if you pass optional `allowed_number_strings` from figures.json later (v1: Source substring is enough; chart_hero title/caption still gated)
  - Normalize palette via existing helper; reject unknown
  - `chart_hero` requires `chart_id` matching `^[a-z][a-z0-9_]{1,31}$`

- [ ] **Step 4: Write `prompt/system_slides.md`** aligned with schema (executive deck, Source-only, 6–12 slides, four layouts, Liber tone, no purple)

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Commit** (only if user asked) `feat(slides): deck IR validator and system_slides prompt`

---

### Task 2: PNG → PPTX + deck PDF export

**Files:**
- Modify: `pyproject.toml` (add `python-pptx>=1.0`)
- Create: `src/case3/slides_export.py`
- Create: `tests/test_slides_export.py`

**Interfaces:**
- Produces: `build_image_pptx(png_paths: list[Path], dest: Path, *, width_in: float = 13.333, height_in: float = 7.5) -> Path`, `build_deck_pdf(png_paths: list[Path], dest: Path) -> Path`
- Consumes: Pillow (already), python-pptx

- [ ] **Step 1: Add dependency** `python-pptx` to `pyproject.toml`; install in env

- [ ] **Step 2: Write failing tests** with tiny 64×36 PNGs in tmp_path

```python
def test_pptx_has_one_shape_per_slide(tmp_path):
    from case3.slides_export import build_image_pptx
    from pptx import Presentation
    pngs = [_solid_png(tmp_path / f"{i}.png") for i in range(2)]
    out = build_image_pptx(pngs, tmp_path / "d.pptx")
    prs = Presentation(str(out))
    assert len(prs.slides) == 2

def test_deck_pdf_page_count(tmp_path):
    from case3.slides_export import build_deck_pdf
    from PIL import Image
    pngs = [_solid_png(tmp_path / f"{i}.png") for i in range(2)]
    out = build_deck_pdf(pngs, tmp_path / "d.pdf")
    assert out.is_file() and out.stat().st_size > 100
```

- [ ] **Step 3: Implement**
  - PPTX: blank layout, slide width/height 13.333"×7.5" (16:9), each PNG as picture covering full slide (no margins)
  - PDF: Pillow save multipage PDF or one image per page at 1920×1080

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** (if asked) `feat(slides): image PPTX and deck PDF builders`

---

### Task 3: Static slide HTML + Playwright capture

**Files:**
- Create: `src/case3/templates/slide_frame.html`
- Create: `src/case3/slides_html.py`
- Create: `src/case3/slides_render.py`
- Create: `tests/test_slides_html.py` (HTML contains required classes / dimensions)
- Optional smoke: `tests/test_slides_render_smoke.py` marked skip if no browser

**Interfaces:**
- Produces: `render_slide_html(slide: dict, *, palette: str, chart_png: Path | None) -> str`, `write_slide_work(slide, work_dir) -> Path` (index.html), `capture_slide_png(html_dir: Path, dest: Path) -> None`
- Consumes: Playwright via `charts._run_sync_playwright` (reuse pool/thread helper — import carefully or extract shared helper if circular)

- [ ] **Step 1: Failing test** — `render_slide_html` for `title` includes `data-layout="title"` and inline/canvas size 1920×1080

- [ ] **Step 2: Implement `slide_frame.html` + `slides_html.py`**
  - Liber tokens (CSS variables matching soft-premium: sage, mist, DM Sans/Crimson via `@font-face` from packaged or CDN-free local files under `templates/fonts/` if needed — prefer package fonts or system stack documented in comment)
  - Layouts: title / bullets / closing / chart_hero (img for chart PNG)
  - Anti-slop: no gradients purple, no emoji slots

- [ ] **Step 3: Implement `capture_slide_png`**
  - viewport 1920×1080; `file://` + route sandbox like `charts.py`
  - screenshot `#slide` (or full page); assert non-blank (reuse blank detection idea)

- [ ] **Step 4: For `chart_hero`** — helper to render chart at ~1600×700 using existing `render_chart_png` / work dir, then embed path in slide HTML (relative)

- [ ] **Step 5: Unit tests PASS**; optional smoke with Playwright

- [ ] **Step 6: Commit** (if asked) `feat(slides): Liber static slide HTML and capture`

---

### Task 4: Slides job orchestrator + API

**Files:**
- Create: `src/case3/slides_job.py`
- Modify: `src/case3/api.py`
- Create: `tests/test_api_slides.py`
- Modify: `_run_result_payload` downloads map; `download_file` MIME for pptx

**Interfaces:**
- Produces: `run_slides_job(run_id: str, *, root: Path) -> None` updating `meta.json`
- API: `POST /api/runs/{run_id}/slides` → 202; `GET /api/runs/{run_id}/slides` → IR + urls
- Meta keys: `slides_status`, `slides_stage`, `slides_error`, `slides_artifacts`
- Downloads: `pptx`, `deck_pdf` explicit (do not discover deck PDF via bare `.pdf` suffix overwrite)

- [ ] **Step 1: Failing API tests** with TestClient + tmp runs dir fixture (follow `tests/test_api_routes.py` patterns)
  - 409 if report not ok
  - 202 when ok; meta gains `slides_status`

- [ ] **Step 2: Implement `slides_job.py`**
  - Load Source/Intent from run out (same places pipeline stores — verify paths in code)
  - Call LLM with `system_slides.md` + Source + Intent + available chart ids from figures.json
  - parse_deck_ir → write `slides/deck.json`
  - For each slide: HTML → PNG under `slides/`
  - export PPTX/PDF with names `{stem}_slides.pptx`, `{stem}_deck.pdf`
  - Never set report `status` to error on slides failure; set `slides_status=error`

- [ ] **Step 3: Wire API**
  - BackgroundTasks + `asyncio.to_thread` like `_bg_run_pipeline`
  - Fix `_run_result_payload`: keep report pdf/docx by **stem** / known names; add pptx/deck_pdf from `meta.slides_artifacts` or explicit filenames
  - pptx media type: `application/vnd.openxmlformats-officedocument.presentationml.presentation`

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** (if asked) `feat(slides): async slides job and API`

---

### Task 5: Liber UI — Export + CTA + tab + fullscreen

**Files:**
- Modify: `web/src/liberTypes.ts`, `ExportMenu.tsx`, `ArtifactCard.tsx`, `ArtifactRail.tsx`, `App.tsx`, `styles.css`
- Create: `web/src/PresentationPane.tsx`, `web/src/PresentationFullscreen.tsx`

**Interfaces:**
- Consumes: poll `slides_status` / `slides_stage` on existing status endpoint; `POST /api/runs/{id}/slides`
- Produces: UI states idle | running | ok | error; tab gated on ok|running

- [ ] **Step 1: Types** — `downloads.pptx?`, `downloads.deck_pdf?`; `slidesStatus`, optional `deck` IR on result

- [ ] **Step 2: ExportMenu** — labels «PDF отчёта», «DOCX», «PPTX», «PDF презентации»; hide missing

- [ ] **Step 3: ArtifactCard CTA** — «Сделать презентацию» when report ok and slides idle; disabled/spinner when running

- [ ] **Step 4: App** — handler posts slides; continue poll; merge downloads; on ok set tab presentation optional via user click (or open tab once without stealing initial report open)

- [ ] **Step 5: PresentationPane** — render slides from IR (or PNG urls if exposed); ←/→; open fullscreen

- [ ] **Step 6: PresentationFullscreen** — clone DiagramFullscreen Esc/portal patterns; 16:9 stage

- [ ] **Step 7: ArtifactRail** — conditional tab «Презентация»

- [ ] **Step 8: `npm run build` + manual smoke checklist

- [ ] **Step 9: Commit** (if asked) `feat(liber): presentation tab, CTA, and export labels`

---

### Task 6: Visual QA matrix + docs ship

**Files:**
- Modify: `docs/knowledge/parked-pptx.md` → shipped
- Create: `docs/adr/0008-liber-deck-image-pptx.md`
- Create: `.agents/knowledge/KI-liber-deck.md`
- Modify: `docs/MEMORY.md` if needed
- Update spec status → `approved / implemented` when done

- [ ] **Step 1: Run ≥1 real desk fixture** (existing Source under `runs/` or gold notes): generate slides; open PPTX + deck PDF on target OS

- [ ] **Step 2: Eyeball PNGs** against anti-slop checklist in spec

- [ ] **Step 3: Write ADR + KI** (entrypoints, invariants, gotchas: Playwright contention, download keys)

- [ ] **Step 4: Mark parked-pptx shipped**; point to ADR/KI

- [ ] **Step 5: Commit** (if asked) `docs(slides): ADR-0008 and KI for Liber deck`

---

## Execution note

Prefer **subagent-driven-development**: one task per subagent with fresh review after Tasks 1–2 (IR/export) and after Task 4 (API) before UI. Do not start Task 5 until API returns real `pptx`/`deck_pdf` on a local run or fixture.

**Verification before «готово»:** use verification-before-completion — pytest slides suite green + `npm run build` + one manual PPTX open.
