# KI: Liber UI

## What
Vite React soft-premium chat desk: sidebar + compose → poll run → compact chat card + **Artifact rail** (Preview · PDF · Source).

## Entry
- `web/src/App.tsx` — shell orchestration, submit FormData, `activeArtifact`, messages
- `Sidebar.tsx` — New / History (sessionStorage) / Settings; collapse
- `EmptyState.tsx` — hero + ≤3 prompts
- `ThinkingBar.tsx` — stage timer above composer
- `icons.tsx` — stroke icon set (no emoji chrome)
- `ChartCard.tsx` — optional insight/highlights around chart figures
- `reportHistory.ts` — local history + last-run payloads
- `ArtifactRail.tsx` — sidecar: tabs, Export, resize, TOC, figure→PDF, SourcePane
- `ArtifactCard.tsx` / `ContextPlaque.tsx` / `ExportMenu.tsx` / `PdfThumb.tsx`
- `SettingsModal.tsx` — palette, types, limits, dry-run
- `ReportView.tsx` — TeX blocks + edit; ChartCard wraps charts
- `PipelineFlow.tsx` — stage animation while pending

## Invariants
- Proxy `/api` → `:8000` (vite)
- Chart type badge not shown in caption (title= only)
- Full report/PDF live in Artifact rail; chat keeps short status + card
- Export ▾ = PDF / DOCX (not sticky footer downloads)
- `sessionStorage` last report + history list → opens rail
- Attach `.txt/.md` or intent >400 chars → plaque + Source tab
- Rail width persisted in `localStorage` key `liber-rail-width` (dblclick reset)
- Soft-green tokens in `styles.css`; PDF = print truth (rail hint)

## Gotchas
- Preview blocks may still drop lists/emphasis (roadmap C1/C2)
- Chat Source without file = Intent text
- pdfjs chunk lazy-loaded — need `npm install` after pull
- Figure→PDF uses TeX `pdfPage` hint (`estimate_figure_pdf_pages`) then figureIndex
- Live Chart.js in Preview + edit sheet (`LiveChart` / `GET…/charts/{id}` + `POST…/preview`); PDF remains print truth
- After chart Apply, `ChartLivePane` must refetch on URL `?v=` bust (stale HTML otherwise)
- Live frame CSS mirrors `chart_frame.html` (donut legend / KPI); no CSS `scale` (breaks hover hit-testing)
- User bubble: collapsed Intent + `chips[]` (C6); long text still opens Source
- Global `editingFigureId` locks all edit buttons
- History payloads are session-only; refresh keeps them until tab close
- `web/public/vendor/chart.umd.min.js` required for live iframes (Vite static)

## See
ADR-0003 · ADR-0006 · `docs/superpowers/specs/2026-10-21-liber-soft-premium-ui-design.md`
