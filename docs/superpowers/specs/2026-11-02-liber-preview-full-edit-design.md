# Liber Preview full edit — design

**Date:** 2026-11-02  
**Status:** approved → implementing  
**Supersedes UX of:** `2026-10-26-liber-preview-edit-mode-design.md` (toggle stays; per-block «Изменить» removed)

## Goal

One top **Редактировать** on Превью opens a full desk: every section expanded; paragraphs, headings, and lists are inline-editable; chart / photo / table panels are open immediately — no second «Изменить».

## Behavior

| Action | Result |
|--------|--------|
| Enter edit | `editMode=true`, clear collapsed sections, hide «Изменить», show inline editors + all media sheets |
| Leave / new run | Close busy UI; reset `editMode` on `runId` change |
| Paragraph / heading / list | Inline field; save on explicit «Сохранить» → one TeX patch + rebuild |
| Chart / photo / table | Existing sheets always mounted while `editMode`; Apply unchanged |
| Focus trap | Disabled on multi-open sheets (`trapFocus={false}`) |

## Backend (new)

- `POST /api/runs/{id}/headings/{heading_index}/edit` `{ text, formats }` — N-th `\section`/`\subsection` (1-based)
- `POST /api/runs/{id}/lists/{list_index}/edit` `{ items: string[], ordered?: bool, formats }` — N-th itemize/enumerate
- Preview lists gain stable `id: list-N`
- `\title` / report h1 — out of scope

## Frontend

- `ReportView` full-open mode; `reportEditMode` helpers + hint copy
- Wire `onEditHeading` / `onEditList` through ArtifactRail → App → `useLiberEdits`
- Sheets: optional `trapFocus` prop

## Non-goals

- Batch save of all text in one request
- Nested lists
- Source tab editing
