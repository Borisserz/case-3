# Liber Deck Julius Parity — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring Liber presentations to Julius-level quality (editable PPTX + twin preview + style UX + templates).

**Architecture:** Theme Pack resolver → ThemeTokens → HTML/PPTX/React twin; report path untouched. PPTX = visual truth.

**Tech Stack:** Python (`deck_theme`, `slides_*`), FastAPI, React/Vite, python-pptx, Playwright capture.

**Spec:** [`../specs/2026-10-22-liber-deck-julius-parity-design.md`](../specs/2026-10-22-liber-deck-julius-parity-design.md)

---

## File map

| File | Responsibility |
|------|----------------|
| `src/case3/deck_theme.py` | resolve packs + overrides → ThemeTokens |
| `src/case3/deck_themes/*.json` | atelier / board / signal / relay |
| `src/case3/slides_job.py` | wire theme; persist `deck.style` |
| `src/case3/slides_html.py` + `templates/slide_frame.html` | CSS vars from tokens |
| `src/case3/slides_pptx_native.py` | fonts/colors from tokens |
| `src/case3/slides_pptx_charts.py` | native OOXML charts (phase 2) |
| `src/case3/slides_pptx_tables.py` | native tables (phase 3) |
| `src/case3/slides_chart_data.py` | extract series from chart HTML (phase 2) |
| `src/case3/slides_ir.py` | section/scorecard/callout + fields (phase 3) |
| `prompt/system_slides.md` + `prompt/themes/slides_*.md` | narrative overlays |
| `src/case3/api.py` | slides POST body theme/style |
| `web/src/deckStyle.ts` | types + localStorage |
| `web/src/DeckStyleSheet.tsx` | colors/fonts/preview |
| `web/src/DeckMakeSplit.tsx` | split CTA |
| `web/src/ArtifactCard.tsx` / `PresentationPane.tsx` / `App.tsx` | wire UI |
| `docs/adr/0008-…` | amend visual truth |
| `tests/test_deck_theme.py` | resolve + twin hex |

---

### Task 0: Docs lock (ADR + KI)

**Files:** `docs/adr/0008-liber-deck-image-pptx.md`, `.agents/knowledge/KI-liber-deck.md`, `docs/MEMORY.md`

- [ ] Amend ADR-0008: PPTX visual truth; preview twins tokens
- [ ] KI: theme packs + style API fields
- [ ] MEMORY link to this plan/spec

### Task 1: `deck_theme` module (TDD)

**Files:** `src/case3/deck_theme.py`, `src/case3/deck_themes/atelier.json`, `board.json`, `tests/test_deck_theme.py`

- [ ] RED: resolve unknown pack → atelier; override accent
- [ ] GREEN: implement resolve + JSON load
- [ ] Tokens include colors + fonts.fallback_pptx

### Task 2: Wire tokens into HTML + PPTX render

**Files:** `slides_job.py`, `slides_html.py`, `slide_frame.html`, `slides_pptx_native.py`

- [ ] Job resolves theme before render; writes `deck["style"]`
- [ ] HTML chrome uses `--deck-*` from tokens
- [ ] PPTX `_palette` / font from tokens
- [ ] Smoke: rebuild existing run with `board` pack

### Task 3: API + meta

**Files:** `api.py`, `liberTypes.ts`

- [ ] POST `/slides` accepts `{ theme_pack, style_settings }`
- [ ] Persist `meta.slides_style`
- [ ] GET status/slides returns style echo

### Task 4: Style sheet UI (frontend)

**Files:** `deckStyle.ts`, `DeckStyleSheet.tsx`, `DeckStylePreview.tsx`, `DeckMakeSplit.tsx`, `ArtifactCard.tsx`, `PresentationPane.tsx`, `App.tsx`, `styles.css`

- [ ] Split CTA + sheet (4 colors, 2 fonts, live CSS preview)
- [ ] localStorage `liber.deckStyle.v1`
- [ ] Pass style into POST slides
- [ ] Manual: open sheet → change accent → generate → PPTX reflects

### Task 5: Native charts (phase 2)

**Files:** `slides_chart_data.py`, `slides_pptx_charts.py`, `slides_pptx_native.py`, tests

- [ ] Extract series from figures.json HTML
- [ ] Native chart for whitelist types; else PNG
- [ ] Visual QA vs Northstar growth slide

### Task 6: IR + tables + overlays (phase 3)

**Files:** `slides_ir.py`, `system_slides.md`, `prompt/themes/*`, `slides_pptx_tables.py`, `slides_html.py`

- [ ] Layouts section/scorecard/callout + chapter/takeaway/appendix
- [ ] Theme overlays board/signal
- [ ] Native tables
- [ ] Golden IR fixtures

### Task 7: Pack parity + gallery + eval (phase 4)

**Files:** `deck_themes/signal.json`, `relay.json`, gallery UI, `tests/fixtures/deck_gold/`

- [ ] signal + relay packs
- [ ] Template gallery + “make like this” (applies pack)
- [ ] Live eval harness optional
- [ ] Blind QA vs 3 Julius refs until bar met

---

## Execution order

Do Tasks 0→4 first (shippable skin + UX). Then 5→7 with visual loops against Downloads refs. No artificial deadline — iterate until parity checklist in the spec is green.
