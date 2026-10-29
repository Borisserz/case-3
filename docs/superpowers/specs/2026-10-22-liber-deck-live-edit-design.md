# Liber Deck Live Edit — Design

**Date:** 2026-10-22  
**Status:** approved-by-user-intent (product ideal / Julius parity; edit-existing only)  
**Amends:** ADR-0008, Julius parity design  
**Refs:** `~/Downloads/marketing_qbr_split_pastel.pptx` + `-3.pdf`, Julius Bold Signal / Split Pastel UI screenshots

## Goal

Web presentation surface matches Julius: **live editable twin** of the deck (not PNG-only), edits sync to **native PPTX**, PDF is a **beautiful twin** of the same look. No add/delete shapes or slides in v1.

## Product locks

| Lock | Choice |
|------|--------|
| Visual truth | **PPTX** (native OOXML) |
| Edit source | **`deck.json` IR** — never patch PPTX binary in browser |
| Preview | Live HTML twin from IR + ThemeTokens (same paint as PPTX) |
| Deck PDF | Twin of preview (PNG stitch OK for v1; LO convert of PPTX when available later) |
| v1 mutate | **Edit existing text/cells only** — no insert, no delete, no layout swap |
| Report path | Untouched |

## Architecture

```text
GET  /slides → deck IR + slide_pngs (filmstrip thumbs)
Web DeckCanvas ← render IR (contenteditable regions)
PATCH /slides/ir  { slides: [...] }  → validate → write deck.json
                 → rebuild PPTX (+ optional recapture PNGs)
Export pptx = rebuilt native; deck_pdf = twin
```

## Editable IR fields (v1)

- `title`, `subtitle`, `kicker`, `takeaway`, `body`, `caption`
- `bullets[i]` (string replace only; count fixed)
- `kpis[i].{label,value,hint,delta}`
- `callout` `term` / `definition`
- `rows[r][c]` table cells
- **Out:** media ids, chart series, chapter int, layout, slide count, style hex

## UI (Julius-like) — approach B + persist path 1

- Rail «Презентация»: **live canvas** (not PNG stage) + filmstrip thumbs
- **View-first (Julius lock):** land on Preview grid; gallery click → **Slide** (`editing=false`). Edit only via segment / `E`.
- Floating toolbar: field label + auto-save (no fake B/I — IR is plain text)
- Debounce **PATCH `/slides/ir`** → rebuild **native PPTX** + twin PNGs/PDF (~700ms after edit); save fail → error pill
- Export: PPTX = visual truth; deck PDF = twin (`deck_pdf_mode`: `lo` | `png_stitch`, shown in Export)

## Craft bar (from Split Pastel)

- Split panel backgrounds (cream + pastel) via theme pack `relay` / future `pastel`
- Dense tables, native charts, Aptos→Calibri fallback
- Footer kicker + slide index like Julius

## Non-goals (v1)

- Freeform shape editor / drag resize
- Chat-driven restyle mid-edit (separate)
- OnlyOffice embed
