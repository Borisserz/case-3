# Liber SSE finish — mode scripts + meta.steps[] (no sound)

**Date:** 2026-10-26  
**Status:** approved (owner: sound out; approach compact)  
**Parent:** [`docs/knowledge/desk-live-progress-and-health.md`](../../knowledge/desk-live-progress-and-health.md) §3 · after 2A/2B

## Goal

1. **Mode scripts:** checklist copy + template switch feel distinct for report / diagram / presentation; `slides_*` stages force presentation craft template.
2. **`meta.steps[]`:** durable compact log of stage/step/terminal for late SSE join + status hydrate (F5 / API restart).
3. **No sound.**

## Server

- Compact entry: `{ t, event, stage?, scope?, detail?, parent?, id?, status?, reason?, label? }`
- Cap **200** entries in `meta["steps"]`.
- Persist on `publish_stage` / `publish_step` / `publish_terminal` when out dir bound (`EVENTS.bind_out`).
- `GET /status` includes `steps` (running + terminal payloads where meta is read).
- Late SSE join: if bus empty and `meta.steps` non-empty → seed bus from steps (prefer over single-stage seed).

## Client

- `effectiveCraftMode(mode, stage)` → `presentation` when stage is `slides_*`.
- Distinct RU labels in `craftTemplate` per mode (polish only).
- `hydrateCraftFromSteps(steps)` → `{ stage, substeps, skipped }`.
- Poll / status path applies hydrate when `steps` present.
- ThinkingFold uses `effectiveCraftMode`.

## Non-goals

- Sound, film replay from steps, fake CoT, desk health.
