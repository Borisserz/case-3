# Liber diagram repair + premium shell — Design

**Date:** 2026-10-23  
**Status:** approved (user: approach 2 + «делай и проверяй»)  
**Amends:** ADR-0007 · composer modes · semantic-diagrams

## Goal

В режиме **Схема** (`output_mode=diagram`):

1. Схема **информативна** — структура Source (ветки, роли, решения), не «Начало → Этап 1… → Завершение».
2. Оболочка **premium-карточка** — type badge, сильный title, спокойный chrome, PNG/fullscreen.

## Non-goals

- Repair в report/presentation (только diagram mode).
- Edit Mermaid в UI / второй язык (Graphviz).
- Inject схем в PDF (ADR-0007).

## Architecture

```text
generate_document → draft diagrams[]
       │
       ▼  iff output_mode=diagram ∧ diagrams ∧ ¬dry_run
diagram_repair (2-й LLM) → enriched diagrams[]
       │
       ▼
parse_diagrams (soft-fail → keep draft)
Liber DiagramPane (premium)
```

| Piece | Change |
|-------|--------|
| `prompt/diagram_repair.md` | System: enrich from Source; anti-slop; same JSON schema |
| `src/case3/diagram_repair.py` | Call + parse + soft-fail |
| `pipeline.py` | Stage `diagram_repair` after llm when mode=diagram |
| `prompt/system_tex.md` | Anti-slop rules for first pass |
| `DiagramPane` / CSS / `DiagramChatCard` | Premium shell |
| meta | `diagrams_repaired`, optional `diagrams_draft` in figures.json |

## Repair contract

**In:** Source, Intent, draft `diagrams[]`.  
**Out:** JSON `{ "diagrams": [ { id, title, type, mermaid } ] }` (fence optional).  
**Rules:** labels only from Source; prefer `{decision}` / roles / parallel; forbid generic Этап N; keep whitelist types; ≤ max_diagrams.

**Soft-fail:** empty/invalid/LLM error → keep draft; `diagrams_repaired=false`.

## UI (diagram mode pane)

- Eyebrow: type label (RU) · «Liber · PNG» (короче текущего hint).
- Title: display weight; actions: PNG primary, fullscreen ghost.
- Canvas: paper frame, меньше engineer-hint у zoom.
- Chat card: live preview; Mermaid snip collapsed by default.

## Testing

- Unit: repair parse, soft-fail, anti-slop heuristic.
- Pipeline: mock LLM → repaired mermaid when mode=diagram.
- Manual: regenerate schema mode in Liber.
