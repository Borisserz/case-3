# Plan: Template botanical bar + PNG previews

> **For agent:** execute task-by-task. Spec: `docs/superpowers/specs/2026-10-22-liber-template-parity-botanical-bar-design.md`

**Goal:** All packs ≥ wine/botanical craft; gallery = real 6-slide PNGs.

**Files:**
- `web/public/deck/previews/{structure}/01–06.png`
- `web/src/DeckTemplateGallery.tsx` + `deckTemplatePreviews.ts`
- `src/case3/deck_themes/{board,signal,atelier}.json`
- `src/case3/slides_pptx_native.py` / `slides_html.py` (foil/bg generalization)
- `prompt/themes/slides_{board,signal,atelier}.md`

## Tasks

### Task 1: Seed botanical PNG strip
Copy `runs/atelier_visual/botanical_smoke/slides/slide_{01..06}.png` → `web/public/deck/previews/launch/` (and `botanical` alias if needed). Wire gallery to `<img>` when files exist.

### Task 2: Gallery PNG-first modal
`previewSlidesFor` returns `{png?: string}[]` or parallel map; modal/thumb use PNG; CSS fallback for missing packs.

### Task 3: Motif + table fill for board/signal
Add `motif` + `table.body_fill` mirroring botanical density (no fern required yet — panels + foil + dark/light atmosphere).

### Task 4: Generalize foil/card chrome
Replace `pack == "botanical"` gates with motif flags (`foil_cards`, `texture`, `hero_bleed`).

### Task 5: Enrich board/signal prompts
Mirror botanical overlay: media on title, card_row + gate, ≥1 table.

### Task 6: Verify
Browser: launch preview = real PNGs. Optional smoke board pack later.
