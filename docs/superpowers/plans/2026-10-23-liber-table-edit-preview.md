# Liber table edit in Preview — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Edit tables in Artifact Preview (caption + cells + add/delete rows/cols); Apply patches TeX and rebuilds PDF/DOCX.

**Architecture:** Structured patch via `table_edit.py` + `POST …/tables/{index}/edit`; UI `TableEditSheet` under the table (mirrors ChartEditSheet). No LLM.

**Tech Stack:** Python (FastAPI, existing `render_tex` / `tex_preview`), React + Vite (`ReportView`, `App`, `ArtifactRail`).

**Spec:** `docs/superpowers/specs/2026-10-23-liber-table-edit-preview-design.md`

## Global Constraints

- Apply = preview + TeX + PDF/DOCX
- Empty JSON cell `""` → TeX `~`; parse back → `""`
- Max ~40 cols × 20 rows; min 1 col + ≥0 data rows (keep ≥1 header col; cannot delete last data row if only one? Spec: cannot delete last column / last data row — if 0 data rows allowed after delete? Spec says "последнюю data-строку" implies at least 1 data row must remain OR we allow 0. Spec: "нельзя снести последний столбец / последнюю data-строку" — so keep ≥1 data row. If table had 0 data rows originally, allow stay at 0.)
- Escape via `escape_tex_text`
- Shared edit busy lock with chart/figure
- No commit unless user asks

## File map

| File | Role |
|------|------|
| `src/case3/table_edit.py` | find / serialize / patch / edit_in_run |
| `src/case3/api.py` | `TableEditBody` + route |
| `tests/test_table_edit.py` | unit round-trip + escape + validation |
| `tests/test_api_routes.py` | 404 smoke |
| `web/src/TableEditSheet.tsx` | sheet UI |
| `web/src/ReportView.tsx` | edit button + sheet on tables |
| `web/src/App.tsx` | `editTable` fetch |
| `web/src/ArtifactRail.tsx` | plumb `onEditTable` |
| `web/src/styles/chat.css` | table-edit grid styles |
| `.agents/knowledge/KI-liber-ui.md` | one-liner |

---

### Task 1: `table_edit` core (TDD)

**Files:** Create `src/case3/table_edit.py`, `tests/test_table_edit.py`

**Produces:** `find_table_spans`, `patch_table_in_tex`, `validate_table_payload`, `serialize_tabular_body`, `TableEditError`

- [x] Write failing tests (round-trip, escape, add/del col, index OOB)
- [x] Implement until green
- [x] Skip full `edit_table_in_run` Docker render in unit tests (mock or only patch layer)

### Task 2: API route

**Files:** Modify `src/case3/api.py`, `tests/test_api_routes.py`

**Produces:** `POST /api/runs/{run_id}/tables/{table_index}/edit`

- [x] 404 missing run test
- [x] Wire `edit_table_in_run` + preview response like chart edit

### Task 3: UI sheet + wiring

**Files:** `TableEditSheet.tsx`, `ReportView.tsx`, `App.tsx`, `ArtifactRail.tsx`, CSS

- [x] Sheet: caption, grid, +/−, Apply/Cancel
- [x] ReportView button on tables; `editingTableIndex` busy
- [x] App `editTable` → update preview/downloads

### Task 4: Verify + KI

- [x] `pytest tests/test_table_edit.py tests/test_api_routes.py::test_table_edit_404_missing_run -q`
- [x] Update KI-liber-ui one line
- [x] verification-before-completion
