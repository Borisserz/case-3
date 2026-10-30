# KI: Pipeline

## What
`run_pipeline` в `src/case3/pipeline.py`: llm → images → charts → inject → **latex/docx ∥ chat summary** → meta ok/error.  
Mermaid `diagrams[]` парсятся в LLM-стадии и пишутся в `figures.json` / result payload — **без** render/inject (Liber UI-only, ADR-0007).  
**Default-on:** при `max_diagrams≥1` модель должна дать ≥1 схему, если в Source есть структура (шаги/роли/ветки/≥3 раздела); Intent UI явно нудит. Soft-drop → `diagrams_dropped` в figures.json/meta.  
**Режим Схема** (`output_mode=diagram`): после llm всегда stage `diagram_repair` (`prompt/diagram_repair.md`) — 2-й LLM обогащает граф из Source; soft-fail → draft; meta `diagrams_repaired`, draft в `figures.json` → `diagrams_draft`.  
**Annotated flow:** числа из Source на labels (`["Заявка<br/>820"]`, `|62%|`) — prompts short, без role-кодов в тексте узла; Liber chips «Числа на схеме» (`diagramMetrics.ts`). Не дублировать chart series. Без живой БД (v1 = Source only). **Не в PDF** (ADR-0007).  
Палитра Settings → `format_diagram_color_prompt` в generate/repair. Liber API: `POST …/diagrams/{id}/edit`; `…/regenerate` + UI «Ещё вариант» (DiagramPane, undo slot `diagram_regen`). Empty diagram mode → honest chat text + empty pane CTA.

## Entry
- CLI: `case3` / `scripts/run.cmd`
- API: `POST /api/run` → background → `GET /api/runs/{id}/status`

## Invariants
- `run_id` = `{stem}_{UTC stamp}`; артефакты в `runs/{work,out,logs}/`
- Uploads bump `max_images` (cap 8)
- Dry-run: без media render; `summary_status=skipped`; `diagrams: []`
- `CASE3_MAX_DIAGRAMS` / `max_diagrams` (0–3, default 2); meta `diagrams_planned` / `diagrams_ok`
- After inject: ThreadPool — `render_tex` + `try_generate_chat_summary` (outline→LLM stream → `summary_bus.BUS`); summary fail ≠ PDF fail
- After render returns → `bump("summary")` so UI leaves «Собираю DOCX…» while summary still streams
- Summary LLM uses ≤90s timeout + local outline blurb fallback on fail/timeout
- `meta.chat_summary` / `summary_status`; SSE fan-out for Liber
- `PipelineError` несёт run_id для debug upload

## Gotchas
- `--reload` на uvicorn рвёт длинные job → `api.cmd` без reload
- Chart soft-fail ≠ pipeline fail
- Intent palette/types парсятся из UI block strings
- Long «Собираю DOCX» with PDF already on disk = hung chat-summary LLM (not pandoc)
- On hard fail: `meta.failed_stage` preserved (`images|charts|inject|latex|docx|…`). Resume: `POST /api/runs/{id}/resume` → `resume_pipeline` (no LLM; regen only missing/failed PNG) when `can_resume_run`; Liber button «Продолжить». Queue/retention/installer still parked.

## See
ADR-0001 · `api.py` · `generate.py` · `inject.py`
