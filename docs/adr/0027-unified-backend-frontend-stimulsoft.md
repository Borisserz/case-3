# ADR-0027: One repo, three processes

## Status
Accepted

## Date
2026-11-26

## Context
Inspectra lived in `case-3` (`src/case3` + `web/`). The Stimulsoft viewer lived in a sibling repo `stimulsoft-preview` and was reached only over HTTP on port 8040. Two git roots, two compose files, and a host URL (`DASHBOARD_SERVICE_URL`) made “run the product” three separate checkouts. The desk still has to start without Docker (`uv` and `npm`) and as one `docker compose up`.

Stimulsoft is Flask, pins Dashboards.PYTHON 2024.2.2, and talks to Postgres. The API is FastAPI on Python 3.12 with Playwright and TeX. The viewer handler forces `StiFrameworkType.FLASK`.

## Decision
One git repository. Three processes.

```text
frontend/                 Vite + React. Docker: Nginx :5173
backend/                  FastAPI :8000. uv, pytest, prompt, assets, runs
backend/stimulsoft/       Flask viewer :8040. Own venv and Dockerfile
docker-compose.yml        frontend + backend + stimulsoft
```

- Local API: `cd backend && uv run inspectra`.
- Local viewer: `cd backend/stimulsoft && uv run python view_dashboard.py` (Python 3.11).
- Local UI: `cd frontend && npm run dev`.
- Docker: from the repo root, `docker compose up -d --build`.
- Inside Compose the API calls `http://stimulsoft:8040`. The browser still opens `DASHBOARD_PUBLIC_URL` (default `http://127.0.0.1:8040`).
- Postgres stays on the host. The viewer container uses `host.docker.internal`.
- `.env`, license keys, and `.mrt` files stay untracked. `backend/.env.example` and `backend/stimulsoft/.env.example` are the templates.
- If `MRT_PATH` is not a file, the viewer opens the first `dashboards/*.mrt` instead of exiting.
- `repo_root()` is the `backend/` directory (the folder that has `Dockerfile` and `src/case3`).

ADR-0026 still stands: the chat starts with uv and npm, and print can use the TeX image. Only the directories change.

## Alternatives Considered

### Leave `web/` and `src/` names, only vendor the viewer
- Pros: smaller diff.
- Cons: the desk the team asked for is `frontend/` and `backend/` with the viewer inside the backend.
- Rejected because the folder names are the contract.

### Import the Flask app into the FastAPI process
- Pros: one port, one venv.
- Cons: the Stimulsoft handler is Flask-only, the wheels target 3.11, and a long report job would share a process with the live viewer and Postgres.
- Rejected because the viewer stays a separate process that the API already calls over HTTP.

## Consequences
- Positive: one branch builds the UI, the API, and the viewer. Docker and uv/npm both reach the same three programs.
- Negative / follow-ups: Windows `scripts\*.cmd` cd into `backend/` and `frontend/`. A machine needs `backend/.env` and `backend/stimulsoft/.env` plus a local Postgres. The old sibling repo is not deleted by this change.
