# case-3

**Файл + промпт** → Qwen (LaTeX + промпты Kandinsky) → PDF/DOCX.

## Каждый день

```cmd
scripts\run.cmd notes.txt -p "сделай PDF с таблицами и 2 картинками"
scripts\run.cmd notes.txt --dry-run
scripts\push-debug.cmd
```

Результат: `runs\out\<run>\`

## Папки (мало)

| | |
|--|--|
| `scripts\` | setup / run / push-debug |
| `src\` | код |
| `prompt\` | system prompt + gold-примеры |
| `runs\` | out / logs / work (всё промежуточное) |
| `notes.txt` | твой исходный текст |

## Env

```env
VISION_API_BASE_URL=http://192.168.x.x:8080
KANDINSKY_MAX_IMAGES=2
KANDINSKY_API_BASE_URL=http://192.168.x.x:8081
```

`KANDINSKY_MAX_IMAGES=0` — без картинок.

## Первый запуск

```cmd
git pull
scripts\setup.cmd
REM правь .env
scripts\run.cmd notes.txt -p "краткий отчёт" --dry-run
```
