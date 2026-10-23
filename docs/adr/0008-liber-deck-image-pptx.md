# ADR-0008: Liber deck — capture preview + native editable PPTX

**Status:** Accepted (2026-10-22), **amended** 2026-10-22 (Julius parity)  
**Spec:** `docs/superpowers/specs/2026-10-22-liber-pptx-deck-design.md` · media: `2026-10-22-liber-deck-media-live-design.md` · parity: `2026-10-22-liber-deck-julius-parity-design.md`

## Context

Need an on-demand executive presentation alongside PDF/DOCX. Users must **edit the PPTX in PowerPoint by hand**. Target quality bar: Julius-class decks (Northstar / Bold Signal refs) — native charts/tables, theme packs, twin preview.

## Decision

1. Separate async job `POST /api/runs/{id}/slides` (optional body: `theme_pack`, `style_settings`).
2. Qwen fills deck IR (`slides/deck.json`); Source-bound numbers; layouts include chart/media (+ later section/scorecard/callout).
3. **Theme packs** (`deck_theme`) resolve → `ThemeTokens` frozen into `deck.json.style`. Deck-only — does **not** change report `chart_palette` / PDF/DOCX.
4. **PPTX = visual truth:** native editable shapes/text via `python-pptx`; progress toward native OOXML charts/tables (PNG charts are fallback only). Image-only PPTX is not the product artifact. **Dark Botanical** pack may set a full-slide photo as OOXML slide background (`hero_bleed` + `media_id`) — Julius VESPER path.
5. **Liber preview:** Live HTML twin from IR (editable) + HTML 1920×1080 capture for filmstrip **twins the same tokens**. Pixel-perfect Office AA is not required for the web twin.
6. **`deck_pdf` (Julius path):** LibreOffice headless converts the **native PPTX** → PDF (`slides_lo.write_deck_pdf`). If `soffice` is missing/fails → PNG stitch fallback (`build_deck_pdf`). Mode stored in `slides_artifacts.deck_pdf_mode` (`lo` | `png_stitch`). Never overwrite report `pdf`.
7. Liber rail tab «Презентация» + Export: `pptx` + `deck_pdf`.
8. **Web edit (v1):** `PATCH /slides/ir` text-only → rebuild PPTX + twin PNGs + deck PDF. No add/delete shapes or slides.

## Consequences

- Preview and PPTX share `ThemeTokens`; divergence is a bug.
- Playwright still needed for filmstrip twin PNGs and Mermaid rasterization; deck PDF prefers LibreOffice.
- Report Chart.js path stays isolated from deck OOXML charts.
- Desk/Windows: install LibreOffice or set `CASE3_SOFFICE` / `LIBREOFFICE_PATH` for LO PDF.
