# KI: Pipeline

## What
`run_pipeline` в `src/case3/pipeline.py`: llm → images → charts → inject → **latex/docx ∥ chat summary** → meta ok/error.

## Entry
- CLI: `case3` / `scripts/run.cmd`
- API: `POST /api/run` → background → `GET /api/runs/{id}/status`

## Invariants
- `run_id` = `{stem}_{UTC stamp}`; артефакты в `runs/{work,out,logs}/`
- Uploads bump `max_images` (cap 8)
- Dry-run: без media render; `summary_status=skipped`
- After inject: ThreadPool — `render_tex` + `try_generate_chat_summary` (outline→LLM stream → `summary_bus.BUS`); summary fail ≠ PDF fail
- `meta.chat_summary` / `summary_status`; SSE fan-out for Liber
- `PipelineError` несёт run_id для debug upload

## Gotchas
- `--reload` на uvicorn рвёт длинные job → `api.cmd` без reload
- Chart soft-fail ≠ pipeline fail
- Intent palette/types парсятся из UI block strings

## See
ADR-0001 · `api.py` · `generate.py` · `inject.py`
