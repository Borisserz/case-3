# scripts/archive — one-shot QA / matrix runners

These are **not** the daily desk path. Liber day-to-day:

| Need | Script |
|------|--------|
| API | `../api.cmd` or `../mac-up.command` |
| UI | `../web.cmd` |
| CLI report | `../run.cmd` |
| Smoke fixtures | `../smoke.cmd` |
| Image worker | `../run-image-worker.sh` |

Archive contents are kept for audits / regression matrices (e2e, slides matrix, gallery decks). Run from repo root with `PYTHONPATH=src`, e.g.:

```bash
python scripts/archive/e2e_mac_matrix.py
```

`ROOT` in these scripts is `Path(__file__).resolve().parents[2]` (repo root — one level above `scripts/`).
