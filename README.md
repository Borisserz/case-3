# case-3 — Inspectra

Аналитическое рабочее пространство (Chat-first UI + FastAPI + LaTeX/Pandoc/LibreOffice/Playwright) для работы с дашбордами **Stimulsoft** и документами (`.pdf`, `.docx`, `.txt`, `.md`):

- **Чат-аналитика по дашбордам и документам:** снятие одного или нескольких экранов дашборда (визуальный PNG + полная векторная таблица PDF до 64 колонок × 500 строк + автоматический расчёт секции `## Производные`: суммы, средние, мин/макс, доли, отклонения `Факт − План` и групповые итоги по областям).
- **Строгая привязка чисел (Fact Grounding):** модель опирается только на исходные данные, числа из вопроса пользователя (*what-if* сценарии) и проверяемую кросс-строчную арифметику (`+`, `−`, `%`, доли) между регионами и периодами.
- **Генерация артефактов:**
  - **В чате:** таблицы, аналитические ответы, inline-графики Chart.js (PNG) и схемы процессов/структур.
  - **Отчёты (PDF + DOCX):** вёрстка через XeLaTeX и Pandoc (`reference.docx`), нативные редактируемые диаграммы в Word, автоматический альбомный разворот широких таблиц (6–15 колонок, включая многостраничные `xltabular`).
  - **Презентации (PPTX + PDF):** 6–24 слайдов, 8 визуальных стилей, 11 структур, нативные векторные графики и схемы в PowerPoint.
- **Живое редактирование (in-place):** правка текста разделов, таблиц, графиков, подписей, стилей и заголовков конкретных слайдов как через UI-превью, так и обычными фразами в чате (*«перекрась график в закат»*, *«в таблице поменяй Пинский р-н на г. Пинск»*, *«поменяй заголовок слайда 3 на Анализ областей»*, *«распиши раздел Выводы подробнее»*, *«отмени»*).
- **Многопользовательский режим и асинхронность:** изоляция рабочих пространств по браузерам (`X-Workspace-Id`), параллельные ответы в чате, пул воркеров для одновременной сборки отчётов (`CASE3_MAX_CONCURRENT_RUNS`, по умолчанию `3`) и FIFO-очередь (`CASE3_MAX_QUEUED_RUNS`, по умолчанию `8`).

---

## Запуск у себя, без Docker

Три терминала. Скрипты не нужны. Команды из корня репозитория.

**API** (`backend/`, FastAPI :8000):

```bash
cd backend
uv venv --python 3.12
uv pip install -r requirements.txt
uv run inspectra
```

**Stimulsoft** (`stimulsoft/`, Flask :8040). Свой venv: пакеты 2024.2.2 не ставятся в API.

```bash
cd stimulsoft
uv venv --python 3.11
uv pip install -r requirements.txt
uv run python view_dashboard.py
```

**Фронт** (`frontend/`, Vite :5173):

```bash
cd frontend
npm i
npm run dev
```

- Сайт: http://127.0.0.1:5173
- API: http://127.0.0.1:8000/docs
- Дашборд: http://127.0.0.1:8040/viewer
- Живой чат и превью работают без Docker. «BI система» ходит на :8040.
- Графики в чате, один раз из `backend/`: `uv run playwright install chromium`
- Qwen: скопируй `backend/.env.example` → `backend/.env` и поставь `VISION_API_BASE_URL`.
- База и лицензия Stimulsoft: `stimulsoft/.env` (файл не коммитится). `.mrt` лежат в `stimulsoft/local/`.

`uv run` без имени не знает, что запускать. Команда API — `uv run inspectra`. Перезагрузка кода на каждый файл рвёт длинную сборку, поэтому её нет. Для неё: `CASE3_RELOAD=1 uv run inspectra`.

Печать PDF и DOCX в локальном столе по-прежнему ждёт образ TeX. Чат поднимается без Docker.

## Полный стек в Docker

Из корня репозитория. Три сервиса: Nginx `:5173`, FastAPI снаружи `:8010` (внутри сети Docker порт `CASE3_PORT`, по умолчанию 8000; TeX Live, Pandoc, LibreOffice, Playwright), Stimulsoft `:8040`. На хосте `:8000` — image-модель, `:8080` — Qwen. Порты меняются в корневом `.env` (образец `.env.example`), не в Dockerfile.

```bash
docker compose up -d --build
```

Сборка API не ходит на `cdn.playwright.dev`. Chrome 159 для контейнера linux/amd64 лежит в `backend/vendor/playwright/` и хранится в Git LFS. Один раз на машине: `git lfs install`, дальше `git pull` забирает zip сам.

