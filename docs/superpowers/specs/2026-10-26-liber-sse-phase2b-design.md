# Liber SSE phase 2B — film + recap (no plaques)

**Date:** 2026-10-26  
**Status:** shipped 2026-10-26 (owner: approach 1; film click → rail; recap only on success; **remove** «PDF ГОТОВ» chips)  
**Parent:** [`docs/knowledge/desk-live-progress-and-health.md`](../../knowledge/desk-live-progress-and-health.md) §3 · extends 2A

## Goal

1. **Film:** as each `cht_*` / `fig_*` PNG lands, a Quiet Mono thumbnail strip under ThinkingFold; click opens that media in the artifact rail.
2. **Recap:** on successful `done` only — one chat line like `Собрано за 2:14 · PDF · DOCX · 3 графика · 1 фото`.
3. **Kill plaques:** remove `artifactChips` / «PDF ГОТОВ» / «DOCX готов» entirely (SSE `artifact` kind pulses may stay for internal use; UI must not render them as chips).

## Server

- `EVENTS.publish_film_frame(run_id, id, kind, url)` → SSE `event: film`
  - Emitted once per PNG under `out/figures/` (`cht_*` → chart, `fig_*`/`usr_*` → figure).
  - `url`: `/api/runs/{run_id}/files/figures/{name}` (or existing figures route).
- Extend `scan_artifacts` (or chart/image progress hooks) to emit frames; track `film_seen` like `artifacts_seen`.
- `publish_terminal(..., recap=?)` on success only:
  ```json
  { "event": "done", "recap": { "elapsed_s": 134, "charts": 3, "figures": 1, "formats": ["pdf","docx"] } }
  ```
  - `elapsed_s` from bus start / first stage; formats from scanned artifacts; counts from meta or PNG scan.
- Still out of scope: sound, durable `meta.steps[]`, film on slides-only mid-job (nice-to-have if easy).

## Client

- Remove `artifactChips` prop/UI/CSS plaques; stop appending chip labels in `App.tsx`.
- `openRunEvents` `onFilm` + `onTerminal` recap payload.
- ThinkingFold: horizontal film strip (max ~8 thumbs, overflow scroll); `prefers-reduced-motion` → no fade.
- Click frame → `ActiveArtifact` kind `media` `{ msgId, runId, id, url, title }` → rail shows image.
- On done + recap → bot message gets `craftRecap` string (or replace pending text suffix); fold collapses as today.

## Non-goals

- Replacing download buttons / rail tabs.
- Fake film frames before PNG exists.
- Recap on error/cancel.
