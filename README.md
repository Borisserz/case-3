# case-3

**Файл + промпт (intent)** → Qwen пишет LaTeX **и** промпты для Kandinsky → картинки (если включено) → PDF/DOCX.

## Каждый день

```cmd
REM данные в notes.txt, что сделать — в -p
scripts\run.cmd notes.txt -p "сделай PDF-отчёт с таблицами и 2 иллюстрациями"

scripts\run.cmd notes.txt --format pdf
scripts\run.cmd notes.txt --dry-run
```

Или intent из файла:

```cmd
scripts\run.cmd notes.txt --prompt-file intent.txt
```

Результат: `out\<run>\` (`.tex`, `.pdf`/`.docx`, `figures\`, `figures.json`).

## Скрипты (3)

| | |
|--|--|
| `scripts\setup.cmd` | один раз |
| `scripts\run.cmd` | прогон |
| `scripts\push-debug.cmd` | tex+логи на GitHub |

## Env

```env
VISION_API_BASE_URL=http://192.168.x.x:8080

# сколько картинок максимум (0 = без Kandinsky)
KANDINSKY_MAX_IMAGES=2
KANDINSKY_API_BASE_URL=http://192.168.x.x:8081
```

Если Kandinsky недоступен — PDF всё равно соберётся, слоты картинок уберутся.

## Как думает модель

1. `prompts/system_tex.md` — правила + формат ответа (latex + json)
2. `gold/` — 2–3 примера по тегам intent (`gold/index.yaml`)
3. User: **Intent** (`-p`) + **Source** (`notes.txt`)

## Первый запуск

```cmd
git pull
scripts\setup.cmd
REM правь .env
scripts\run.cmd notes.txt -p "краткий отчёт с таблицей" --dry-run
```
