# case-3

**Файл + Intent** → Qwen (LaTeX + HTML-графики Chart.js + Kandinsky) → PDF/DOCX (Docker TeX).

Модель **сама пишет** HTML каждого графика под документ. Рецепты в `prompt/system_tex.md` — только образцы; цифры только из Source.

## Запуск из корня проекта (терминал)

Все команды — из корня репо (`case-3\`), не из `web\` / `scripts\`.

**Один раз** (Docker Desktop включён):

```cmd
scripts\setup.cmd
```

Потом правь `.env` (`VISION_API_BASE_URL=...`).

**Сайт (два терминала, оба из корня):**

```cmd
scripts\api.cmd
```

```cmd
scripts\web.cmd
```

Открой **сайт:** http://127.0.0.1:5173  
API docs: http://127.0.0.1:8000/docs · health: `/api/health`  
(корень `:8000/` сам уводит на `/docs` — это не сайт)

Если `web.cmd` пишет про **npm**: поставь [Node.js LTS](https://nodejs.org/), галка Add to PATH, **новые** окна cmd, проверка `node -v` и `npm -v`.

**Только CLI (без сайта):**

```cmd
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
```

## Требования (Windows)

| Что | Зачем |
|-----|--------|
| **Docker Desktop** (WSL2) | образ `case-3:tex` → PDF/DOCX |
| **Python 3.9+** (`python` или `py`) | pipeline, API, Playwright |
| **Node.js 18+** + npm | только для React demo UI |
| Сеть до Qwen | полный прогон (не dry-run) |

## Быстрый старт Windows

### 1. Один раз (~5–20 мин)

```cmd
cd /d C:\path\to\case-3
git pull
scripts\setup.cmd
```

`setup.cmd` делает:

1. проверяет Docker;
2. копирует `.env.example` → `.env` (если нет);
3. `pip install -e .`;
4. `playwright install chromium` (PNG графиков);
5. `docker compose build` → образ `case-3:tex`.

Правь `.env`:

```env
VISION_API_BASE_URL=http://192.168.x.x:8080
CASE3_MAX_CHARTS=3
KANDINSKY_MAX_IMAGES=0
CASE3_IMAGE=case-3:tex
```

| Env | Смысл |
|-----|--------|
| `VISION_API_BASE_URL` | Qwen / Vision API |
| `CASE3_MAX_CHARTS` | потолок графиков по умолчанию (0 = off; UI может переопределить) |
| `KANDINSKY_MAX_IMAGES` | потолок картинок (0 = off) |
| `KANDINSKY_API_BASE_URL` | если нужны иллюстрации |
| `CASE3_IMAGE` | Docker-образ TeX (по умолчанию `case-3:tex`) |

Типы Chart.js: `bar`, `line`, `donut`, `horizontal_bar`, `grouped_bar`, `stacked_bar`, `area`, `scatter`, `kpi`.

### 2. Demo UI (два окна cmd)

```cmd
scripts\api.cmd
```

```cmd
scripts\web.cmd
```

- UI: http://127.0.0.1:5173  
- API / docs: http://127.0.0.1:8000/docs  
- health: http://127.0.0.1:8000/api/health  

В UI: Source (drag-drop / текст), **«на усмотрение модели»** или типы / своё пожелание, лимиты (потолок), Intent → **PDF + DOCX**.  
Без Vision — включи **Dry-run** (проверка Docker/TeX без LLM).

`web.cmd` при первом запуске выполнит `npm install` в `web\`.

### 3. CLI без UI

```cmd
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
scripts\run.cmd notes.txt -p "сделай отчёт с таблицами и графиком"
scripts\run.cmd notes.txt -p "короткий отчёт" --format both
```

Результат: `runs\out\<run_id>\` (`*.pdf`, `*.docx`, `meta.json`).

| Флаг | Что делает |
|------|------------|
| `notes.txt` | исходный текст |
| `-p` / `--prompt "..."` | Intent |
| `--prompt-file path` | Intent из файла |
| `--format pdf\|docx\|both` | по умолчанию **`pdf`** |
| `--dry-run` | без Qwen — stub TeX + Docker |

### 4. Отладка

```cmd
scripts\run.cmd notes.txt -p "тест" --dry-run
scripts\push-debug.cmd
```

### 5. Если что-то не стартует

| Симптом | Что сделать |
|---------|-------------|
| `Docker image missing` | Docker Desktop запущен → `scripts\setup.cmd` |
| `VISION_API…` / health `ok: false` | заполни `.env`, или UI → Dry-run |
| графики skip / Playwright | `python -m playwright install chromium` |
| UI / `npm не является…` | [Node.js LTS](https://nodejs.org/) + PATH, новые cmd; `node -v` / `npm -v` |
| 404 на `http://127.0.0.1:8000/` | это API, не сайт → `/docs` или UI на `:5173` |
| API `ModuleNotFoundError` | снова `scripts\setup.cmd` (`pip install -e .`) |
| порт занят | закрой старый `api.cmd` / `web.cmd` или смени порт |

Проверка health (PowerShell / curl):

```cmd
curl http://127.0.0.1:8000/api/health
```

Ожидаемо для полного парада: `docker_ok`, `playwright_ok`, `vision_configured`.

## Графики: как это устроено

1. Intent + Source → Qwen пишет LaTeX + JSON со слотами `%CASE3_CHART:id%` и полем `html`.
2. HTML — **уникальный фрагмент Chart.js** на каждый запуск (не копипаст рецептов).
3. Playwright + offline `assets/charts/chart.umd.min.js` → PNG → inject в TeX → PDF/DOCX.

Правила качества и «не выдумывать числа» — в `prompt/system_tex.md`. UI передаёт потолок, auto/типы/пожелания в Intent (`src/case3/api.py`).

## Папки

| | |
|--|--|
| `scripts\` | `setup` / `run` / `api` / `web` / `push-debug` |
| `web\` | React demo |
| `src\case3\` | pipeline + FastAPI |
| `prompt\` | system prompt + gold |
| `assets\charts\` | offline Chart.js |
| `runs\` | локальные артефакты прогонов (не код) |

**`runs\out\`** — готовые PDF/DOCX/tex после генерации.  
**`runs\logs\`** — логи ошибок TeX.  
**`runs\work\`** / **`uploads\`** — временные файлы.  

Можно спокойно удалять содержимое `runs\out`, `runs\logs`, `runs\work` — это мусор прогонов, в git почти не попадает. Нужные PDF копируй куда сдаёшь.

## Pipeline (кратко)

1. Intent ∥ Source (+ UI-требования).
2. Gold из `prompt\gold\`.
3. Qwen → LaTeX + JSON (`figures` + `charts`).
4. Charts → Playwright PNG; Kandinsky (если URL в `.env`).
5. Docker `case-3:tex` → PDF/DOCX.
