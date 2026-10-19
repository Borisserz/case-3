# case-3

**Файл + Intent** → Qwen (LaTeX + HTML-графики + Kandinsky) → PDF/DOCX (Docker TeX).

DOCX стилизуется через `assets/docx/reference.docx` (pandoc `--reference-doc`), не «как получится» из дефолта.

## Запуск (из корня `case-3\`)

**Один раз:**

```cmd
scripts\setup.cmd
```

Правь `.env`: `VISION_API_BASE_URL=...`  
Если ошибка «нет documentclass» / пустой ответ модели → в `.env` поставь `VISION_REASONING=off` и перезапусти `api.cmd`.

**Сайт — два окна:**

```cmd
scripts\api.cmd
scripts\web.cmd
```

- UI: http://127.0.0.1:5173  
- API: http://127.0.0.1:8000/docs · health: `/api/health`

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

`scripts\` · `web\` · `src\` · `prompt\` · `assets\charts\` · `runs\` (out / logs / work / uploads)
