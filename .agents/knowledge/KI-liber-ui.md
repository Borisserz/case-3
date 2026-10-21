# KI: Liber UI

## What
Vite React soft-premium chat desk: sidebar + compose → poll run → compact chat card + **Artifact rail** (Preview · PDF · Схема · Source).

## Entry
- `web/src/App.tsx` — thin shell: state + `send`/`edit*` + rail wiring (≈1.3k lines after 2026-10-21 split)
- `liberTypes.ts` / `liberConstants.ts` / `liberRunHelpers.ts` — shared types, defaults, pure run helpers (C8 error format, SSE summary, stage labels)
- `ChatMessages.tsx` / `ChatComposer.tsx` / `ComposerPhotoChips.tsx` — transcript + composer UI
- `useLiberDevPreviews.ts` — `?preview=artifact|flow` bootstraps
- `Sidebar.tsx` — New / History (sessionStorage) / Settings; collapse
- `EmptyState.tsx` — hero + ≤3 prompts
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
- Attach `.txt/.md` or intent >400 chars → plaque + Source tab
- Rail width persisted in `localStorage` key `liber-rail-width` (dblclick reset)
- Close rail: keep `activeArtifact` until width→0 (`railExiting` + `onClosed`); don’t null early (snaps user bubble). Guard `onAnimationComplete` until width &lt; 32px.
- Soft-green tokens in `styles.css`; PDF = print truth (rail hint)
- Diagrams are Liber-only (`RunResult.diagrams`); never TeX-injected; Settings «Схемы» 0–3; client PNG download
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
- User bubble: collapsed Intent + `chips[]` (C6); long text still opens Source
- Global `editingFigureId` locks all edit buttons
- History payloads are session-only; refresh keeps them until tab close
- `web/public/vendor/chart.umd.min.js` required for live iframes (Vite static)

## See
ADR-0003 · ADR-0006 · `docs/superpowers/specs/2026-10-21-liber-soft-premium-ui-design.md`
