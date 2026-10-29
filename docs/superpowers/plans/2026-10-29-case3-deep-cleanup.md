# case-3 Deep cleanup — plan

> **For agentic workers:** execute task-by-task; verify after each phase.

**Spec:** `docs/superpowers/specs/2026-10-29-case3-deep-cleanup-design.md`

## Task 1: Phase A — disk junk

- Wipe `runs/out/*`, `runs/work/*`, `runs/logs/*`, `runs/uploads/*` (keep `.gitkeep`).
- Remove untracked matrix folders under `runs/` (`_qa`, `atelier_visual`, `*matrix*`, etc.).
- Remove `.playwright-browsers/`, `.local-wrangler/`, `**/__pycache__`, `.pytest_cache`.
- `rm -rf /tmp/case3-qa` if present.

## Task 2: Phase B — gitignore + debug-bundle

- `git rm -r debug-bundle`
- Edit `.gitignore`: drop ignores for `tests/`, `docs/`, `AGENTS.md`, `fixtures/`; keep `runs/out|work|logs|uploads`; add `.playwright-browsers/`, `.local-wrangler/`, `runs/*` with exceptions for gitkeeps if needed.

## Task 3: Phase C — archive scripts

Move to `scripts/archive/` (git mv):

- `e2e_*`, `*_matrix*`, `full_audit*`, `full_structure*`, `owner_review*`, `premium_gallery*`, `render_premium*`, `run_freeform*`, `run_slides*`, `run_structure*`, `chart_visual_pack.py`

Keep at root: `api/web/run/setup/smoke.cmd`, `mac-up.command`, `push-debug.cmd`, `run-image-worker.sh`, `cf_image_proxy.py`, `build_reference_docx.py`, `render_template_previews.py` (used for gallery assets).

Add `scripts/archive/README.md`.

## Task 4: Phase D — repo-map + light code cleanup

- Write `docs/knowledge/repo-map.md`.
- Grep for obvious dead exports / unused imports only if safe; no behavior change.
- Keep prior fixes: `python-docx` dep, slides title-echo heal.

## Task 5: Phase E — verify

```bash
.venv/bin/python -m pytest tests/ -q
(cd web && npm run build)
curl -s http://127.0.0.1:8000/api/health
```
