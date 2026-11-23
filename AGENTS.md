# AGENTS.md — case-3 / Liber Atelier

Ты работаешь в репозитории **case-3**: Source+Intent → **Qwen** (LaTeX + Chart.js HTML + фото) → PDF/DOCX (Docker TeX) + Liber chat UI.

## Сначала память

1. Прочитай [`docs/MEMORY.md`](docs/MEMORY.md) (карта L1/L2/L3).
2. Для зоны задачи — KI в [`.agents/knowledge/`](.agents/knowledge/) и ADR в [`docs/adr/`](docs/adr/).
3. Не выдумывай API/пути — проверяй файлы. Не рапортуй «готово» без проверки.

## Стек (коротко)

| Слой | Путь |
|------|------|
| Pipeline | `src/case3/pipeline.py` |
| LLM prompts | `prompt/MANIFEST.md` + `case3.prompts` · TeX via `generate.py` |
| Charts | `chart_*.py`, Playwright, `templates/chart_frame.html` |
| Images | `image_api.py`, `workers/case3-image/` |
| Render | `render.py` → Docker `case-3:tex` |
| API | `src/case3/api.py` (FastAPI) |
| UI | `web/src/` (Vite + React) |

Прод-контур: **Windows desk**, Qwen (`VISION_*`), Image API (`IMAGE_API_BASE_URL`).  
Запуск: `scripts\api.cmd` + `scripts\web.cmd` — см. README и `docs/knowledge/ops-windows.md`.  
Карта папок: [`docs/knowledge/repo-map.md`](docs/knowledge/repo-map.md). One-shot matrix/gallery → `scripts/archive/`.

## Состояние на 2026-11-22

Код на `main`: `c7c035d`. Память, которую читает агент, едет на Windows: этот файл, `docs/MEMORY.md`, `docs/adr/`, `docs/knowledge/`, `.agents/knowledge/`.

- Плашка «Отчёт» побеждает голое «проанализируй» (ADR-0017). Вопрос и «проанализируй отчёт» остаются в чате.
- Числа: своя строка, своя область в одной фразе, доля только со словом «доля» или `%`. `12,5` — одна точка графика, `100,40` — две. `105865` без пробелов входит в доли. Чужое число в `\title` становится «Отчёт».
- Дашборд поступлений: фильтр «на 1 февраля» — это числа за январь. Чат разбирает их и не отказывается (ADR-0019). Март при заголовке «январь» по-прежнему другой период.
- Ячейка слайда `07` / `12` требует Source. Кикер `01` остаётся. Год `2024.` в начале строки остаётся числом.
- «Итого …» не входит в доли. Обрезка таблицы пишется в markdown. Сбой PNG не становится фото. Подпись про экран не встаёт на таблицу PDF.
- Широкая таблица Word переворачивает только свою страницу.
- Рестарт API: мёртвый `running` → `error`, сам не продолжается (ADR-0010). Третий запрос говорит, что очередь занята, без id и без «перезапуск». «Скрыть» прячет плашку и оставляет документ.
- Схемы есть в PDF/DOCX (ADR-0009). Очередь: один прогон и один ожидающий. Снимок: `docs/MEMORY.md`. Числа — ADR-0015 и ADR-0016.

## Жёсткие правила продукта

- Числа в новом файле — из Source, из этой реплики, или старое число пользователя только рядом с тем же словом. Память чата и уже собранный отчёт сами по себе числами не являются. Строка таблицы отдаёт только свои ячейки.
- Палитры: editorial / ocean / sunset / mono / atelier — без фиолетового нейрослопа.
- Chart types — whitelist в `chart_html.CHART_TYPES`.
- PDF — истина печати; чат-превью ≈ TeX blocks, может расходиться.
- Не коммитить `runs/`, `.env`, секреты, PDF/DOCX артефакты (кроме `assets/docx/reference.docx`).
- Палитры: editorial / ocean / sunset / mono / atelier — без фиолетового нейрослопа.
- Chart types — whitelist в `chart_html.CHART_TYPES`.
- PDF — истина печати; чат-превью ≈ TeX blocks, может расходиться.
- Не коммитить `runs/`, `.env`, секреты, PDF/DOCX артефакты (кроме `assets/docx/reference.docx`).

## Process

- Новая фича → brainstorming → plan в `docs/superpowers/` при необходимости.
- Баг → systematic-debugging до правок.
- Код → TDD где уместно; перед «готово» → verification.
- Отчёты БГУИР — отдельно skill `bsuir-academic-writing` (не этот репо).

## Parked (не делать без явного запроса)

- PPTX deck v1 shipped; native charts — `docs/superpowers/specs/2026-10-26-liber-pptx-native-charts-design.md`. Extra skins — `docs/knowledge/parked-pptx.md`.
- UX polish roadmap — `docs/superpowers/plans/2026-10-20-liber-ux-polish-roadmap.md` (фаза 0+ по запросу).
- C7 DOCX lists + resume-failed-stage **shipped** 2026-10-29 — see `docs/knowledge/backlog-deferred-2026-10-25.md`.
