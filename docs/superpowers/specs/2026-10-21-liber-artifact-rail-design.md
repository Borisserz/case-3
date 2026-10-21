# Liber Artifact Rail — Design

**Date:** 2026-10-21  
**Status:** approved (chat A · tabs B · attach/plaque C)

## Goal

Julius-style split: chat stays conversational; heavy artifacts open in a right **Artifact rail** with motion.

## Behavior

1. **Report ready** — chat shows short «Отчёт готов» + `ArtifactCard`; rail auto-opens on tab **PDF**. Tabs: Превью · PDF · Source.
2. **Export ▾** — dropdown PDF / DOCX (rail header + card).
3. **Attach .txt/.md** — FileReader → rail tab Source; chip stays in composer.
4. **Long text (>400 chars)** — `ContextPlaque` above messages; click opens rail Source/intent.
5. **Narrow (<900px)** — rail overlay; Esc / × close.

## State

`activeArtifact: null | { kind: "report"|"source"|"intent", msgId?, tab, title?, text?, fileName? }`

## Components

| File | Role |
|------|------|
| `ArtifactRail.tsx` | Split panel, tabs, Export, hosts ReportView / PdfFirstPage / source |
| `ArtifactCard.tsx` | Compact chat card + Смотреть / Export |
| `ContextPlaque.tsx` | Collapsed source/intent chip bar |
| `ExportMenu.tsx` | Shared PDF/DOCX dropdown |

## Out of scope (v1)

Data Explorer, DOCX preview, PPTX, persist rail across reload (restore last report still opens rail).

## ADR note

Extends ADR-0003: still chat-first; rail is artifact focus, not a settings form.
