# Liber diagram edit · legend · regenerate — Design

**Date:** 2026-10-23  
**Status:** approved (user: C + pane-only + full regen)  
**Amends:** ADR-0007 · repair+premium

## Goal

В панели «Схема»:

1. Легенда ролей (цвета из Mermaid `classDef` / `:::`)
2. Палитра Settings → hex в prompt/repair
3. Copy Mermaid + PNG
4. Edit Mermaid (textarea · live preview · Apply)
5. «Ещё вариант» = полный переген diagrams (+ repair), без TeX/PDF

## API

| Endpoint | Body | Effect |
|----------|------|--------|
| `POST /api/runs/{id}/diagrams/{dia}/edit` | `{ mermaid, title? }` | sanitize → figures.json |
| `POST /api/runs/{id}/diagrams/regenerate` | `{ palette? }` | LLM diagrams-only + repair |

## Non-goals

Chat-card controls · PDF inject · prose-inline diagrams.
