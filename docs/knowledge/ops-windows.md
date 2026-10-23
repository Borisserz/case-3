# Ops — Windows desk

Финальный прогон (3 запроса + readiness): [`windows-final-run.md`](windows-final-run.md).

## First install

1. Docker Desktop running  
2. `git pull origin main`  
3. `scripts\setup.cmd`  
4. Edit `.env`: `VISION_*`, `IMAGE_API_BASE_URL`, optional `CASE3_MAX_CHARTS`  
5. `cd web && npm install`  
6. `scripts\api.cmd` + `scripts\web.cmd`  
7. Check `http://127.0.0.1:8000/api/health` → `ok` / vision / image flags  

## After every pull

```cmd
git pull origin main
cd web && npm install
```

Restart api + web. If charts blank: `python -m playwright install chromium`.

## Common fixes

| Symptom | Fix |
|---------|-----|
| Empty model / no documentclass | `VISION_REASONING=off`, restart api |
| Truncated TeX | raise `VISION_MAX_TOKENS`, lower max_charts |
| No Docker image | `setup.cmd` / build image |
| Port busy | kill old api/web |
| Proxy breaks Vision | unset HTTP(S)_PROXY for api session |

## Do not ship to git

`.env`, `runs/*` artifacts, local PDF/DOCX outputs.
