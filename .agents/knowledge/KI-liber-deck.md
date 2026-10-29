# KI: Liber presentation deck

## Entry points

- API: `POST /api/runs/{id}/slides`, `GET …/slides`, `PATCH …/slides/ir` (text), `POST …/slides/structure` (reorder|duplicate|delete → IR + rebuild twin/PPTX, no LLM), `POST …/cancel`, `GET …/slides/png|media/{name}`
- Job: `src/case3/slides_job.py` (`rebuild_slides_from_deck` after edit/structure)
- Structure: `slides_patch.apply_deck_structure` · UI filmstrip/gallery DnD + Дублировать/Удалить (confirm)
- Cancel: `src/case3/run_cancel.py` — cooperative `cancel_requested` between stages + `LLMClient.complete(cancel_check=…)`
- IR: `src/case3/slides_ir.py` + `slides_patch.py` (text-only) + `prompt/system_slides.md`
- Capture: `slides_html.py` / `slides_render.py` / `templates/slide_frame.html`
- Export: `slides_pptx_native.py` (editable PPTX) + `slides_lo.py` (LO PPTX→PDF, Julius) + `slides_export.build_deck_pdf` (PNG fallback)
- UI: `PresentationPane.tsx` (PPTX twin) + `DeckSlidesFilm.tsx` (PDF vertical film) + `DeckCanvas.tsx` + `DeckFileCard.tsx`

## Invariants

- Not part of `formats` / Docker TeX. Composer **Презентация** → `formats=[]` (no report PDF/DOCX).
- **One presentation, two formats:** PPTX tab = live twin + edit; PDF tab = vertical slide film. Same deck IR.
- **Download contract:** «Скачать» on **both** `DeckFileCard` (chat) **and** rail head (`deck-slides-film-dl` next to slide count). No Export sheet / `is-export` chrome.
- **After slides ok:** pulse cards in chat; **do not** auto-open artifact rail.
- Layouts: `title` | `section` | `kpi_row` | `scorecard` | `card_row` | `chart_hero` | `chart_split` | `media_hero` | `media_split` | `table_hero` | `callout` | `bullets` | `closing`. Cross-fields: `chapter?`, `takeaway?`.
- Prompt: `system_slides.md` + `prompt/themes/slides_{pack}.md` + `structure_{id}.md`; prefer 10–12 slides.
- **Anti-monotony:** ≥5 distinct layouts when ≥8 slides; vary beat 2; cap consecutive scorecards; title takeaway hero KPIs on split packs.
- **Premium twin craft:** `card_row` leading `%` → `narr-meter` (HTML+PPTX); chart caption=`caption--insight`; closing `takeaway` → `closing-hero`; grain on `signal`/`ink`/`voltage`/`botanical`; pack charts via `scripts/archive/render_premium_gallery_charts.py`.
- Media ids only from run: `cht_*` PNG, `fig_*`/`usr_*` PNG, `dia_*` Mermaid→PNG (`slides_media.py`).
- Numbers ⊆ Source. Whole-token match; spaced thousands `9 330` ≡ `9330`.
- **Freeform (no `structure_id`):** `slides_beat_planner.plan_beats` → skeleton. Live QA: `scripts/archive/run_freeform_slides_live.py`.
- **Number heal:** `scrub_invented_numbers` on IR reject. Meta: `slides_number_scrub=true`.
- **Chrome nums:** zero-padded `01`…`099` and bare `1`…`12` allowed without Source (kickers / deck indices). Multi-digit facts still gated.
- **Single kick:** UI must not `POST /slides` twice (SSE `pipeline_ok` + `makePresentation`). `slidesJobNeedsKick` / in-flight → attach only.
- **LLM 402 credit clamp:** `llm_client` re-clamps `afford` max_tokens (up to 4 shrinks).
- Downloads: `pptx` + `deck_pdf` (`deck_pdf_mode`: `lo` | `png_stitch`). Report `pdf` untouched.
- **PPTX = visual truth**; Liber twin ≈ tokens (ADR-0008). Deck style ≠ report palette.
- Soft-fail: `slides_status=error|cancelled` does not flip report `status`.
- **Stop:** UI shows «Останавливаю…» until meta `cancelled` (or timeout); `POST /cancel` sets `cancel_requested`. Checkpoints: pipeline `bump`, LLM `cancel_check`, slides `_set_slides` / render / pptx / PDF. `PresentationPane` has explicit `cancelled` state (not error).

## Theme / style

- Packs: `atelier` · `board` · `signal` · `relay` · `ink` · `voltage` · `studio` · `botanical`.
- Structures: eight unique pairs (board_update/board … workshop/studio).
- UI: `DeckStyleSheet` + `DeckTemplateGallery`; `localStorage liber.deckStyle.v1`.
- Presentation UX: Preview → Slide → Edit; Present = click-advance + idle chrome hide + Space/←/→; Esc exits; concurrent IR PATCH coalesces (no 409).
- API: `POST …/slides` may send `theme_pack` + `style_settings` → `meta.slides_style`.
- Roadmap: [`docs/superpowers/specs/2026-10-22-julius-live-ux-parity-design.md`](../../docs/superpowers/specs/2026-10-22-julius-live-ux-parity-design.md).

## Fonts (PPTX)

- Roles: `fonts.title` → title runs; `fonts.body` → body (then `fallback_pptx` only if body missing).
- Liber/web faces map in `slides_pptx_native._office_font_name`: Liber Serif/Fraunces/… → Georgia; Liber Sans/Inter/… → Calibri; Aptos Display → Aptos.
- Twin HTML may still use woff2; PPTX must not look “all Calibri” when pack declares serif titles (atelier/botanical → Georgia titles).

## Native charts (PPTX)

- Every deck slide with eligible `cht_*` embeds OOXML (`ppt/charts/…`); Liber twin stays PNG.
- Series IR on `figures.json` charts (`series` field) via `attach_series_ir`; PPTX prefers it over HTML regex (`slides_chart_data`).
- Whitelist: bar / grouped_bar / stacked_bar / horizontal_bar / line / area / donut. KPI/scatter → PNG.
- Colors from pack `chart_series` (per-point for single-series bar/donut).
- Every eligible `cht_*` in run must appear in deck: `ensure_deck_charts` injects missing `chart_hero`s (meta `slides_chart_injected` = list of ids).
- Twin recolor: pack `chart_series` + per-category colors for single-series bar/donut (`apply_pack_category_colors_to_html`) so twin ≈ native.
- Donut native: % data labels + series name from caption (not anonymous `Series`).
- Spec: `docs/superpowers/specs/2026-10-26-liber-pptx-native-charts-design.md`.

## Gotchas

- Slides job = **daemon thread**; meta `running`/`starting` before kick. Crash → `slides_error` (never forever-`queued`).
- Report `/api/run` = daemon thread (not BackgroundTasks — Windows stall).
- Capture: home Playwright browsers if sandbox path broken.
- Mermaid: `web/node_modules/mermaid/dist/mermaid.min.js`.
- Stem: `{stem}_slides.pptx`, `{stem}_deck.pdf`.
- **deck_pdf:** LO-convert native PPTX; fallback PNG stitch. Env `CASE3_SOFFICE`.
