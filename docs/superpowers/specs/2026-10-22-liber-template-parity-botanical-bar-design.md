# Liber templates → botanical bar (≥5/10) + real previews

**Date:** 2026-10-22  
**Status:** approved direction (user: preview + generated PPTX; wine/botanical = floor)

## Verdict

Yes. Julius PPTX alone is not enough — they are **recipes**. Floor = Dark Botanical (wine bottle). Two tracks:

1. **Gallery preview** — real Liber twin PNGs (6 frames), not CSS wireframes  
2. **Generated PPTX** — every pack gets botanical-class motif (texture/bleed/foil/table fills/prompt density)

## Why wine is 5/10 and others ~3/10

Botanical alone ships: fern `botanical_bg.png`, `hero_bleed`, foil cards, dark `body_fill`, rich `slides_botanical.md`. Board/signal are flat tokens.

## Approach (chosen)

- **Preview assets:** `web/public/deck/previews/{structureId}/01.png…06.png` = **Liber Playwright twins only** (`scripts/render_template_previews.py`). Julius PPTX = style DNA for packs/IR — **never** ship Julius screenshots in the gallery.
- **Craft lift:** motif blocks + `body_fill` on board/signal/atelier; generalize foil/chrome off botanical-only `if pack ==`; enrich `slides_board.md` / `slides_signal.md`.
- **Not:** clone Julius purple; ship Julius PPTX as Liber output.

## Success

- Modal scroll shows photographic/rendered slides for botanical/launch (≥ smoke quality)
- Board/Signal generated title+cards visibly denser than flat white/black sheet
- User rating floor ~5/10 across packs on a known Source
