# Liber Deck Live Edit — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Julius-class live editable presentation preview; edits patch IR → rebuild PPTX. Edit existing text/cells only.

**Spec:** [`../specs/2026-10-22-liber-deck-live-edit-design.md`](../specs/2026-10-22-liber-deck-live-edit-design.md)

## File map

| File | Responsibility |
|------|----------------|
| `src/case3/slides_patch.py` | Apply text-only IR patches; preserve layout/media |
| `src/case3/slides_job.py` | `rebuild_slides_from_deck()` without LLM |
| `src/case3/api.py` | `GET` deck IR; `PATCH /slides/ir` |
| `web/src/DeckCanvas.tsx` | Live twin renderer + contenteditable |
| `web/src/DeckEditToolbar.tsx` | Floating chrome (v1 minimal) |
| `web/src/PresentationPane.tsx` | Swap PNG stage ↔ DeckCanvas |
| `web/src/liberTypes.ts` | Deck IR types |
| `tests/test_slides_patch.py` | Patch invariants |

## Tasks

### Task 1: Patch IR helper (TDD)

- RED: cannot change layout; can change title/bullets/kpi/table cell
- GREEN: `apply_deck_text_patch(deck, patch)`

### Task 2: Rebuild without LLM

- `rebuild_from_ir(run_id)` → pptx + pngs from existing deck.json
- Wire API PATCH

### Task 3: GET deck for UI

- Return `deck` + `slide_pngs` on slides status

### Task 4: DeckCanvas

- Render layouts from IR + CSS vars from style
- contenteditable on allowed fields; blur → PATCH

### Task 5: Wire PresentationPane + Edit mode

- Edit toggle; filmstrip keeps PNG thumbs until recapture

### Task 6: Visual craft pass

- Align section/scorecard denser; optional pastel pack later
