# System map

```text
┌──────────── Liber (web :5173) ────────────┐
│  App · Settings · ReportView · PdfSlider  │
└───────────────┬───────────────────────────┘
                │ /api/*
┌───────────────▼───────────────────────────┐
│           FastAPI (api.py :8000)          │
│  run · status · chart/figure edit · health│
└───────────────┬───────────────────────────┘
                │
┌───────────────▼───────────────────────────┐
│              run_pipeline                 │
│  llm → images → charts → inject → render  │
└───┬─────────┬──────────┬──────────┬───────┘
    │         │          │          │
 Qwen      Image API  Playwright  Docker
 VISION_*  IMAGE_*    Chart.js    case-3:tex
                                  PDF + DOCX
```

## Artifacts per run

```text
runs/out/<run_id>/
  *.tex  figures.json  figures/*.png  *.pdf  *.docx  meta.json
runs/logs/<run_id>/   pipeline + latex logs
runs/work/<run_id>/   scratch
```

## Key modules

| Concern | Module |
|---------|--------|
| Orchestration | `pipeline.py` |
| LLM + parse | `generate.py`, `parse_output.py` |
| Charts | `charts.py`, `chart_*` |
| Photos | `image_api.py`, `user_photos.py`, `figure_edit.py` |
| TeX | `tex_preamble.py`, `inject.py`, `render.py` |
| Preview JSON | `tex_preview.py` |
