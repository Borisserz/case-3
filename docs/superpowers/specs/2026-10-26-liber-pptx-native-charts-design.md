# Liber PPTX — native charts for every deck chart

**Date:** 2026-10-26  
**Status:** approved (owner: approach Series IR + bar B, every `cht_*` in deck)  
**Backlog:** A11 in `docs/knowledge/backlog-deferred-2026-10-25.md`

## Goal

Downloaded `{stem}_slides.pptx`: every slide that references an eligible chart (`cht_*`) embeds a **native OOXML Office chart** (`ppt/charts/…`), colored from pack `chart_series`, editable in PowerPoint. Liber twin stays PNG.

## In scope

- Persist structured ChartSeriesIR on each chart in `figures.json` (`series` field) at write/edit time; PPTX prefers it over HTML regex.
- Native for whitelist: bar, grouped_bar, stacked_bar, horizontal_bar, line, area, donut.
- Pack colors on series (and per-point for single-series bar / donut).
- **Every** native-eligible `cht_*` in the run appears in the deck (`ensure_deck_charts` injects missing `chart_hero`s).
- Twin recolor: same pack per-category colors for single-series bar/donut (`apply_pack_category_colors_to_html`).
- Donut native: `%` data labels + series name from caption (not anonymous `Series`).
- Smoke: multi-chart deck → one native part per eligible `cht_*`.

## Out of scope

- Mermaid `dia_*` (stay PNG).
- KPI / scatter (PNG).
- Changing Liber twin / Chart.js report path visuals beyond series persistence.
- Editable SmartArt diagrams.

## Data

```json
{
  "id": "cht_01",
  "type": "bar",
  "html": "...",
  "series": {
    "type": "bar",
    "categories": ["Q1", "Q2"],
    "series": [{"name": "Rev", "values": [1, 2]}]
  }
}
```

## Files

- `slides_chart_data.py` — attach / prefer stored series
- `slides_pptx_charts.py` — richer native styling
- `slides_job.py` — ensure deck chart slide + build series map
- `pipeline.py` / `chart_edit.py` / chart finalize — persist `series`
- tests: chart_data, pptx_charts, optional ensure-deck
