# case-3

**Файл + промпт** → Qwen (LaTeX + HTML-графики + Kandinsky) → PDF/DOCX (Docker TeX).

## Запуск на Windows (рабочий ПК)

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
| `CASE3_MAX_CHARTS` | 0 = без графиков; 1–N HTML→PNG |
| `KANDINSKY_MAX_IMAGES` | 0 = без картинок Kandinsky |
| `VISION_API_BASE_URL` | Qwen API |

### 2. Прогон

Положи текст в `notes.txt` (или любой `.txt`/`.md`).

```cmd
REM без API — проверка Docker/TeX
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run --format pdf

REM полный прогон (модель сама решит про графики, если в -p не запретил)
scripts\run.cmd notes.txt -p "сделай PDF с таблицами"

REM явный тип графика
scripts\run.cmd notes.txt -p "добавь столбчатую диаграмму bar по цифрам"

REM запрет графиков
scripts\run.cmd notes.txt -p "без графиков и диаграмм, только текст и таблицы"

REM только PDF
scripts\run.cmd notes.txt -p "короткий отчёт" --format pdf

REM только DOCX
scripts\run.cmd notes.txt -p "короткий отчёт" --format docx
```

Результат: `runs\out\<run_id>\` → `notes.pdf`, `notes.docx`, `.tex`, `figures\`, `meta.json`.

### 3. Флаги `run.cmd`

| Флаг | Что делает |
|------|------------|
| `notes.txt` | исходный текст |
| `-p` / `--prompt "..."` | Intent |
| `--prompt-file path` | Intent из файла |
| `--format pdf\|docx\|both` | формат (по умолчанию `both`) |
| `--dry-run` | без Qwen/графиков — stub TeX |

### 4. Отладка

```cmd
scripts\run.cmd notes.txt -p "тест" --dry-run
REM ошибка → runs\logs\<run>\error.txt и *.log
scripts\push-debug.cmd
```

## Папки

| | |
|--|--|
| `scripts\` | `setup` / `run` / `push-debug` |
| `src\case3\` | код |
| `prompt\` | system prompt + gold |
| `assets\charts\` | offline Chart.js |
| `runs\` | `out` / `logs` / `work` |
| `notes.txt` | исходный текст |

## Pipeline

1. Intent (`-p`) + Source (`notes.txt`).
2. Gold-примеры из `prompt\gold\`.
3. Qwen → LaTeX + JSON (`figures` + `charts` с HTML).
4. Если Intent **молчит** про графики, но в Source есть числа — модель **сама** выбирает тип/число/место (каталог: bar, line, donut, …).
5. HTML → Playwright PNG → слоты `%CASE3_CHART:id%`.
6. Kandinsky (если включён) → `%CASE3_FIG:id%`.
7. Docker `case-3:tex` → PDF/DOCX.
