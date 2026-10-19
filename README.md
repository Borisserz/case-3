# case-3

**Файл + Intent** → Qwen (LaTeX + HTML-графики + Kandinsky) → PDF/DOCX (Docker TeX).

DOCX стилизуется через `assets/docx/reference.docx` (pandoc `--reference-doc`), не «как получится» из дефолта.

## Запуск на Windows (из корня `case-3\`)

```cmd
git pull origin main
scripts\setup.cmd
```

Правь `.env` под **Qwen**: `VISION_API_BASE_URL=http://<host>:8080`  
(картинки: `KANDINSKY_MAX_IMAGES=0` если Kandinsky нет)  
Если «нет documentclass» / пустой ответ → `VISION_REASONING=off`, перезапуск `api.cmd`.

**Сайт — два окна cmd:**

```cmd
scripts\api.cmd
scripts\web.cmd
```

- UI: http://127.0.0.1:5173  (прокси `/api` → `:8000`)
- API: http://127.0.0.1:8000/docs · health: `/api/health`
- Сборка в Liber идёт с прогрессом (`POST /api/run` → poll `/status`); `api.cmd` **без** `--reload` (иначе рвёт длинные job). Dev-reload: `set CASE3_RELOAD=1` перед `api.cmd`.

**CLI:**

```cmd
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
scripts\run.cmd notes.txt -p "сделай отчёт" --format both
```

**Smoke (готовые Source в `fixtures\smoke\`):**

```cmd
scripts\smoke.cmd
```

Каждый файл → `run --format both`. Результат: `runs\out\<run_id>\`

## Env (`.env`)

| | |
|--|--|
| `VISION_API_BASE_URL` | Qwen |
| `CASE3_MAX_CHARTS` | потолок графиков (0 = off) |
| `KANDINSKY_MAX_IMAGES` | потолок картинок (0 = off) |
| `CASE3_IMAGE` | `case-3:tex` |

## Если сломалось

| | |
|--|--|
| нет Docker-образа | Docker Desktop → `scripts\setup.cmd` |
| нет графиков / Playwright | `python -m playwright install chromium` → перезапуск `api.cmd` |
| нет `\documentclass` / пустой ответ | `.env`: `VISION_REASONING=off`, перезапуск `api.cmd` |
| мало текста / нет графиков (обрыв) | `VISION_MAX_TOKENS=16384`, `max_charts≤2`, перезапуск `api.cmd` |
| Dry-run | графиков не будет — снять галку, нужен Vision |
| нет Vision | `.env` или UI → Dry-run |
| порт занят | закрой старые `api.cmd` / `web.cmd` |
| отдать логи | `scripts\push-debug.cmd` → ветка `debug/upload-STAMP` (без PDF/DOCX) |

## Папки

`scripts\` · `web\` · `src\` · `prompt\` · `assets\charts\` · `assets\docx\reference.docx` · `runs\` (out / logs / work / uploads)

## Windows checklist после pull

1. Docker Desktop запущен → `scripts\setup.cmd` (образ `case-3:tex`, Playwright, `pip install -e .`)
2. `.env` с Qwen URL; `.env` не в git
3. `scripts\api.cmd` + `scripts\web.cmd` → health `ok` / `vision_configured`
4. В Liber: Source + тип `kpi` / `line` / … → «Собрать»; стадии в pending; PDF/DOCX качаются
5. CLI smoke: `scripts\smoke.cmd` (нужен живой Vision)
