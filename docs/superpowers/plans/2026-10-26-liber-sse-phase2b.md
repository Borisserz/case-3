# SSE phase 2B — film + recap + kill plaques

> Spec: `docs/superpowers/specs/2026-10-26-liber-sse-phase2b-design.md`

## Files

| File | Change |
|------|--------|
| `src/case3/run_events.py` | `publish_film_frame`, film_seen, recap on terminal, scan PNGs |
| `src/case3/pipeline.py` | pass recap on ok terminal |
| `tests/test_sse_phase2b.py` | film + recap + no chip requirement |
| `web/src/api/runEvents.ts` | onFilm, recap on done |
| `web/src/domain/craftSteps.ts` | `formatCraftRecap`; drop chip labels usage |
| `web/src/ThinkingFold.tsx` | film strip; remove chips |
| `web/src/ArtifactRail.tsx` | `ActiveArtifact` media pane |
| `web/src/app/App.tsx` | wire film/recap; remove chip append |
| `web/src/ChatMessages.tsx` / types / css / previews | clean plaques; show recap |

## Tasks

1. RED/GREEN server film+recap tests  
2. Client helpers + remove chips  
3. ThinkingFold film + rail media  
4. Wire App SSE  
5. Visual `?preview=flow` + build/tests  
