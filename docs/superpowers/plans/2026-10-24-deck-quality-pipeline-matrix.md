# Deck Quality Pipeline Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close PPTX↔HTML craft gaps, pack-color live chart PNGs for decks, tighten density + insight prompts, then verify all 8 structure×pack pairs via PNG + native PPTX + deck PDF.

**Architecture:** Premium craft already lives in `slide_frame.html` / gallery. Extend `slides_pptx_native.py` for closing heroes + insight captions; recolor + re-render charts used by a deck inside `_materialize_deck_artifacts` using theme `chart_series`; tighten CSS/prompt; add `scripts/run_structure_matrix8.py` for offline full export QA.

**Tech Stack:** Python, Playwright charts, python-pptx, Pillow PDF stitch / LO PDF, Vite gallery (cache bust if needed).

## Global Constraints

- Numbers ⊆ Source only (no invented KPIs in fixtures beyond gallery twins).
- Chart types whitelist unchanged; pack colors from `ThemeTokens.chart_series`.
- Do not commit `runs/` artifacts; commit code + plan.
- PPTX is download truth; HTML twin should stay aligned.

---

### Task A — PPTX closing hero + chart insight caption

**Files:** `src/case3/slides_pptx_native.py`, tests under local `tests/` if present

- [x] A1. Add `_layout_closing` using `parse_hero_metrics(takeaway)` → large foil value + label + ≤3 bullets (mirror HTML).
- [x] A2. Chart/media caption: use larger ink + accent when caption present (insight, not muted footnote).
- [x] A3. Smoke: build PPTX from a closing slide with `72% — CSAT` and assert shapes exist / open file.

### Task B — Pack-colored live chart PNGs for decks

**Files:** `src/case3/chart_style.py` (or small helper), `src/case3/slides_job.py`, `src/case3/charts.py`

- [x] B1. `apply_hex_series_to_html` — remap onto pack `chart_series`.
- [x] B2. `_recolor_deck_charts` in `_materialize_deck_artifacts` → `slides/charts/`.
- [x] B3. Smoke remap + live signal recolor verified.

### Task C — Density + prompt insights

**Files:** `src/case3/templates/slide_frame.html`, `prompt/system_slides.md`

- [x] C1. Stretch `narr-grid` / metered cards to fill vertical band (less empty bottom).
- [x] C2. Prompt: chart insight caption + closing hero + survey `%` kickers.

### Task D — Structure matrix (8 packs) PNG + PPTX + deck PDF

**Files:** `scripts/run_structure_matrix8.py`

- [x] D1. `scripts/run_structure_matrix8.py` — 8/8 PNG+PPTX+LO PDF.
- [x] D2. `runs/structure_matrix8/summary.json`.
- [x] D3. Visual QA PDF pages (fitz) + live `_materialize` recolor 8/8.

### Task E — Live pipeline pass (optional if VISION works)

- [ ] E1. Pick one rich `runs/out/*` with charts; for each structure_id call `run_slides_job(..., skip_llm_ir=premium_ir)` OR live LLM once per structure.
- [ ] E2. Confirm `*_slides.pptx` + `*_deck.pdf` + `deck_pdf_mode` ok.

### Task F — Full analysis + finish

- [ ] F1. Write short analysis to chat: what improved, remaining gaps.
- [ ] F2. Commit code (not runs/) if user wants; verification-before-completion checklist.

## Verification gates

1. All 8 matrix cases: ≥6 PNGs, PPTX opens, PDF ≥6 pages.
2. Closing PPTX shows hero number when takeaway has `VALUE — label`.
3. Deck chart PNG for dark pack is not white-letterboxed atelier olive.
4. No purple in slide CSS.
