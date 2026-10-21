# Top 10 pipeline probes — полная проверка Liber Atelier

Готовые Intent + Source для ручного прогона в Liber (`http://127.0.0.1:5173`) или CLI.
Покрывают: все типы графиков, палитры, Mermaid-схемы, таблицы, PDF/DOCX, фото, edge-cases.

Settings baseline: палитра из Intent; `max_charts` / `max_diagrams` / `max_images` как в колонке.

| # | Цель | Source | max_c / max_d / max_i | Intent (вставить в чат) |
|---|------|--------|------------------------|-------------------------|
| 1 | Line + donut, ocean, PDF+DOCX | `fixtures/smoke/01_temp_shares.txt` | 2 / 0 / 0 | Русский отчёт. ОБЯЗАТЕЛЬНО типы графиков: line, donut. Палитра ocean. Без фото. Без схем. |
| 2 | Все числовые ряды → bar + kpi, atelier | `fixtures/smoke/04_demo_dense.txt` | 2 / 0 / 0 | Демография. ОБЯЗАТЕЛЬНО типы: bar, kpi. Палитра atelier. Таблица с KPI. Без фото. Без схем. |
| 3 | Scatter + line, editorial | `fixtures/smoke/08_scatter_pairs.txt` | 2 / 0 / 0 | Маркетинг. ОБЯЗАТЕЛЬНО типы: scatter, line. Палитра editorial. Без фото. Без схем. |
| 4 | Широкая таблица tabularx | `fixtures/smoke/02_wide_table.txt` | 0 / 0 / 0 | Сравнительная таблица на всю ширину A4 через tabularx. Без графиков, схем и фото. |
| 5 | Flowchart + state (Liber «Схема») | `fixtures/smoke/05_process_pipeline.txt` | 0 / 2 / 0 | Технический обзор: Mermaid flowchart шагов пайплайна + stateDiagram статусов run. Без графиков. Без фото. |
| 6 | Sequence + donut + SLA-таблица | `fixtures/smoke/07_support_flow.txt` | 1 / 1 / 0 | Поддержка: таблица SLA, donut по метрикам, sequenceDiagram эскалации L1→L2. Палитра ocean. Без фото. |
| 7 | Mindmap + timeline + line | `fixtures/smoke/06_product_release.txt` | 1 / 2 / 0 | Релиз Desk Notes: mindmap рисков, timeline discovery→GA, line по выручке. Палитра sunset. Без фото. |
| 8 | Kitchen sink (макс. структура) | `fixtures/smoke/06_product_release.txt` | 2 / 2 / 0 | Полный отчёт: разделы, таблица KPI, графики bar+line, схемы flowchart+sequence. Палитра atelier. Без фото. Форматы PDF и DOCX. |
| 9 | Фото + bar, mono | `fixtures/smoke/01_temp_shares.txt` | 1 / 0 / 1 | Отчёт с одним bar и одной фотоиллюстрацией по теме данных. Палитра mono. Без схем. |
| 10 | Проза без чисел / без выдумок | `fixtures/smoke/03_prose_no_numbers.txt` | 0 / 0 / 0 | Только проза и списки шагов. Без графиков, схем, фото. Не выдумывать числа. |

## Как прогонять

1. `scripts\api.cmd` + `scripts\web.cmd` (или Mac: uvicorn + `npm run dev`).
2. Health: `http://127.0.0.1:8000/api/health` → `ok`, `docker_ok`, `playwright_ok`, vision/image flags.
3. В Liber: New → прикрепить Source → вставить Intent → Settings (лимиты) → Send.
4. Проверить Artifact rail: **Превью** (блоки/live charts) · **PDF** · **Схема** (если max_d>0) · **Source** · Export PDF/DOCX.
5. Автоматрица (~30 кейсов): `PYTHONPATH=src python3 scripts/full_audit_matrix.py`.

## Чеклист визуала после прогона

- [ ] Нет orphan `%CASE3_*%` в TeX
- [ ] Donut не овальный в PDF; KPI — не bar-canvas
- [ ] Схемы только во вкладке «Схема», не в PDF
- [ ] Палитра без фиолетового нейрослопа
- [ ] Chat summary стримится; ThinkingFold не пустой
- [ ] Edit chart (палитра/тип) обновляет Preview + PDF
