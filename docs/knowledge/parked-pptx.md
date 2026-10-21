# Parked: PPTX / HTML presentations

**Status:** not in scope until explicitly requested.  
**Discussed:** 2026-10-20.

## Conclusion so far

- Good PPTX ≠ dump TeX into slides. Need **slide JSON** + builder (`python-pptx`) or freeform agent (e.g. PPTAgent).  
- HTML decks (Reveal/Marp) are fine for Liber preview; HTML→PPTX conversion is mediocre.  
- Templates/layout engine still needed for quality; “no templates” ≈ freeform HTML or LLM-written python-pptx (fragile).  
- Existing assets to reuse later: `figures/*.png`, captions, palettes.

## When unparking

Write `docs/superpowers/specs/YYYY-MM-DD-pptx-design.md` first; do not bolt onto `system_tex.md`.
