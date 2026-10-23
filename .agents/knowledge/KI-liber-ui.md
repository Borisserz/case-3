# KI: Liber UI

## What
Vite React soft-premium chat desk: sidebar + compose → poll run → compact chat card + **Artifact rail** (Preview · PDF · Схема · Source).

## Entry
- `web/src/App.tsx` — thin shell: state + `send`/`edit*` + rail wiring (≈1.3k lines after 2026-10-21 split)
- `liberTypes.ts` / `liberConstants.ts` / `liberRunHelpers.ts` — shared types, defaults, pure run helpers (C8 error format, SSE summary, stage labels)
- `ChatMessages.tsx` / `ChatComposer.tsx` / `ComposerPhotoChips.tsx` — transcript + composer UI
- `useLiberDevPreviews.ts` — `?preview=artifact|flow` bootstraps
- `Sidebar.tsx` — New / History (sessionStorage) / Settings; collapse
- `EmptyState.tsx` — «Чем займёмся?»; empty desk uses `is-empty-home` (composer centered mid-viewport like Julius)
- `liberModes.ts` + `ChatComposer` pills: Отчёт · Схема · Презентация — **остаются** после первого сообщения; gallery только empty∧presentation; стиль → `DeckStyleSheet`
- Template apply: **только** pack+structure (не DNA-промпт в чат); honesty «пример · 6 кадров / 10–12 в деке»; presentation send требует Source или brief ≥48 символов
- `output_mode=presentation` → `formats=none` (без PDF/DOCX) + после run сразу `makePresentation`; rail **не** авто-открывается — Julius large `DeckFileCard`s in-chat; rail only on card click
- Composer modes diagram/report: likewise no auto-open rail after finish (click ArtifactCard)
- Julius in-chat cards (2026-10-23): matte paper stage + file glyph + hover veil + footer «→»; deck = PPTX+PDF twin (+ filmstrip); report = A4 sheet; diagram = sketch hero; `DeckMakeSplit quiet` under cards; empty hero = Crimson serif + segmented mode track; `?preview=deck` QA; history/restore **не** auto-open rail
- Deck gen (2026-10-23): `makePresentation` **closes rail**, keeps progress in chat (`DeckBuildCard` + thinking); presentation tab only when `ok`/`error`; `thinkingMode` pools in `pipelinePhrases.ts` (report/diagram/presentation + slides_*)
- Julius strip (2026-10-23): composer `Working · m:ss` on **any** busy run (report/diagram/deck); chat column sticky head from `preview.title` (`provisionalSessionTitle` → `reportTitle`); sidebar brand unchanged
- Empty-home centering (2026-10-23): report/diagram = `is-starters-home` @ `composer-max`; presentation = `is-deck-home` @ `--deck-stage-max` — composer sheet **same width** as template grid (`max-width:100%`, no 40rem cap); rail-open chat column centered
- `ThinkingFold.tsx` + `pipelinePhrases.ts` — collapsible «Размышления» in bot bubble (Flow above); no ThinkingBar; phrases from large pools, seeded per run (`thinkingStartedAt`) so logs don’t repeat the same sequence
- `icons.tsx` — stroke icon set (no emoji chrome)
- `ChartCard.tsx` — optional insight/highlights around chart figures
- `reportHistory.ts` — local history + last-run payloads
- `ArtifactRail.tsx` — sidecar: tabs (Превью·PDF·Схема·Source), Export, resize, TOC, figure→PDF, SourcePane
- `DiagramPane.tsx` / `MermaidView.tsx` / `DiagramFullscreen.tsx` / `downloadDiagramPng.ts` — UI-only Mermaid (tab «Схема»)
- `ArtifactCard.tsx` / `ContextPlaque.tsx` / `ExportMenu.tsx` / `PdfThumb.tsx`
- `SettingsModal.tsx` — palette, types, limits, dry-run
- `ReportView.tsx` — TeX blocks + edit; ChartCard wraps charts
- `PipelineFlow.tsx` — stage animation while pending

