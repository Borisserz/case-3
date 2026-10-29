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
| LLM → TeX | `src/case3/generate.py`, `prompt/system_tex.md` |
| Charts | `chart_*.py`, Playwright, `templates/chart_frame.html` |
| Images | `image_api.py`, `workers/case3-image/` |
| Render | `render.py` → Docker `case-3:tex` |
| API | `src/case3/api.py` (FastAPI) |
| UI | `web/src/` (Vite + React) |

Прод-контур: **Windows desk**, Qwen (`VISION_*`), Image API (`IMAGE_API_BASE_URL`).  
Запуск: `scripts\api.cmd` + `scripts\web.cmd` — см. README и `docs/knowledge/ops-windows.md`.  
Карта папок: [`docs/knowledge/repo-map.md`](docs/knowledge/repo-map.md). One-shot matrix/gallery → `scripts/archive/`.

## Жёсткие правила продукта

- Числа и факты — только из Source; не выдумывать.
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
