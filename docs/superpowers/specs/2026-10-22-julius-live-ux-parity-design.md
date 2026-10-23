# Julius live UX → Liber presentation parity

**Date:** 2026-10-22  
**Status:** P0 shipped (2026-10-22) · P1 next  
**Observed:** logged-in Julius at `/chat` (Slides) + `/slides-templates`  
**Brand lock:** Liber olive/Atelier — **not** Julius dark/purple chrome

## Julius screens (live)

### 1. Empty / Slides home (`/chat`, tab Slides)
- Centered H1 «What can I do for you today?»
- Composer center: attach · tools · **palette (Style templates)** · model · send
- Mode chips under composer: Browser · Website · Video · Image · Excel · **Slides** · More
- Below: **template card grid** (Board Update, Performance, QBR, Survey, Investor, Launch…) with expand + «Use prompt»
- Link: Explore all templates → `/slides-templates`

### 2. Presentation style sheet (palette button)
- Modal «Presentation style»
- **Upload PowerPoint template** (.pptx ≤20MB) — reuse layouts/bg/images
- Toggle «Use colors and fonts for new presentations»
- Primary / Accent / Background / Text + Heading/Body fonts
- Live mini preview («Quarterly results»)
- Explicit honesty: *«PowerPoint exports use your selected fonts. In-app previews may show different fonts.»*
- Free plan may lock hex/font edits after toggle

### 3. Template gallery (`/slides-templates`)
- Filters: All / Light / Dark · Sort Most used
- Cards with use-count social proof
- Preview modal: example slide(s) + style label + prompt blurb + **Use this template**

### 4. Generated deck (product knowledge + Liber parity goal)
- Grid preview → click opens **Slide view** (not Edit)
- Edit explicit; Present fullscreen; Export PPTX/PDF
- Inline field edit → rebuild PPTX

## Liber already close
- Centered empty + mode pills + pack presets (Презентация)
- Composer palette → deck colors/fonts
- PresentationPane: Preview | Slide | Edit | Present | Export
- Theme packs + DeckStyleSheet + twin canvas
- Focused workbench rail

## Liber gaps to close (ordered)

| # | Gap | Liber action |
|---|-----|----------------|
| P0 ✅ | Gallery/open defaults to Edit | `editing` default false; gallery → Slide |
| P0 ✅ | Space advances outside Present | Space only in `PresentationFullscreen` |
| P0 ✅ | Fake B/I via execCommand | Removed from `DeckEditToolbar` |
| P0 ✅ | Twin fonts unwired | `--deck-font-*` from `deck.style.fonts` |
| P0 ✅ | PPTX Calibri-only titles | `_PPTX_TITLE_FONT` + body from theme |
| P0 ✅ | Silent save fail | Error pill + dismiss on patch timeout/error |
| P0 ✅ | Honesty copy twin≠Office fonts | `.presentation-font-honesty` under twin |
| P1 ✅ | Template gallery (empty) | `DeckTemplateGallery` under composer when mode=Презентация |
| P0 ✅ | `deck_pdf_mode` in Export | Label LO vs PNG stitch (`ExportMenu` + `GET /slides`) |
| P1 ✅ | Native OOXML charts smoke | `tests/test_slides_pptx_charts.py` asserts `ppt/charts/` |
| P1 | Upload PPTX as style seed | Parked (Julius Chat Settings · Presentation style) |
| P1 ✅ | Present polish | Click-advance + idle chrome (`PresentationFullscreen`) |
| P1 ✅ | Generating steps | IR→Media→Twin→PPTX chips + RU stage labels |
| P1 ✅ | Template grid ×8 | Julius Slides card set mapped to Liber packs |
| P1 ✅ | Style honesty copy | DeckStyleSheet foot = Julius font disclaimer |
| P2 | Dark Julius chrome | Never |

## Agent lock (2026-10-22)

- Design map: Julius Empty→Style→Grid→Slide→Edit→Present→Export; Liber chrome stays Atelier.
- Code map: gallery→Edit was the trust break; fonts/save/view-first closed in P0.
- **Live send run:** [`2026-10-22-julius-live-generation-run.md`](./2026-10-22-julius-live-generation-run.md) — Board Update 12 slides, Working timer, PPTX Edit/Export, takeaway titles.

## Non-goals
- Clone dark UI / purple accents
- 100+ seasonal templates
- Freeform canvas
