# KI: Windows desk (prod)

## What
Corporate Windows workstation: Qwen Vision URL + Image API + Docker Desktop + Liber.

## Entry
- `scripts\setup.cmd` — image, playwright, pip
- `scripts\api.cmd` + `scripts\web.cmd`
- `.env` — never commit

## Invariants
- `VISION_API_BASE_URL` required for real runs
- `VISION_REASONING=off` if empty/`documentclass` missing
- Playwright Chromium installed for charts
- Docker image tag `case-3:tex` (env `CASE3_IMAGE`)

## Gotchas
- After pull: `cd web && npm install` (pdfjs)
- Proxy unset for API if corp proxy breaks localhost
- Don't use CASE3_RELOAD=1 on long jobs
- Health tip in UI may still sound Windows-centric (ok here)

## See
`README.md` · `docs/knowledge/ops-windows.md`