- **Интерфейс Inspectra:** http://127.0.0.1:5173 (проксирует `/api/*` и SSE на `backend:${CASE3_PORT}`)
- **Swagger API:** http://127.0.0.1:8010/docs
- **Swagger Stimulsoft:** http://127.0.0.1:8040/docs
- **Проверка:** `curl -s http://127.0.0.1:5173/api/health`

Внутри сети контейнеров API зовёт `http://stimulsoft:8040`. Браузер открывает дашборд по `DASHBOARD_PUBLIC_URL` (по умолчанию `http://127.0.0.1:8040`). Postgres остаётся на хосте: контейнер Stimulsoft ходит в `host.docker.internal`.

Отдельный образ `case-3:tex`, если рендер нужен снаружи backend-контейнера:

```bash
docker compose --profile tex build tex
```

---

## Сначала проверь Qwen (Win LAN)

Пока модель молчит — Liber «жду модель» крутится зря. Подставь IP/модель из `.env`.

**Важно:** в PowerShell `curl` = `Invoke-WebRequest` → ошибка про Headers / Content-Type. Пиши **`curl.exe`**.

```cmd
curl.exe -s --max-time 30 http://192.168.4.101:8080/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"qwen3.5-4b\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":8,\"chat_template_kwargs\":{\"enable_thinking\":false}}"
```

`--max-time 30` = лимит ожидания ответа (сек), не путать с JSON-полем `"model"`.

- JSON с `choices` за ≤30 с → Vision ок, дальше `api.cmd` / `web.cmd`
- таймаут / ошибка → чини хост `:8080` у коллеги (не UI)
- **404 на `:8080/generate` — нормально (это путь Image API).** Текст: только `/v1/chat/completions`
- Фото отдельно: `curl.exe -s -o NUL -w "%{http_code}" http://192.168.4.101:8000/` (корень может дать 404 — процесс жив; для генерации нужен `POST /generate`)

**Source ingest:** `.pdf` / `.docx` — просмотр во вкладке «Источник» (pdf.js), текст и таблицы извлекаются автоматически. `.txt` / `.md` / снимки дашбордов Stimulsoft — просмотр таблиц с поиском и подсветкой + редактирование по клику до сборки. Скан-PDF без текстового слоя → отказ (422). `.doc`/`.rtf`/PDF-превью DOCX — через LibreOffice.

**Схемы:** вкладка «Схема» — процессы с числами из документа, легенда, скачивание PNG и редактирование узлов. Слот `%CASE3_DIAG:dia_NN%` попадает в PDF и DOCX как `figures/dia_NN.png` (ADR-0009), а в PPTX рисуется нативными фигурами PowerPoint.

**Презентация:** слайдов 6–24 (настройка «Слайдов в презе»). До 5 своих PNG/JPEG.

**Preview edit:** разделы текста / списки / графики / фото / **таблицы** («Изменить» → редактирование ячеек → «Сохранить» = пересборка TeX + PDF/DOCX). Таблицы: `POST /api/runs/{id}/tables/{n}/edit`.

Фото: офисный Image API `POST /generate` и `POST /edit` (`IMAGE_API_BASE_URL`).  
DOCX: `assets/docx/reference.docx` (pandoc `--reference-doc`).

## Запуск на Windows (из корня `case-3\`)

```cmd
git fetch origin
git checkout unify-stack
git pull
docker compose up -d --build
```

Правь `backend\.env` под **Qwen**: `VISION_API_BASE_URL=http://host.docker.internal:8080`  
(фото: `IMAGE_API_BASE_URL=http://host.docker.internal:8000`, `IMAGE_MAX_IMAGES=2`. Свои вложения в презу — отдельно, до 5)  
Если «нет documentclass» / пустой ответ → `VISION_REASONING=off`, затем `docker compose up -d --build backend`.

