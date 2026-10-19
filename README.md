# case-3

**Файл + Intent** → Qwen (LaTeX + HTML-графики Chart.js + Kandinsky) → PDF/DOCX (Docker TeX).

Модель **сама пишет** HTML каждого графика под документ. Рецепты в `prompt/system_tex.md` — только образцы; цифры только из Source.

## Node.js для сайта (Windows) — сначала это

Всё ниже — **только Windows / PowerShell**. Нужен **локальный** Node  
(**не** Docker, **не** Chocolatey, **не** winget с сайта nodejs.org).

### A. Скачать и поставить

1. Скачай `.msi`: **https://nodejs.org/dist/v24.22.0/node-v24.22.0-x64.msi**  
2. Запусти → Next → Finish  
3. **Закрой все** окна PowerShell / cmd / терминал Cursor  
4. Открой **новый** PowerShell

### B. Проверка (новый PowerShell)

```powershell
Test-Path "C:\Program Files\nodejs\node.exe"
node -v
npm -v
where.exe node
```

Норма: `True` и номера версий (`v24…`, `10…` / `11…`).  
Тогда дальше — раздел «Запуск из корня» (`api.cmd` + `web.cmd`).

### C. Пишет «уже установлена», а `node -v` — «не распознано»

Это сломанный PATH. В **новом** PowerShell по очереди:

```powershell
Test-Path "C:\Program Files\nodejs\node.exe"
dir "C:\Program Files\nodejs"
```

```powershell
Get-ChildItem -Path "C:\Program Files","C:\Program Files (x86)","$env:LOCALAPPDATA" -Filter node.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
```

Если `node.exe` нашёлся (часто `C:\Program Files\nodejs\node.exe`):

```powershell
$nodeDir = "C:\Program Files\nodejs"
$p = [Environment]::GetEnvironmentVariable("Path", "User")
if ($p -notlike "*$nodeDir*") {
  [Environment]::SetEnvironmentVariable("Path", "$p;$nodeDir", "User")
}
$env:Path = "$nodeDir;" + $env:Path
node -v
npm -v
```

Снова **закрой окно → новое** → ещё раз `node -v` и `npm -v`.

Проверка в обход PATH:

```powershell
& "C:\Program Files\nodejs\node.exe" -v
& "C:\Program Files\nodejs\npm.cmd" -v
```

### D. Файла нет — снести фантом и поставить .msi заново

PowerShell **от имени администратора**:

```powershell
winget uninstall OpenJS.NodeJS.LTS
winget uninstall OpenJS.NodeJS
winget list | findstr -i node
```

Потом снова раздел **A** (только `.msi` по ссылке выше).

### E. Не делай так

- способ **Docker** на nodejs.org  
- способ **Chocolatey** (`choco install…`)  
- способ **winget** с сайта, если он уже падал  

Подробнее: [docs/WINDOWS_NODE.md](docs/WINDOWS_NODE.md)

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

Если `node`/`npm` не находятся — смотри блок **Node.js** в начале этого README (разделы C–D).

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
