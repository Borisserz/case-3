# Pipeline action log (ThinkingBar) — Design

**Date:** 2026-10-21  
**Status:** approved (client poll log · ThinkingBar only)

## Goal

Show Cursor-like **pipeline action steps** above the composer while a run is busy — not model reasoning tokens.

## Behavior

1. `ThinkingBar` expands into a step list driven by poll `stage` / `stage_detail`.
2. On each distinct stage(+detail) transition, previous step → done (✓), current → active (spinner).
3. Collapsed header still shows current label + elapsed seconds.
4. Default: expanded while `busy`; clears when run ends.
5. Bot bubble / PipelineFlow unchanged.

## Out of scope

Server `meta.steps[]`, SSE for stages, real LLM `<think>` streaming.
