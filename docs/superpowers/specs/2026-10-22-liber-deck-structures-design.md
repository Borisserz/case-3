# Liber deck structures (Julius DNA) — design

**Date:** 2026-10-22  
**Status:** shipped (v1 overlays + API)  
**Refs (local copies under `runs/julius_ref/`, not committed):**

| File | Structure |
|------|-----------|
| `Northstar_Q3_2026_Board_Update.pptx` | board_update |
| `Relay_Q3_2026_Investor_Update.pptx` | investor |
| `marketing_qbr_split_pastel.pptx` | qbr |
| `marketing_performance_bold_signal.pptx` | performance |
| `VESPER_Dark_Botanical_Launch.pptx` | launch |

## Split

- **Pack** (`atelier` / `board` / `signal` / `relay` / `botanical`) = colors, fonts, motif.
- **Structure** (`board_update` / `investor` / …) = slide **arc** + layout bias (not just swatches).

## Plumbing

- JSON: `src/case3/deck_structures/*.json`
- Prompt: `prompt/themes/structure_*.md` → `{{STRUCTURE_OVERLAY}}`
- API: `POST /slides` body `structure_id`; `GET /deck-themes` → `structures[]`
- UI: template cards set `deckStyle.structureId` + pack + prompt

## Non-goals

- Cloning Julius freeform shape editor
- Shipping their binary PPTX as Liber skins (copyright / brand)
- 100+ seasonal junk templates
