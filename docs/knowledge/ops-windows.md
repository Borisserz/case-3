# Ops — Windows desk

Финальный прогон (3 запроса + readiness): [`windows-final-run.md`](windows-final-run.md).

## First install

1. Docker Desktop running  
2. `git fetch origin` then `git checkout unify-stack` and `git pull`  
3. Edit `backend\.env`: `VISION_*`, `IMAGE_API_BASE_URL`. Stimulsoft: `backend\stimulsoft\.env` and the `.mrt` files in `backend\stimulsoft\dashboards\`  
4. `docker compose up -d --build`  
5. Check `http://127.0.0.1:5173/api/health` → `ok` / vision flags  

## After every pull

```cmd
git pull
docker compose up -d --build
```

Health must show `vision_configured` + `docker_ok` + `playwright_ok` before Liber runs. Playwright and TeX are already inside the backend image.

## Common fixes

| Symptom | Fix |
|---------|-----|
| `No module named 'pptx'` / api crash on import | `docker compose up -d --build backend` |
| Empty model / no documentclass | `VISION_REASONING=off`, restart api |
| Truncated TeX | raise `VISION_MAX_TOKENS`, lower max_charts |
| Charts `Timeout 15000ms` / all `cht_*` fail | `.env`: `CASE3_CHART_TIMEOUT_S=45` (or delete line), restart `api.cmd`; code default is 45s |
| `UnicodeDecodeError` cp1251 in `_readerthread` / UI «Остановлено» mid-PDF | Pull fix (`procutil.run_captured`); restart `api.cmd` — was Docker TeX UTF-8 vs Win locale |
| No Docker image | `setup.cmd` / build image |
| Port busy | kill old api/web |
| Proxy breaks Vision | unset HTTP(S)_PROXY for api session |

## Do not ship to git

`.env`, `runs/*` artifacts, local PDF/DOCX outputs.

## push-debug (agent handoff)

Default bundle is **slim** (~few MB): `*.tex`, `*.log`, `*.json`, `*.txt` — no PNG, `slides/`, `docx_media/`, deck.  
If push fails with **remote rejected … Internal Server Error** and ~100+ MB in git output → old script copied all PNG; `git pull` and re-run `scripts\push-debug.cmd`.  
Optional: `set KEEP_MEDIA=1` (heavy), `set KEEP_PDF=1`, `set KEEP_WORK=1`.
