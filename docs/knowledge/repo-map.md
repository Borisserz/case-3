# case-3 — карта репозитория

Кратко: **что где лежит**. Детали подсистем — KI в `.agents/knowledge/`, ADR в `docs/adr/`.

## Корень

| Путь | Зачем |
|------|--------|
| `backend/src/case3/` | Pipeline, API, charts, TeX/DOCX/PPTX, images |
| `backend/stimulsoft/` | Flask-viewer Stimulsoft, порт 8040. Отдельный процесс и свой venv |
| `frontend/` | Liber UI (Vite + React) |
| `backend/prompt/` | System prompts для LLM |
| `backend/assets/docx/reference.docx` | Pandoc reference для DOCX |
| `workers/case3-image/` | Cloudflare Workers AI image API (local `:8787`) |
| `backend/tests/` | Pytest. Запуск из `backend/` |
| `scripts/` | Desk launchers (`api`/`web`/`setup`/`push-debug`) |
| `backend/runs/` | Локальные артефакты прогонов (не коммитить) |
| `docs/` | MEMORY, ADR, knowledge, superpowers specs/plans |
| `AGENTS.md` | Контракт для агентов |
| `docker-compose.yml` | frontend + backend + stimulsoft. TeX-only — профиль `tex` |

## `backend/src/case3` (ядро)

| Модуль (примеры) | Роль |
|------------------|------|
| `pipeline.py` | Оркестрация стадий Source→PDF/DOCX |
| `api.py` | FastAPI Liber |
| `generate.py` | LLM → TeX / figures JSON |
| `charts*.py` / `chart_*.py` | Chart.js HTML → PNG (Playwright) |
| `render.py` | Docker TeX + pandoc DOCX |
| `slides_*.py` | Deck IR → HTML/PPTX/PDF |
| `image_api.py` | Фото generate/edit |
| `docx_*.py` | Post-pandoc polish / lists / charts |

## `frontend/src`

| Зона | Роль |
|------|------|
| `app/` | Shell Liber, composer, run UX |
| `domain/` | Типы, craft steps, phrases |
| `styles/` | CSS по поверхностям (chat, deck, shell…) |

## Не путать

- **PDF** = истина печати; chat preview ≈ TeX blocks (`\section`, `\subsection`, `\subsubsection`, таблицы, списки, фигуры).
- **Схемы Mermaid** — в Liber UI, в PDF/DOCX как PNG (`%CASE3_DIAG:dia_NN%`, ADR-0009) и в PPTX как нативные фигуры PowerPoint (`slides_pptx_diagrams.py`).
- **Палитры** — editorial / ocean / sunset / mono / atelier (без фиолетового нейрослопа).
