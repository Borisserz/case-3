# Liber Preview edit mode — design

**Date:** 2026-10-26  
**Status:** done

## Goal

One top control on **Превью**: **Редактировать** / **Готово**. Reading stays clean; edit affordances appear only in edit mode.

## Behavior

| Mode | UI |
|------|-----|
| Off (default) | No per-block «Изменить» |
| On | «Изменить» on paragraphs, tables, charts, photos (existing sheets) |
| Leave / new run | Close open sheets; `editMode` resets on `runId` change |

Source tab stays read-only. Print truth remains PDF/DOCX after Apply.

## Files

- `web/src/domain/reportEditMode.ts` — helpers + tests  
- `web/src/ReportView.tsx` — bar + gates  
- `web/src/styles/chat.css` — `.report-edit-bar`
