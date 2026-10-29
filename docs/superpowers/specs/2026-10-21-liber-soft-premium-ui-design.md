# Liber Soft-Premium UI — Design

**Date:** 2026-10-21  
**Status:** implemented (Phases 0–3 core)  
**ADR:** [0006](../../adr/0006-liber-soft-premium-ui.md)

## Goal

Mary soft-premium shell anatomy + Julius chat/RHS behavior, Liber brand (olive sage, DM Sans + Crimson), all prior functions preserved.

## Shell

```text
[ Sidebar | Chat column | Artifact rail ]
  New       empty/msgs     Preview·PDF·Source
  History   ThinkingBar    Export · TOC
  Settings  pill composer
```

## Charts

- Print truth = Playwright PNG (`chart_frame` premium CSS + donut enhance).
- Chat `ChartCard` may show `insight` / `highlights` from Source-only schema fields.
- Edit via existing chart sheet API.

## Out of scope (later)

- Live Chart.js hover in Preview (G12)
- Backend runs history API
- Mobile sidebar drawer overlay
- Feedback thumbs
