# PPTX / Liber presentation deck

**Status:** **implemented (v1)** — image PPTX + deck PDF + Liber tab.  
**Design:** [`docs/superpowers/specs/2026-10-22-liber-pptx-deck-design.md`](../superpowers/specs/2026-10-22-liber-pptx-deck-design.md)  
**ADR:** [`docs/adr/0008-liber-deck-image-pptx.md`](../adr/0008-liber-deck-image-pptx.md)  
**KI:** [`.agents/knowledge/KI-liber-deck.md`](../../.agents/knowledge/KI-liber-deck.md)

## v1 summary

- On-demand `POST /api/runs/{id}/slides` (not every report run).
- Deck IR → Liber static HTML → Playwright PNG → `{stem}_slides.pptx` + `{stem}_deck.pdf`.
- Layouts: title, kpi_row, chart_*, media_* (photos + Mermaid→PNG), bullets, closing; optional `kicker`.
- Live LLM path validated on 10 real `runs/out` (2026-10-22); numbers from Source + chart captions.
- **PPTX is native editable** (`slides_pptx_native.py`); Liber preview = token twin; **deck PDF = LO-convert PPTX** (PNG stitch fallback).
- Extra theme skins / richer native layouts — later.
