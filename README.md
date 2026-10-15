# case-3

**Текст → Qwen (text-to-text) → LaTeX → PDF/DOCX** в Docker.

Модель **не** генерирует картинки. Только LaTeX-код, потом `latexmk` / `pandoc`.

API как в bam-bam-bam: `POST {VISION_API_BASE_URL}/v1/chat/completions` (без image в запросе).

## Как прогнать (главное)

1. Положи текстовый файл в корень проекта, например `notes.txt`.
2. Запусти:

```cmd
scripts\run.cmd notes.txt
```

Только PDF или только Word:

```cmd
scripts\run.cmd notes.txt pdf
scripts\run.cmd notes.txt docx
```

Без API (проверка Docker/TeX):

```cmd
scripts\run.cmd notes.txt both --dry-run
```

Результат: `out/<имя>_<время>/` — `.tex`, `.pdf`, `.docx`, `meta.json`.  
Логи: `logs/<имя>_<время>/`.

Отправить вывод на GitHub для удалённого дебага:

```cmd
scripts\push-debug.cmd
```

## Скрипты (всего три для тебя)

| Скрипт | Зачем |
|--------|--------|
| `scripts\setup.cmd` | **Один раз:** pip + `docker compose build` |
| `scripts\run.cmd` | **Каждый день:** текст → модель → PDF/DOCX |
| `scripts\push-debug.cmd` | Залить `out/` + `logs/` в ветку `debug/runs` |

Остальные файлы в `scripts\` — вспомогательные (`_resolve-python.cmd`, `.sh` для Mac).

## Первый запуск на Windows

```cmd
git clone https://github.com/Borisserz/case-3.git
cd case-3
scripts\setup.cmd
```

В `.env`:

```env
VISION_API_BASE_URL=http://192.168.x.x:8080
```

## macOS / Linux

```bash
cp .env.example .env   # VISION_API_BASE_URL=...
pip install -e .
docker compose build
./scripts/run.sh notes.txt
./scripts/push-debug.sh
```

Или: `python -m case3.cli run notes.txt --format both`

## Что внутри

```
notes.txt  →  LLM пишет .tex  →  docker case-3:tex  →  PDF + DOCX
```

- `gold/` — эталонные куски LaTeX для промпта  
- `prompts/system_tex.md` — системный промпт (text-only)  
- `Dockerfile` — lean XeLaTeX + Pandoc  

## Env

| Variable | Meaning |
|----------|---------|
| `VISION_API_BASE_URL` | хост Qwen (обязателен для реальной генерации) |
| `VISION_API_KEY` | optional |
| `VISION_MODEL` | optional |

## Гайд: Docker Desktop («Virtualization support not detected»)

Если Docker пишет **Virtualization support not detected** / **Engine stopped**, образ не собрать без виртуализации.

### 1. Проверка

PowerShell от администратора:

```powershell
systeminfo | findstr /i "Hyper-V"
Get-ComputerInfo -Property "HyperV*"
```

Нужно: **Virtualization Enabled In Firmware: Yes**.

### 2. Компоненты Windows

`Win + R` → `optionalfeatures` → включить:

1. **Virtual Machine Platform**
2. **Windows Subsystem for Linux**
3. **Hyper-V** (если есть; на Home часто нет)

Перезагрузка, затем:

```powershell
wsl --install
wsl --update
wsl --set-default-version 2
```

### 3. BIOS / UEFI

Включить Intel **VT-x** или AMD **SVM**. Если BIOS под паролем — через IT.

### 4. После включения

```cmd
docker version
docker run --rm hello-world
cd C:\Users\serjanovich\Projects\case-3
scripts\setup.cmd
```
