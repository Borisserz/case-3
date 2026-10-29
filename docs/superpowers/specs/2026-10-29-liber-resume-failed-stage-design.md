# Liber — Resume failed pipeline stage

**Status:** Approved (owner 2026-10-29)  
**Backlog:** [`docs/knowledge/backlog-deferred-2026-10-25.md`](../../knowledge/backlog-deferred-2026-10-25.md) §I (resume only; queue/retention/installer stay parked)

## Goal

When a run fails after LLM on `images` | `charts` | `inject` | `latex` | `docx`, the user can continue **the same `run_id`** from that point: redo only missing/failed media, then inject → render — without re-calling the model.

## Product decisions

- UI button «Продолжить» on failed Liber card → `POST /api/runs/{id}/resume`.
- Same `run_id`; no new stamp.
- Media: keep `ok` PNGs; regenerate only missing/failed.
- Button only if `status=error`, `failed_stage` ∈ resume set, and TeX (+ `figures.json`) exist under work/out.

## Design

### Preserve failed stage

Today `pipeline` sets `meta["stage"]="error"` on exception and loses the real stage. On error:

- `meta["failed_stage"]` = stage at failure (`images`|`charts`|`inject`|`latex`|`docx`|…).
- Keep `status=error`; `stage` may stay `"error"` for UI compatibility.

### API

`POST /api/runs/{run_id}/resume`

- 404 unknown run; 409 if not eligible; 200 `{ run_id, status: "started" }` and background job like `/api/run`.
- Clears cancel flag; sets `status=running`, bumps `resume_count`, records `resumed_from_stage`.

### `resume_pipeline(run_id, project_root, …)`

1. Load meta + locate TeX (`work` preferred, else `out`), `figures.json`, `status.json`.
2. Skip LLM.
3. If `failed_stage` in `{images, charts}` or media incomplete: rematerialize uploads; Image API / charts only for ids with `ok≠true` or missing PNG.
4. Always re-`inject` then `render_tex` (formats from meta) + summary path as in `run_pipeline` (parallel when print formats set).
5. On success → `ok`; on fail → same error diagnostics + new `failed_stage`.

### UI

Failed `ArtifactCard` (or Liber error strip): button «Продолжить» when `can_resume` from status (or client heuristic: error + failed_stage in set). Calls resume; resumes SSE/poll on same run.

### Eligibility helper

`can_resume_run(meta, work, out) -> bool` used by API and optionally exposed on `GET …/status` as `can_resume: true`.

## Non-goals

- Resume after LLM failure (no TeX).
- Queue / concurrency / retention / Win installer.
- Partial product modes B20 as Settings toggles.
- Auto-resume without button.

## Verification

- pytest: eligibility; media skip-ok / regen-failed (mocked generators); API 409 paths.
- Manual: force latex fail → Продолжить → PDF appears, same run_id.