Сайт уже внутри контейнера `frontend`. Отдельно `npm` и `python` для монолита не нужны. `.mrt` положи в `stimulsoft\dashboards\`.

- UI: http://127.0.0.1:5173  (прокси `/api` на порт контейнера `CASE3_PORT`)
- API: http://127.0.0.1:8010/docs · health: `/api/health`
- Сборка в Liber идёт с прогрессом (`POST /api/run` → poll `/status`); `api.cmd` **без** `--reload` (иначе рвёт длинные job). Dev-reload: `set CASE3_RELOAD=1` перед `api.cmd`.

Сборка и артефакты: через Liber UI → `backend\runs\out\<run_id>\`.

## Env (`.env`)

| Переменная | Описание |
|--|--|
| `VISION_API_BASE_URL` | URL сервера Qwen / OpenAI-совместимого LLM (`http://<host>:8080/v1`) |
| `VISION_API_KEY` | API-ключ LLM (если требуется) |
| `VISION_MODEL` | Имя модели (например, `qwen3.5-4b` или `openrouter/free`) |
| `DASHBOARD_SERVICE_URL` | Куда API ходит за дашбордом. Локально `http://127.0.0.1:8040`. В Docker Compose это `http://stimulsoft:8040` |
| `DASHBOARD_PUBLIC_URL` | URL, который открывает браузер. По умолчанию `http://127.0.0.1:8040` |
| `CASE3_MAX_CHARTS` | Потолок графиков в отчёте (0 = off, default 5) |
| `CASE3_MAX_DIAGRAMS` | Потолок схем (0–5, default 5). PNG в PDF/DOCX и нативные фигуры в PPTX |
| `IMAGE_API_BASE_URL` | Офисный Image API (`/generate`, `/edit`) |
| `IMAGE_MAX_IMAGES` | Потолок сгенерированных фото (0 = off, default 2) |
| `CASE3_IMAGE` | Имя Docker-образа TeX (`case-3:tex`) |
| `CASE3_LOCAL_TEX` | `1` внутри контейнера `backend` (локальный `latexmk` + `pandoc` без вложенного Docker) |
| `CASE3_MAX_CONCURRENT_RUNS` | Число параллельных воркеров сборки отчётов/презентаций (`1..8`, default `3`) |
| `CASE3_MAX_QUEUED_RUNS` | Размер FIFO-очереди ожидающих сборок (`1..32`, default `8`) |
| `CASE3_CORS_ORIGINS` | Дополнительные разрешённые CORS-ориджины через запятую |

## Если сломалось

| | |
|--|--|
| нет Docker-образа | Docker Desktop → `docker compose up -d --build` |
| нет графиков / Playwright | `python -m playwright install chromium` → перезапуск `api.cmd` |
| нет `\documentclass` / пустой ответ | `.env`: `VISION_REASONING=off`, перезапуск `api.cmd` |
| HTTP **500** Context size exceeded | `.env`: `VISION_MAX_TOKENS=4096` (не 16384 на LAN GGUF), Source короче, фото/графики=0, рестарт `api.cmd` |
| Завис после TeX на «фото» / `stage=images` / `inject` навсегда | Баг ETA-lock (fixed `4a64a98`+): `git pull`, убей python, один прогон. Image `:8000` мёртв → `IMAGE_MAX_IMAGES=0` |
| «PDF 6 минут» а файла нет | Это не latexmk — LLM + deadlock на 2-й стадии; после pull PDF ~секунды после TeX |
| Куча `running` в `backend\runs\out` | Task Manager → убей все `python`, один `api.cmd`, один прогон |
| HTTP **409** | Третий `POST /api/run`: один прогон уже идёт, второй ждёт (`202 queued`). Сброс слота — `POST /api/pipeline/slot/reset`, только если поток мёртв |
| Коллега «404» | Не тот URL: Qwen≠`/generate`; или качаешь PDF пока `status=running` |
| мало текста / нет графиков (обрыв) | поднять `VISION_MAX_TOKENS` (≥12288 при 4–5 графиках); UI «Графиков ≤» + `CASE3_MAX_CHARTS`; рестарт `api.cmd` |
| Dry-run | графиков не будет — снять галку, нужен Vision |
| нет Vision | `.env` или UI → Dry-run |
| порт занят | закрой старые `api.cmd` / `web.cmd` |
| отдать логи | `scripts\push-debug.cmd` → ветка `debug/upload-STAMP` (slim: tex/logs/json/raw, без PNG/slides; `KEEP_MEDIA=1` / `KEEP_PDF=1` по необходимости) |

## Папки

`frontend\` · `backend\` (`src`, `stimulsoft`, `prompt`, `assets`, `runs`) · `docker-compose.yml`

## Windows checklist после pull

1. Docker Desktop → `docker compose up -d --build`
2. `backend\.env` с Qwen URL и `stimulsoft\.env` с Postgres и лицензией; оба файла не в git
3. `.mrt` в `stimulsoft\dashboards\`
4. http://127.0.0.1:5173/api/health → `"ok": true`
5. Liber: «BI система», затем отчёт в панели
