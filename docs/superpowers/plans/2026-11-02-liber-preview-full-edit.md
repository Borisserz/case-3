# Liber Preview full edit — Implementation Plan

> **For agentic workers:** execute task-by-task with TDD. Checkboxes track progress.

**Goal:** Full-open Preview edit: inline prose/headings/lists + always-open media sheets; new heading/list TeX patch APIs.

**Architecture:** Mirror `paragraph_edit` for headings and lists; ReportView drops per-block «Изменить» and mounts editors when `editMode`.

**Tech Stack:** FastAPI, pytest, React/TS, existing rebuild_run_docs

## Global Constraints

- Numbers/facts only from Source (no inventing)
- PDF truth after Apply
- Do not commit runs/, .env, secrets

---

### Task 1: Heading TeX patch (backend)

**Files:** `src/case3/tex_preview.py` (find_heading_spans), `src/case3/heading_edit.py`, `tests/test_heading_edit.py`, `src/case3/api_edits.py`

- [x] RED: tests for find spans + patch Nth section
- [x] GREEN: implement + API route
- [x] Verify pytest

### Task 2: List TeX patch (backend)

**Files:** `src/case3/tex_preview.py` (list ids + find_list_spans), `src/case3/list_edit.py`, `tests/test_list_edit.py`, `src/case3/api_edits.py`

- [x] RED: tests for list-N ids + patch items
- [x] GREEN: implement + API route
- [x] Verify pytest

### Task 3: Frontend domain + ReportView UX

**Files:** `web/src/domain/reportEditMode.ts(+test)`, `reportPreview.ts`, `ReportView.tsx`, sheet `trapFocus`, styles

- [x] RED: helpers for enter-full-edit / toggle visibility includes heading+list
- [x] GREEN: inline editors; expand all; sheets always open; no «Изменить»

### Task 4: Wire edits

**Files:** `useLiberEdits.ts`, `ArtifactRail.tsx`, `App.tsx`

- [x] editHeading / editList → postJsonEdit
- [x] Pass handlers to ReportView
- [x] Run `npm run test:helpers` + targeted pytest