## Invariants
- Proxy `/api` → `:8000` (vite)
- Chart type badge not shown in caption (title= only)
- Full report/PDF live in Artifact rail; chat shows streamed LLM **chat summary** (prose) + card — not bare «Отчёт готов»
- Summary SSE: `GET /api/runs/{id}/summary/stream` while stage `latex`/`docx`; light markdown via `lightMd.tsx`
- Export ▾ = PDF / DOCX (not sticky footer downloads)
- `sessionStorage` last report + history list → opens rail
- Attach `.txt/.md` or intent >400 chars → `ContextPlaque` (Source + MD/TXT/Текст badge, kind glyph) + Source tab
- Deck build: `ThinkingFold` auto-opens with `live` + «Собираю презентацию» while `slides_*` / slides_status running|queued; `DeckBuildCard` under ArtifactCard; QA `?preview=deck-busy`
- `PdfThumb`: skeleton+shimmer while pdf.js loads (not empty “PDF” stub)
- Rail width persisted in `localStorage` key `liber-rail-width` (dblclick reset)
- Close rail: keep `activeArtifact` until width→0 (`railExiting` + `onClosed`); don’t null early (snaps user bubble). Guard `onAnimationComplete` until width &lt; 32px.
- Soft-green tokens in `web/src/styles/tokens.css` (split: shell/chat/composer/deck/rail/presentation/modals); PDF = print truth (rail hint)
- Premium UI refactor 2026-10-22: empty-home desk scrolls; composer send right; deck style only via `DeckStyleSheet`; template gallery Julius-stage mocks; `useFocusTrap` on modals/FS
- Template preview 2026-10-22: modal = **6-slide vertical scroll**; **PNG-first** Liber twins only (`scripts/render_template_previews.py` → `web/public/deck/previews/{structureId}/01–06.png`); Julius refs = style DNA, not gallery screenshots; CSS mock = fallback
- Craft floor = botanical (wine): board/signal/atelier now have `motif.foil_cards` + `panels` + `table.body_fill` (`deck_theme` passes through); foil chrome via `_foil_cards()` not botanical-only
- Specs: `2026-10-22-liber-template-preview-6slides-design.md` · `2026-10-22-liber-template-parity-botanical-bar-design.md`
- Spec/plan: `docs/superpowers/specs/2026-10-22-liber-premium-ui-refactor-design.md` · `docs/superpowers/plans/2026-10-22-liber-premium-ui-refactor.md`
- Diagrams are Liber-only (`RunResult.diagrams`); never TeX-injected; Settings «Схемы» 0–3; client PNG download
- Composer mode **Схема** → `output_mode=diagram` + `formats=none` (no PDF/DOCX); rail opens «Схема» + chat summary as short description
- Spec: `docs/superpowers/specs/2026-10-22-liber-composer-modes-design.md`
- Focused workbench: rail default ~62%; card has no Export (rail only); Presentation CTA primary — `docs/superpowers/specs/2026-10-22-liber-focused-workbench-design.md`
- Schema tab: hint «Только в Liber»; zoom ± / % / Ctrl+wheel + pan; PNG via viewBox + slug(title); fullscreen has own SVG ref

## Gotchas
- C8: run error bubble may include `график …` / `TeX: …` from status `failed_charts` + `latex_log_tail`
- Chart type chip hover: portal card `pointer-events:auto` + delayed hide; unknown typeId → GlyphBar fallback (G1)
- Edit sheet palette seeds from `block.palette` then Settings default (G2)
- Chat Source without file = Intent text
- pdfjs chunk lazy-loaded — need `npm install` after pull
- Figure→PDF: **pdf.js text search** by caption (TeX `pdfPage` hints omit natural breaks → badge no longer shows «с.N»; jump must not seed page=1 or it clobbers find)
- Donut print canvas forced square in `enhance_donut_html` (LLM 1100×560 → oval)
- Image edit sheet: no second preview body (figure above stays source of truth); chat summary kept on Apply
- Live Chart.js in Preview + edit sheet (`LiveChart` inline mount — no iframe / `GET…/charts/{id}` + `POST…/preview`); PDF remains print truth. Blur root cause was iframe fractional-px compositor layer, not Chart DPR alone. Retina live DPR → 3. QA all types: `?preview=charts-qa` + `web/public/qa-chart-fixtures.json`.
- After chart Apply, `ChartLivePane` must refetch on URL `?v=` bust (stale HTML otherwise)
- Live frame CSS mirrors `chart_frame.html` (donut legend / KPI); no CSS `scale` (breaks hover hit-testing)
- Live donut canvas must stay **in-flow** (not `absolute; inset:0`) — stretch inverted arc hit-tests; doughnut interaction = `nearest`+`intersect`; `.live-chart` overflow visible so center tooltips show
- User bubble: collapsed Intent + `chips[]` (C6); long text still opens Source
- Global `editingFigureId` locks all edit buttons
- History payloads are session-only; refresh keeps them until tab close
- `web/public/vendor/chart.umd.min.js` required for live iframes (Vite static)

## See
ADR-0003 · ADR-0006 · `docs/superpowers/specs/2026-10-21-liber-soft-premium-ui-design.md`
