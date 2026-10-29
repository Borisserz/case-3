# Liber DOCX — native charts (post-pandoc)

**Date:** 2026-10-26  
**Status:** approved (owner: approach post-pandoc replace, bar = every eligible `cht_*`)  
**Depends on:** Series IR (`slides_chart_data`) + pack colors from PPTX native charts work

## Goal

Downloaded `{stem}.docx`: every eligible report chart (`cht_*`) is a **native Word OOXML chart** (`word/charts/…`), pack-colored, editable in Word. KPI / scatter / photos / Mermaid stay images.

## Flow

1. Pandoc TeX → DOCX + `docx_media` (unchanged).
2. Table polish (`try_polish_docx`).
3. `replace_docx_native_charts(docx, figures, pack_hexes)` — soft-fail.
4. Match drawings whose media target contains `cht_\d+`.
5. Replace image drawing with chart graphic; write `word/charts/chartN.xml` (+ rels/content types).

## Word safety (2026-10-29)

MS Word rejects DOCX packages that embed a full `xlsx` under `word/embeddings/` for chart data. Liber ships **cache-only ChartML**: `c:numCache` / `c:strCache` in the chart XML, **no** `c:externalData`, empty `chartN.xml.rels`. Charts remain editable in Word (series/values live in the cache). Opt-out: `CASE3_DOCX_NATIVE_CHARTS=0`.

## Reuse

- `attach_series_ir` / `series_from_figures_json` / `NATIVE_CHART_TYPES`
- Color rules (per-point bar/donut, series colors) — shared helpers where practical
- Donut: % labels + caption series name

## Out of scope

- PDF path, Mermaid native, SSE, custom DOCX builder
