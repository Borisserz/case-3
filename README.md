# case-3

**Text + images → Qwen (OpenAI-compatible API) → LaTeX → PDF/DOCX** in Docker.

Same API style as [bam-bam-bam](https://github.com/Borisserz/bam-bam-bam): `POST {VISION_API_BASE_URL}/v1/chat/completions` (text and/or `data:image;base64`).

Target OS for daily use: **Windows + Docker Desktop** (also works on macOS/Linux).

## Architecture

```
in/jobs/<name>/
  content.txt      →  LLM (Qwen)  →  work/…/*.tex  →  docker case-3:tex
  images/*.png                                         latexmk → PDF
                                                       pandoc  → DOCX
                         ↓
                    out/<run_id>/   logs/<run_id>/
```

## Windows setup (work PC)

```cmd
git clone https://github.com/Borisserz/case-3.git
cd case-3
git pull
scripts\setup-windows.cmd
```

Needs **Python 3.9+ on PATH** (`python --version` works). The setup script prefers `python`, not a fixed `py -3.11`.

Edit `.env`:

```env
VISION_API_BASE_URL=http://192.168.x.x:8080
```

(Same host you use for bam-bam-bam vision.)

### Run

```cmd
REM without API (skeleton tex → PDF/DOCX) — smoke test
scripts\run-pipeline.cmd in\jobs\demo --dry-run

REM with Qwen
scripts\run-pipeline.cmd in\jobs\demo
```

### Push outputs for remote debug

After a run (success or fail):

```cmd
scripts\push-debug.cmd
```

Pushes `out/` + `logs/` (+ `debug-bundle/<stamp>/`) to branch **`debug/runs`** on the private GitHub repo so Cursor can inspect logs remotely.

## macOS / Linux

```bash
cp .env.example .env
python3 -m pip install -e . -r requirements.txt
docker compose build
make dry-run
# make run   # needs API
./scripts/push-debug.sh
```

## Job layout

```
in/jobs/myreport/
  content.txt          # required (or .md)
  images/
    chart.png          # optional; referenced as images/chart.png in TeX
```

## Gold examples for the model

See [`gold/`](gold/) — figures, tables, lists distilled from real reports (Prototip / CSIS style), adapted to the lean TeX image.

## Manual TeX render (no LLM)

```bash
./bin/case-3 both in/example.tex
```

## Env vars

| Variable | Meaning |
|----------|---------|
| `VISION_API_BASE_URL` | Qwen / VLM base (required for real generate) |
| `VISION_API_KEY` | optional Bearer |
| `VISION_MODEL` | optional model id |
| `CASE3_IMAGE` | Docker tag (default `case-3:tex`) |

## What is not in this repo

Dashboard, FastAPI, presentations, DB — later. This repo is the **output + LLM→TeX** slice.

## Гайд: Docker Desktop на Windows («Virtualization support not detected»)

Если Docker пишет **Virtualization support not detected** / **Engine stopped**, образ `case-3:tex` не собрать, пока не включена виртуализация.

### 1. Проверка (~1 мин)

PowerShell **от администратора**:

```powershell
systeminfo | findstr /i "Hyper-V"
Get-ComputerInfo -Property "HyperV*"
```

Нужно: **Virtualization Enabled In Firmware: Yes**.

### 2. Компоненты Windows

`Win + R` → `optionalfeatures` → включить:

1. **Virtual Machine Platform**
2. **Windows Subsystem for Linux**
3. **Hyper-V** (если есть в редакции; на Home часто нет — хватит пунктов 1–2)

Перезагрузка, затем:

```powershell
wsl --install
wsl --update
wsl --set-default-version 2
```

### 3. BIOS / UEFI

1. Перезагрузка → вход в BIOS (`F2` / `Del` / `F10` — зависит от ПК).
2. Включить:
   - Intel: **Intel VT-x** / Virtualization Technology  
   - AMD: **SVM Mode** / AMD-V  
3. Save & Exit.

Если пункты серые или BIOS под паролем — нужен **IT**: «включите VT-x/SVM для Docker Desktop / WSL2».

### 4. После включения

1. Запустить **Docker Desktop** — статус не «Engine stopped».
2. Проверка:

```cmd
docker version
docker run --rm hello-world
```

3. В проекте:

```cmd
cd C:\Users\serjanovich\Projects\case-3
git pull
scripts\build-image.cmd
```

### Если виртуализацию на рабочем ПК не дадут

На этой машине можно только шаг LLM → `.tex`:

```cmd
python -m case3.cli generate in\jobs\demo -o work\demo.tex --dry-run
scripts\push-debug.cmd
```

Сборку PDF/DOCX делать на ПК/Mac, где Docker уже работает.
