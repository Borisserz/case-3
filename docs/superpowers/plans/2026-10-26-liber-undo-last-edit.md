# B21 Undo last edit — plan

> Spec: `docs/superpowers/specs/2026-10-26-liber-undo-last-edit-design.md`

## Files

| File | Role |
|------|------|
| `src/case3/run_undo.py` | capture / apply / meta |
| `tests/test_run_undo.py` | TDD |
| `chart_edit.py` / `figure_edit.py` / `table_edit.py` / `paragraph_edit.py` + diagram edit | capture + commit |
| `api.py` | `POST …/undo` + undo in edit responses |
| `web` App + small UndoBar | wire |

## Tasks

1. RED/GREEN `run_undo` + apply  
2. Hook edits + API  
3. UI affordance  
4. Verify  
