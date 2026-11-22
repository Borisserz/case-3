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

Код на `main`: `72a0d52`. Свежие правки могут быть ещё не в коммите. Память, которую читает агент, едет на Windows: этот файл, `docs/MEMORY.md`, `docs/adr/`, `docs/knowledge/`, `.agents/knowledge/`.

- Схемы есть в PDF/DOCX (ADR-0009). ADR-0007 снят.
- В PPTX flowchart (≤10 узлов), timeline и mindmap — фигуры; иначе PNG (`slides_pptx_diagrams.py`).
- Пустой запрос: `input_validation.py` + JSON `insufficient_data`. Фото факты не заменяют.
- Свои фото: до 5. Сгенерированное фото только по просьбе (ADR-0012).
- Очередь: один прогон и один ожидающий (ADR-0010). Разбор PDF/DOCX — `source_ingest.py`. Дашборд — «Выбрать данные».
- Снимок: `docs/MEMORY.md`. Память чата — ADR-0013, числа — ADR-0015 и ADR-0016.

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
