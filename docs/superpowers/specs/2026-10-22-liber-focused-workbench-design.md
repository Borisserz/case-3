# Liber Focused workbench — Design

**Date:** 2026-10-22  
**Status:** approved (user: B Focused workbench)  
**Builds on:** Julius empty + modes (`2026-10-22-liber-composer-modes-design.md`)

## Goal

After a report exists: **narrow chat / wide artifact**, one Export (rail only), Presentation CTA primary on the card — Liber DNA, no IA rewrite.

## Post-report UX

```
[ Sidebar | Chat (~36–40%) | Artifact rail (~60–64%) ]
                 ↑ compact card     ↑ Preview·PDF·Презентация·Source
                                    Export ▾ only here
```

| Change | Detail |
|--------|--------|
| Rail default | ~62% (was 55%); chat feels like assistant strip |
| Card Export | Removed — Export lives only in ArtifactRail |
| Card CTA | «Сделать презентацию» / «Презентация» = primary fill; «Открыть» secondary |
| Duplicate labels | Body `aria-label` = «Открыть …», not «Смотреть …» (no double Смотреть) |

## Non-goals

- Separate Report/Deck/Diagram workspaces (approach C)
- Removing rail Export or chat card entirely
