# Full audit findings — 2026-10-21

Полный прогон Liber Atelier: unit/UI/Windows + **30** live pipeline probes + chart multi-edit.

| Слой | Результат |
|------|-----------|
| Unit (`pytest`) | **187 passed** |
| Web build (`npm run build`) | OK (chunk-size warning only) |
| Helper tests (`npm run test:helpers`) | 3/3 |
| Health (`/api/health`) | docker · playwright · vision · image OK |
| Pipeline matrix | **29/30** → blank-chart flake на photo+bar; **fixed + retry** |
| Chart multi-edit (4×) | **4/4** ok |
| Live charts QA (`?preview=charts-qa`) | все 9 типов рисуются |
| Purple neuroslop in chart HTML | **0** hits |

Артефакты матрицы (локально, не в git): `runs/full_audit_oct21/summary.json`, `runs/out/audit_*`.

Top-10 ручных запросов: [`2026-10-21-top10-pipeline-probes.md`](2026-10-21-top10-pipeline-probes.md).  
Скрипт: `scripts/full_audit_matrix.py`.

---

## Вердикт

Продукт в целом **здоровый**: все whitelist-графики, все Mermaid-типы, PDF/DOCX, таблицы, dry-run, kitchen-sink, chat summary и Liber desk работают. Один flake (blank canvas после Image API) закрыт retry + paint nudge. Settings: поле «Схем ≤» было на второй строке 2-col grid — починено 3-col row.

Windows desk: скрипты `.cmd`, pathlib, Playwright cache Windows-путь — **готово к desk**; не коммитить `.env` / `runs/`.

---

## Проблемы (найдено → статус)

### P1 — Blank chart после фото (E01) — **FIXED**

- **Симптом:** `cht_01` `canvas painted=0` при `max_images=1` + bar; PDF всё равно собрался (~849 KB с fig).
- **Причина:** `__CASE3_CHART_READY` раньше первой заливки canvas (особенно после Image API); HTML валидный.
- **Фикс:** `charts._force_chart_paint` + один полный relaunch Chromium при `is_blank_chart_error`; тест `tests/test_blank_chart_retry.py`.
- **Проверка:** re-render того же `figures.json` → PNG 41 KB OK; suite 187 green.

### P2 — Settings: «Схем ≤» не в первом экране — **FIXED**

- **Симптом:** `.row` = `1fr 1fr` → третье поле (схемы) уезжало вниз; без скролла тела модалки не видно.
- **Фикс:** `.settings-limits-row { grid-template-columns: repeat(3, …) }` + class на Limits row.

### P3 — Soft / notes (не блокеры)

| # | Наблюдение | Действие |
|---|------------|----------|
| N1 | `scripts/e2e_mac_matrix.py` hardcode Mac Playwright path | Исправлен на Mac/Linux/Windows candidates |
| N2 | Vite chunk >500 KB (mermaid/pdf) | Warning only; code-split later |
| N3 | `?preview=charts-qa` кратко «нет fixture» до fetch | Race; после load все 9 OK |
| N4 | Chart soft-fail ≠ pipeline fail | by design; PDF без cht_* |
| N5 | Playwright: несколько версий chromium в cache | `playwright install` после апгрейда пакета |

---

## Матрица 30 probes

### Charts (C01–C09) — all OK

bar · grouped_bar · stacked_bar · line · horizontal_bar · donut · kpi · area · scatter  
Палитры: atelier / ocean / sunset / mono / editorial. Donut не овал; KPI — HTML-числа, не bar-canvas.

### Multi-chart (M01–M05) — all OK

line+donut · bar+kpi · area+hbar · grouped+stacked · scatter+line (+ DOCX где задано).

### Diagrams Liber-only (D_*) — all OK

flowchart · sequence · mindmap · timeline · stateDiagram — в `figures.json`, **не** в TeX (`%CASE3_DIAG*` нет).

### Structure / formats (T01–T05) — all OK

wide tabularx · prose · docx-only · pdf full (charts+flowchart) · kitchen sink (bar+line + flowchart+sequence + DOCX).

### Edges (E01–E06)

| ID | Result | Notes |
|----|--------|-------|
| E01 photo+bar | FAIL→fixed | blank canvas; retry landed |
| E02 dry-run | OK | 1.3s |
| E03 без схем | OK | diagrams=[] |
| E04 support | OK | donut + sequence |
| E05 process | OK | flowchart + stateDiagram |
| E06 release | OK | line + mindmap + timeline |

Orphan `%CASE3_*` в TeX audit_*: **none**.

---

## UI Liber (визуальный проход)

- Empty / hero prompts, Sidebar New/History/Settings — ок
- Settings: все 9 chart types + 6 palettes + health «Vision · Docker · Playwright · Image API»
- Artifact rail: Превью · PDF · Source · Export · TOC · «в PDF» на figure
- `?preview=flow`: ThinkingFold + PipelineFlow («В очереди…»)
- `?preview=charts-qa`: live Chart.js ×9
- `?preview=artifact`: demo Northstar + donut Preview

---

## Windows readiness

| Check | Status |
|-------|--------|
| `scripts\api.cmd` / `web.cmd` / `setup.cmd` / `run.cmd` / `smoke.cmd` | OK |
| Proxy cleared in api/web.cmd | OK |
| Playwright: `AppData\Local\ms-playwright` candidate | OK in `charts.py` |
| Pathlib (no `/tmp` in `src/case3`) | OK |
| Docker image `case-3:tex` | required on desk |
| Do not ship `.env`, `runs/` | enforced |

Ops: [`docs/knowledge/ops-windows.md`](../knowledge/ops-windows.md).

---

## Per-case (matrix raw)

- **OK** `C01`…`C09`, `M01`…`M05`, `D_*`, `T01`…`T05`, `E02`…`E06`
- **FAIL→fixed** `E01_with_photo` — blank chart after photo

---

## Next action (optional)

Перезапустить API на desk (подтянуть `charts.py`), затем probe #9 из top-10 (photo+bar) один раз глазами в Liber.
