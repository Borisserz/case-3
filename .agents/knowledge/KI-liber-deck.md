# KI: Liber presentation deck

## Entry points

- API: `POST /api/runs/{id}/slides`, `GET …/slides`, `PATCH …/slides/ir`, `GET …/slides/png|media/{name}`
- Job: `src/case3/slides_job.py` (`rebuild_slides_from_deck` after edit)
- IR: `src/case3/slides_ir.py` + `slides_patch.py` (text-only) + `prompt/system_slides.md`
- Capture: `slides_html.py` / `slides_render.py` / `templates/slide_frame.html`
- Export: `slides_pptx_native.py` (editable PPTX) + `slides_lo.py` (LO PPTX→PDF, Julius) + `slides_export.build_deck_pdf` (PNG fallback)
- UI: `PresentationPane.tsx` + `DeckCanvas.tsx` (live twin, Edit mode), `ExportMenu.tsx`

## Invariants

- Not part of `formats` / Docker TeX.
- Layouts: `title` | `section` | `kpi_row` | `scorecard` | `card_row` | `chart_hero` | `chart_split` | `media_hero` | `media_split` | `table_hero` | `callout` | `bullets` | `closing`. Cross-fields: `chapter?`, `takeaway?`.
- Prompt: `system_slides.md` + `prompt/themes/slides_{pack}.md` overlays; prefer 10–12 slides.
- Media ids only from run: `cht_*` PNG, `fig_*`/`usr_*` PNG, `dia_*` Mermaid→PNG (`slides_media.py`).
- Numbers ⊆ Source (optional `allowed_number_strings`).
- Downloads: `pptx` (native editable) + `deck_pdf` (LO-convert PPTX; PNG stitch fallback); report `pdf` untouched.
- `slides_artifacts.deck_pdf_mode`: `lo` | `png_stitch`. Env: `CASE3_SOFFICE` / `LIBREOFFICE_PATH`.
- **PPTX = visual truth**; Liber preview twins `ThemeTokens` from `deck_theme` (ADR-0008 amended). Deck style ≠ report palette.
- Soft-fail: `slides_status=error` does not flip report `status`.

## Theme / style

- Packs (visual): `atelier` / `board` / `signal` / `relay` / **`botanical`**.
- **Structures (arc):** `board_update` / `investor` / `qbr` / `performance` / `launch` / `survey` / `campaign` / `workshop` — Julius DNA from live PPTX refs; `POST /slides` `structure_id` + `prompt/themes/structure_*.md`.
- Botanical motif: `atmosphere: dark`, `hero_bleed: true` — title/closing full-bleed `media_id` (OOXML bg + HTML veil). Non-hero slides: fern texture `deck_themes/botanical_bg.png` as OOXML slide bg + HTML/CSS twin.
- `card_row`: 3 narrative cards (`kicker`/`title`/`body`) + optional gold gate `caption` (Julius VALIDATION GATE).
- UI: split CTA → `DeckStyleSheet`; `localStorage liber.deckStyle.v1`.
- Empty presentation mode: pack chips + `DeckTemplateGallery` (8 Julius-mapped cards, Light/Dark filter, Use → pack + chat).
- Present: click-advance + idle chrome; generating: IR→Media→Twin→PPTX steps.
- Twin fonts: `--deck-font-title/body` from IR; PPTX title/body via `_PPTX_TITLE_FONT` / `_PPTX_FONT`.
- Presentation UX: Preview → Slide (not Edit); Space only in Present; save errors surfaced.
- Export shows `deck_pdf_mode` (`lo` | `png_stitch`) on deck PDF item.
- Chat: `DeckFileCard` PPTX/PDF with slide preview + Export/Edit|View (Julius).
- Rail Export → `DeckExportSheet` (preview + download PPTX/PDF).
- API: `POST …/slides` may send `theme_pack` + `style_settings` → `meta.slides_style`.
- Roadmap: [`docs/superpowers/specs/2026-10-22-julius-live-ux-parity-design.md`](../../docs/superpowers/specs/2026-10-22-julius-live-ux-parity-design.md).

## Gotchas

- Slides job starts on a **daemon thread** (`_kick_slides_thread`); meta flips to `running`/`starting` before kick. Crash → `slides_error` (never leave forever-`queued`).
- Capture must use home Playwright browsers if sandbox `PLAYWRIGHT_BROWSERS_PATH` is broken.
- Mermaid needs `web/node_modules/mermaid/dist/mermaid.min.js` (npm install in web/).
- Do not screenshot the Vite rail — fixed static HTML only.
- Stem artifacts: `{stem}_slides.pptx`, `{stem}_deck.pdf`.
- **Split Pastel twin:** `motif.panels` rotate by `slide_index` (section/title/callout). Scorecard cards use panels `0..n` (distinct). Pass `slide_index` into HTML render + DeckCanvas.
- **Title hero KPIs:** `parse_hero_metrics(takeaway)` → stacked value/label on pastel panel (Julius). Prompt relay: newlines or `VALUE — label · …`.
- **deck_pdf:** LO-convert native PPTX (`slides_lo`); fallback PNG stitch. Env `CASE3_SOFFICE`.
