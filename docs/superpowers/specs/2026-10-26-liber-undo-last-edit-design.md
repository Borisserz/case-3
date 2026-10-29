# Liber B21 — Undo last edit

**Date:** 2026-10-26  
**Status:** shipped 2026-10-26 (depth A = one undo; approach 1 = server `.undo/` snapshot)  
**B19 batch recolor:** rejected — out of scope forever unless re-opened

## Goal

After a successful Liber edit (chart / photo / table / paragraph / diagram), one **Отменить** restores the previous run artifacts and rebuilds PDF/DOCX. No stack; next edit overwrites the undo slot.

## Server

- Module `case3/run_undo.py`:
  - `capture_before_edit(out_dir, *, kind, target)` → write `out/.undo/` (tex, figures.json, meta.json, figures PNGs that exist, diagrams.json if any)
  - `commit_undo_slot(out_dir)` / mark `meta.undo = {kind, target, ts}` after edit OK
  - `apply_undo(out_dir)` → restore files, clear slot, `render_tex` like edits
- Hook: start of `edit_*_in_run` (and diagram edit) calls capture; on success set undo meta; on failure discard if current matches.
- `POST /api/runs/{run_id}/undo` → `{status, preview, downloads, undo: null}`
- Edit responses include `undo: {kind, target}` when slot ready

## Client

- After edit OK with `undo` → toast/bar «Отменить» (Quiet Mono, not a plaque chip)
- Click → POST undo → refresh preview/downloads; hide control
- Esc / second edit clears affordance when server says no undo

## Out of scope

- Multi-step stack, redo, slides IR reorder undo (unless same snapshot covers), chat-only `/api/photo/edit`
