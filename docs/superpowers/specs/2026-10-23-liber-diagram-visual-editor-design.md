# Liber visual diagram editor — Design

**Date:** 2026-10-23  
**Status:** approved (user: manager · light structure · modal 90% · React Flow + IR)  
**Amends:** diagram-edit-legend · ADR-0007

## Goal

Менеджер правит схему **без Mermaid**: текст, роль/цвет, добавить/удалить блок, стрелки и подписи. Сохранение → Mermaid → существующий `POST …/diagrams/{id}/edit`.

## Shell

Modal ~90%: canvas (React Flow) + правый inspector. [Отмена] [Сохранить].

## Data

`DiagramIR`: nodes `{id,label,kind}`, edges `{id,source,target,label?}`, `direction`, `title`.  
Parse/serialize flowchart subset only. Non-flowchart → fallback message + keep raw Mermaid sheet.

## Non-goals v1

Sequence/mindmap edit · free drag layout persistence · Miro swimlanes · collaborative cursors · free hex colors · multi-select · LLM in-canvas rewrite · live React Flow outside modal · PDF of diagrams.

## Subset (support / refuse)

**Support:** `flowchart TD|LR`; nodes `[]`/`{}`/`()`/`[[]]` mapped to kinds; `A --> B` / `A -->|lbl| B`; `:::role` + Liber `classDef` (six roles).  
**Refuse:** subgraph / chains `A-->B-->C` / sequence·mindmap·… / `click` / custom styles / dotted-thick edges as truth. Gate: `isSupportedFlowchartSubset`.

## UX risks (from design review)

1. Drag positions ≠ Mermaid layout after Save — set expectations (layout is Mermaid’s).  
2. Orphan edges after delete — clean edges on node delete (done).  
3. Role vs shape — kind drives shape+color, not free hex.  
4. Decision exits — prefer Да/Нет chips; validation TBD (warn vs block).  
5. Save anxiety — dirty confirm (done); optional live Mermaid preview later.

## Open product choice

Save when decision has ≠2 labeled exits: **warn** (allow) vs **block** — decide before next editor polish.

## See

Plan: `docs/superpowers/plans/2026-10-23-liber-diagram-visual-editor.md`  
Review notes: [Diagram editor UX review](0a597914-4274-42e9-aafe-ef49a8816c0f)
