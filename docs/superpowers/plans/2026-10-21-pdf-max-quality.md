# План: PDF отчёта до максимального качества

> **Для агентов:** выполнять задача за задачей через `superpowers:subagent-driven-development` (предпочтительно) или `superpowers:executing-plans`. Шаги — чекбоксы `- [ ]`.

**Цель:** довести Liber PDF до «max quality» — chrome печати, таблицы, графики, структура текста и регрессионный контроль — **не ломая** цепочку Qwen → TeX → Docker.

**Архитектура:** PDF — истина (`latexmk`). Улучшаем post-LLM harden (`tex_preamble`, `tex_safe`, polish графиков) + prompt + опционально лёгкий TeX-pass по спискам. Фикстуры страхуют регрессии. DOCX вторичен (pandoc + `reference.docx`).

**Стек:** XeLaTeX / `case-3:tex`, Playwright + Chart.js PNG, FastAPI pipeline, pytest, опционально скрины страниц PDF.

**Контекст:** [`docs/superpowers/specs/2026-10-21-pdf-max-quality-analysis.md`](../specs/2026-10-21-pdf-max-quality-analysis.md)

**Уже сделано (не повторять):** vivid-палитры, крупная легенда, D4 линия под title, D6 списки в prompt, D7 clamp ширины/высоты, D1–D3.

---

## Жёсткие ограничения

- Типы графиков — только whitelist (`chart_html.CHART_TYPES`)
- Палитры: editorial / ocean / sunset / mono / atelier — **без фиолетового**
- Числа и факты — только из Source
- Не выдумывать стадии pipeline / env без ADR/KI
- Не коммитить `runs/`, `.env`, секреты, PDF/DOCX (кроме `assets/docx/reference.docx`)
- PDF = истина печати; чат-превью может расходиться
- Harden/стиль — через TDD; chrome PDF — глазами по страницам

---

## Карта файлов

| Зона | Файл |
|------|------|
| Chrome отчёта | `src/case3/tex_preamble.py` |
| Width / escape | `src/case3/tex_safe.py` |
| Графики | `chart_style.py`, `chart_types_coerce.py`, `templates/chart_frame.html` |
| Prompt | `prompt/system_tex.md` |
| DOCX | `assets/docx/reference.docx`, `scripts/build_reference_docx.py` |
| Inject / render | `inject.py`, `render.py` |
| Фикстуры | `tests/fixtures/pdf_quality/` (новая) |
| KI | `.agents/knowledge/KI-tex-render.md`, `KI-charts.md` |

---

## Фазы (что делать дальше)

| Фаза | Задачи | Срок | Результат |
|------|--------|------|-----------|
| **A — Gate** | Задача 1 | 0.5–1 день | Не ломаем chrome при правках |
| **B — Печать** | Задачи 2, 3, 5 | 1–2 дня | «Журнальный» вид PDF |
| **C — Текст** | Задача 4 | ~1 день или park | Списки не только за счёт LLM |
| **D — Word** | Задача 6 | ~1 день | **done** 2026-10-21 |
| **E — Бренд** | Задачи 7–8 | 1–2 дня | Общие tokens / два стиля |

**Рекомендация:** сначала **A**, потом **B**.

---

### Задача 1: Визуальный smoke / D11 lite (фаза A)

**Файлы:**
- Создать: `tests/fixtures/pdf_quality/minimal.tex`
- Создать: `tests/test_pdf_quality_smoke.py`
- Опционально: `scripts/pdf_quality_smoke.py`

- [x] **Шаг 1–5.** Done 2026-10-21: `tests/test_pdf_quality_smoke.py` + `fixtures/pdf_quality/minimal.tex`; skip без Docker; KI обновлён.

---

### Задача 2: Print chrome 2.0 — секции и float (фаза B)

**Файлы:** `tex_preamble.py` (`_SAFE_TITLEFORMAT`, `REPORT_STYLE`), `tests/test_report_style.py`

- [x] **Шаг 1–5.** Done 2026-10-21: titlespacing 1.8ex / parskip+itemsep в `_LIBER_PRINT_CHROME`; тесты + vivid_demo.

---

### Задача 3: Таблицы в PDF (фаза B)

**Файлы:** `tex_preamble.py` или тонкий `tex_tables.py`; `prompt/system_tex.md`; `tests/test_harden_tables.py`

- [x] **Шаг 1–3.** Done 2026-10-21: `tex_tables.harden_table_rules` в `ensure_document_preamble`; prompt + тесты.

---

### Задача 4: Структура прозы сверх D6 (фаза C)

**Файлы:** опционально `tex_prose.py`; вызов после salvage / в harden; `tests/test_tex_prose_lists.py`

- [x] **Шаг 1–3.** Done 2026-10-21: `tex_prose.harden_prose_lists` в `ensure_document_preamble`; `tests/test_tex_prose_lists.py`.
- [x] **Шаг 4.** Низкий риск — shipped (не park).

---

### Задача 5: Плотность графиков на A4 (фаза B)

**Файлы:** `chart_types_coerce.py`, `inject.py`, `chart_frame.html`, `tests/test_chart_a4_limits.py`

- [x] **Шаг 1–3.** Done 2026-10-21: multi-chart width 0.82 в `polish_charts`; donut `minmax(320px,1fr)`; vivid_demo пересобран.

---

### Задача 6: Паритет DOCX — D5 + D8 (фаза D)

**Файлы:** `scripts/build_reference_docx.py`, `assets/docx/reference.docx`, `src/case3/docx_polish.py`, `render.py`

- [x] **Шаг 1.** Reference: margins 2.2cm, heading spacing, footer PAGE (D8).
- [x] **Шаг 2.** Post-pandoc `try_polish_docx` — bold header + numeric right-align (D5).
- [x] **Шаг 3.** KI + tests; глазами — открыть `runs/vivid_demo/out/vivid_demo.docx` (на Windows desk — Liberation).

---

### Задача 7: Общие print-tokens — D10 lite (фаза E)

**Файлы:** `chart_style.py`; при UI — CSS print-mode (C9); ADR если появится `print_tokens.json`

- [x] **Шаг 1–2.** Done 2026-10-21: `palette_fallback_table()` → `{{PALETTE_TABLE}}` в `system_tex.md`; `tests/test_palette_tokens.py`.

---

### Задача 8: Два стиля отчёта — D9 (фаза E, по запросу)

**Файлы:** Settings UI + строка Intent + id стиля в `tex_preamble`

- [ ] **Шаг 1.** Сначала brainstorming с пользователем: Liber vs «строгий».
- [ ] **Шаг 2.** Только после OK: `report_style: liber|strict` в Intent.

---

## Критерии «готово»

- [ ] `pytest tests/` зелёный (smoke с Docker или skip)
- [ ] Offline PDF с несколькими графиками просмотрен **постранично**
- [ ] KI + roadmap актуальны; analysis-спека не врёт
- [ ] Нет purple; нет выдуманных фактов; нет `runs/` в git

---

## Следующий шаг для тебя

Выбери фазу: **A** (gate), **B** (печать + графики) или **C** (текст).  
По умолчанию: **A → B**.
