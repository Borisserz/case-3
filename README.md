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
