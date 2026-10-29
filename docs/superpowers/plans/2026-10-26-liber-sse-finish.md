# Liber SSE finish Implementation Plan

> **For agentic workers:** TDD; no sound; commit only if owner asks.

**Goal:** Mode-aware craft scripts + durable `meta.steps[]` (seed SSE / hydrate UI).

**Architecture:** `RunEventBus.bind_out` persists compact steps into `meta.json`; client hydrates + switches template on `slides_*`.

**Tech:** Python bus + meta RMW · TS `craftSteps` · status/SSE API · App poll path.

## File map

| File | Role |
|------|------|
| `src/case3/run_events.py` | bind_out, persist steps, seed_from_steps |
| `src/case3/api.py` | bind on start; status.steps; events seed |
| `tests/test_sse_finish.py` | persist + seed |
| `web/src/domain/craftSteps.ts` | effectiveCraftMode, hydrate, labels |
| `web/src/domain/craftSteps.test.ts` | unit tests |
| `web/src/ThinkingFold.tsx` | effectiveCraftMode |
| `web/src/app/App.tsx` | hydrate from status.steps |
| backlog / desk-live / MEMORY | mark done |

## Tasks

### Task 1: Server meta.steps
1. RED: test_sse_finish — publish stage/step → meta.steps; seed bus from steps.
2. GREEN: bind_out + persist + seed_from_meta_steps.
3. Wire api start + events join + status `steps`.

### Task 2: Client mode + hydrate
1. RED: craftSteps tests for effectiveCraftMode + hydrateCraftFromSteps.
2. GREEN: implement + ThinkingFold + App status hydrate.
3. Polish template labels.

### Task 3: Docs
Update backlog-deferred, desk-live, MEMORY.
