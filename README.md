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
(корень `:8000/` — API, не сайт)

**Только CLI (без сайта):**

```cmd
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
```

## Chromium (Playwright) — для графиков

**Зачем:** модель отдаёт HTML Chart.js → Playwright открывает его в headless **Chromium** → снимок PNG → картинка в PDF/DOCX.  
Без Chromium документ соберётся, но **графики будут skip** (`playwright_ok: false` в health).

**Поставить / починить** (из корня, тот же Python что у API):

```cmd
python -m playwright install chromium
```

или:

```cmd
py -3 -m playwright install chromium
```

Проверка: http://127.0.0.1:8000/api/health → `"playwright_ok": true`  
(перезапусти `scripts\api.cmd` после установки).

`scripts\setup.cmd` уже вызывает эту установку один раз; если пропустила/упала — команда выше.

## Требования (Windows)

| Что | Зачем |
|-----|--------|
| **Docker Desktop** (WSL2) | образ `case-3:tex` → PDF/DOCX |
| **Python 3.9+** | pipeline, API, Playwright |
| **Node.js 18+** + npm | React demo UI (`web.cmd`) |
| Сеть до Qwen | полный прогон (не dry-run) |

## Быстрый старт Windows

### 1. Один раз (~5–20 мин)

```cmd
cd /d C:\path\to\case-3
git pull
scripts\setup.cmd
```

`setup.cmd`: Docker → `.env` → `pip install -e .` → Playwright Chromium → `docker compose build`.

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
| `CASE3_MAX_CHARTS` | потолок графиков (0 = off; UI может переопределить) |
| `KANDINSKY_MAX_IMAGES` | потолок картинок (0 = off) |
| `KANDINSKY_API_BASE_URL` | если нужны иллюстрации |
| `CASE3_IMAGE` | Docker-образ TeX |

Типы Chart.js: `bar`, `line`, `donut`, `horizontal_bar`, `grouped_bar`, `stacked_bar`, `area`, `scatter`, `kpi`.

### 2. Demo UI

```cmd
scripts\api.cmd
scripts\web.cmd
```

UI: http://127.0.0.1:5173 — Source, типы/лимиты, Intent → PDF + DOCX.  
Без Vision — **Dry-run**.

### 3. CLI

```cmd
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
scripts\run.cmd notes.txt -p "сделай отчёт с таблицами и графиком" --format both
```

Результат: `runs\out\<run_id>\`.

| Флаг | Что делает |
|------|------------|
| `-p` / `--prompt` | Intent |
| `--format pdf\|docx\|both` | по умолчанию `pdf` |
| `--dry-run` | без Qwen |

### 4. Отладка

```cmd
scripts\run.cmd notes.txt -p "тест" --dry-run
scripts\push-debug.cmd
```

### 5. Если что-то не стартует

| Симптом | Что сделать |
|---------|-------------|
| `Docker image missing` | Docker Desktop → `scripts\setup.cmd` |
| health `ok: false` / нет Vision | `.env` или UI → Dry-run |
| графики skip / нет Chromium | `python -m playwright install chromium` → перезапуск `api.cmd` |
| UI / npm | поставь Node LTS, новые окна cmd |
| 404 на `:8000/` | это API → `/docs` или сайт `:5173` |
| `ModuleNotFoundError` | `scripts\setup.cmd` |
| порт занят | закрой старые `api.cmd` / `web.cmd` |

```cmd
curl http://127.0.0.1:8000/api/health
```

Нужно: `docker_ok`, `playwright_ok`, `vision_configured` (для полного парада).

## Графики

1. Qwen → LaTeX + JSON (`charts[].html`).
2. Playwright Chromium + offline Chart.js → PNG.
3. Inject → Docker TeX → PDF/DOCX.

## Папки

| | |
|--|--|
| `scripts\` | setup / run / api / web / push-debug |
| `web\` | React demo |
| `src\case3\` | pipeline + FastAPI |
| `prompt\` | system prompt + gold |
| `assets\charts\` | offline Chart.js |
| `runs\` | out / logs / work / uploads (локальный мусор прогонов) |

**`runs\out\`** — готовые PDF/DOCX. Содержимое `runs\` можно чистить.

## Pipeline

1. Intent ∥ Source  
2. Gold  
3. Qwen → LaTeX + JSON  
4. Charts → Chromium PNG; Kandinsky (если URL)  
5. Docker `case-3:tex` → PDF/DOCX  
