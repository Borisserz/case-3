# Liber SSE phase 2A — smarter craft progress

**Date:** 2026-10-26  
**Status:** shipped 2026-10-26 (owner: approach server steps + ETA; scope A)  
**Parent:** [`docs/knowledge/desk-live-progress-and-health.md`](../../knowledge/desk-live-progress-and-health.md) §3

## Goal

ThinkingFold shows honest substeps (`cht_*` / `fig_*`), ETA when confident, skipped photos with reason, fast cancel freeze, error hint.

## Server

- `EVENTS.publish_step(parent, id, status, reason?)` → SSE `event: step`
- Pipeline bumps charts/images also emit steps; Image down → photos skipped
- `meta.stage_timings` + desk rolling averages → optional `eta_s` on stage events
- Terminal `error` may include `hint`

## Client

- `openRunEvents` `onStep`
- Nested lines under charts/photos; title `… · ещё ~Ns`
- Skipped craft step + reason; cancel freezes checklist

## Out of scope

Film, post-run recap, sound, durable `meta.steps[]` replay.
