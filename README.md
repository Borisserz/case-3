# case-3

**Файл + промпт** → Qwen (LaTeX + HTML-графики + Kandinsky) → PDF/DOCX (Docker TeX).

## Demo UI (React)

Два терминала после `scripts\setup.cmd`:

```cmd
scripts\api.cmd
scripts\web.cmd
```

Открой http://127.0.0.1:5173 — drag-drop Source, лимиты графиков/картинок (потолок, не план), чип **«на усмотрение модели»** или свой тип/пожелание, Intent в чат → **PDF + DOCX**. Графики и Kandinsky только если уместны по Source.

API: http://127.0.0.1:8000/docs · health: `/api/health`

## Запуск CLI на Windows

### 1. Один раз (~5–20 мин)

1. Docker Desktop **запущен** (WSL 2 / virtualization).
2. В корне репо:

```cmd
git pull
scripts\setup.cmd
```

`setup` ставит Python-пакет, **Playwright Chromium** (для графиков) и собирает образ `case-3:tex`.

3. Правь `.env` (из `.env.example`):

```env
VISION_API_BASE_URL=http://192.168.x.x:8080
CASE3_MAX_CHARTS=3
KANDINSKY_MAX_IMAGES=0
```

| Env | Смысл |
|-----|--------|
| `CASE3_MAX_CHARTS` | **единственный** бюджет графиков по умолчанию: 0 = off, 1–N (UI может переопределить на запрос) |
| `KANDINSKY_MAX_IMAGES` | 0 = без картинок Kandinsky (UI тоже может переопределить) |
| `VISION_API_BASE_URL` | Qwen API |

Типы графиков (Chart.js): `bar`, `line`, `donut`, `horizontal_bar`, `grouped_bar`, `stacked_bar`, `area`, `scatter`, `kpi`.

### 2. Прогон CLI

```cmd
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
scripts\run.cmd notes.txt -p "сделай отчёт с таблицами"
scripts\run.cmd notes.txt -p "короткий отчёт" --format both
```

Результат: `runs\out\<run_id>\`.

### 3. Флаги `run.cmd`

| Флаг | Что делает |
|------|------------|
| `notes.txt` | исходный текст |
| `-p` / `--prompt "..."` | Intent |
| `--prompt-file path` | Intent из файла |
| `--format pdf\|docx\|both` | по умолчанию **`pdf`** |
| `--dry-run` | без Qwen — stub TeX |

### 4. Отладка

```cmd
scripts\run.cmd notes.txt -p "тест" --dry-run
scripts\push-debug.cmd
```

## Папки

| | |
|--|--|
| `scripts\` | setup / run / api / web / push-debug |
| `web\` | React demo UI |
| `src\case3\` | pipeline + FastAPI |
| `prompt\` | system prompt + gold |
| `assets\charts\` | offline Chart.js |
| `runs\` | out / logs / work / uploads |
| `notes.txt` | исходный текст |

## Pipeline

1. Intent + Source.
2. Gold из `prompt\gold\`.
3. Qwen → LaTeX + JSON (`figures` + `charts`).
4. HTML charts → Playwright PNG; Kandinsky (если включён).
5. Docker `case-3:tex` → PDF/DOCX.
