# case-3

## Сначала проверь Qwen (Win LAN)

Пока модель молчит — Liber «жду модель» крутится зря. Подставь IP/модель из `.env`.

**Важно:** в PowerShell `curl` = `Invoke-WebRequest` → ошибка про Headers / Content-Type. Пиши **`curl.exe`**.

```cmd
curl.exe -s --max-time 30 http://192.168.4.101:8080/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"qwen3.5-4b\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":8,\"chat_template_kwargs\":{\"enable_thinking\":false}}"
```

`--max-time 30` = лимит ожидания ответа (сек), не путать с JSON-полем `"model"`.

- JSON с `choices` за ≤30 с → Vision ок, дальше `api.cmd` / `web.cmd`
- таймаут / ошибка → чини хост `:8080` у коллеги (не UI)

**Файл + Intent** → Qwen (LaTeX + HTML-графики + фото) → PDF/DOCX (Docker TeX).

**Liber Schema (Mermaid):** вкладка «Схема» — процессы с числами из Source (annotated flow), легенда, PNG. **В PDF/DOCX схем нет** (только графики/фото); print-truth = PDF.

**Preview edit:** графики / фото / **таблицы** («Изменить» → sheet → Сохранить в отчёт = TeX + PDF/DOCX). Таблицы: `POST /api/runs/{id}/tables/{n}/edit`.

**Память проекта (агенты и люди):** [`docs/MEMORY.md`](docs/MEMORY.md) · [`AGENTS.md`](AGENTS.md)

Фото: офисный Image API `POST /generate` и `POST /edit` (`IMAGE_API_BASE_URL`).  
DOCX: `assets/docx/reference.docx` (pandoc `--reference-doc`).

## Запуск на Windows (из корня `case-3\`)

```cmd
git pull origin main
scripts\setup.cmd
```

Правь `.env` под **Qwen**: `VISION_API_BASE_URL=http://<host>:8080`  
(фото: `IMAGE_API_BASE_URL=http://192.168.4.101:8000`, `IMAGE_MAX_IMAGES=2`)  
Если «нет documentclass» / пустой ответ → `VISION_REASONING=off`, перезапуск `api.cmd`.

**Сайт — два окна cmd:**

```cmd
scripts\api.cmd
scripts\web.cmd
```

После `git pull` в `web\`: `npm install` (нужен `pdfjs-dist` для превью 1-й стр. PDF в чате).

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
| `CASE3_MAX_DIAGRAMS` | потолок Mermaid-схем Liber UI (0–3, default 2; не в PDF) |
| `IMAGE_API_BASE_URL` | офисный Image API (`/generate`, `/edit`) |
| `IMAGE_MAX_IMAGES` | потолок фото (0 = off) |
| `CASE3_IMAGE` | `case-3:tex` |

## Если сломалось

| | |
|--|--|
| нет Docker-образа | Docker Desktop → `scripts\setup.cmd` |
| нет графиков / Playwright | `python -m playwright install chromium` → перезапуск `api.cmd` |
| нет `\documentclass` / пустой ответ | `.env`: `VISION_REASONING=off`, перезапуск `api.cmd` |
| HTTP **500** Context size exceeded | `.env`: `VISION_MAX_TOKENS=4096` (не 16384 на LAN GGUF), Source короче, фото/графики=0, рестарт `api.cmd` |
| мало текста / нет графиков (обрыв) | поднять `VISION_MAX_TOKENS` если ctx позволяет; `max_charts≤2`, рестарт `api.cmd` |
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
