# Plan: Liber Present · structure ops · SVG

> **For agentic workers:** TDD per task; pytest + `cd web && npm run build` at end.

**Spec:** `docs/superpowers/specs/2026-10-25-liber-d-e-present-structure-svg-design.md`

## Task 1: Present polish

1. Confirm `PresentationFullscreen` click / Space / idle / Esc.
2. Harden: `touchstart`/`touchmove` → `bumpChrome`; keep Esc.
3. Smoke in browser if desk up; else CSS/class review.

## Task 2: Structure ops (TDD)

1. RED: `tests/test_slides_structure.py` — reorder / dup / delete / last-slide refuse / bad order.
2. GREEN: `apply_deck_structure` in `slides_patch.py`.
3. API `POST …/slides/structure` + reuse `_slides_patch_worker`.
4. UI: `PresentationPane` + `DeckGallery` DnD + dup/delete; poll rebuild like text patch.
5. KI-liber-deck note.

## Task 3: SVG export (TDD)

1. RED: client helper or API unit for SVG content-type / diagram missing.
2. GREEN: `downloadDiagramSvg` + DiagramPane button; API GET SVG (Playwright extract or figures path).
3. KI-liber-ui note.

## Verify

```bash
python3 -m pytest tests/test_slides_structure.py tests/test_slides_patch.py -q
# + any new diagram svg test
cd web && npm run build
```
