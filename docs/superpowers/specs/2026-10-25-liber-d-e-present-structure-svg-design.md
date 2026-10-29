# Liber D/E — Present polish · slide structure · SVG export

**Date:** 2026-10-25  
**Status:** approved (owner backlog D/E **do** items)  
**Scope:** only these three. Rejected D/E (notes, layout picker, Sequence/ER/Gantt, etc.) stay untouched.

## 1. Present mode polish

**Files:** `PresentationFullscreen.tsx`, `presentation.css`, `PresentationPane.tsx` (Present entry).

**Behavior (Julius-like):**
- Click stage: left ~28% → prev; rest → next. Space / → next; ← prev (existing).
- Idle ~2.2s without mouse/key → hide chrome (count, nav, hint); movement/key → show.
- Esc / backdrop / Esc button → exit. Must not break.

**Note:** core already landed; this task verifies + hardens (touch idle bump, chrome pointer-events).

## 2. Reorder / duplicate / delete (no LLM regen)

**Backend:**
- `slides_patch.apply_deck_structure(deck, op)` — ops: `reorder` | `duplicate` | `delete`.
- `POST /api/runs/{id}/slides/structure` → IR mutate → same coalesce worker as text `PATCH …/slides/ir` → `rebuild_slides_from_deck` only.
- Never `POST …/slides` full job.

**Rules:**
- `reorder`: `order` = permutation of existing slide ids.
- `duplicate`: deep-copy slide after source; new unique `id` (`sNN` style).
- `delete`: refuse if only one slide left; confirm in UI before call.
- After op: write `deck.json`, rebuild twin PNGs + PPTX; UI polls `GET …/slides` like text patch.

**UI:**
- Filmstrip + gallery: drag-reorder.
- Toolbar (slide view): «Дублировать» · «Удалить» (confirm).
- Busy: disable structure controls while `slides_stage=patch`.

## 3. Схема → SVG export

**Client:** `downloadDiagramSvg` (serialize Mermaid SVG, download `.svg`) + button next to PNG in `DiagramPane` (+ fullscreen if PNG exists there).

**API:** `GET /api/runs/{id}/diagrams/{diagram_id}/svg` — render Mermaid→SVG via same Playwright path as PNG (return `image/svg+xml`). Button prefers live DOM; API for parity / headless.

## Out of scope

Speaker notes, layout insert, aspect ratios, Google/Keynote, pack motif/veil parity, deck-from-report picker, Sequence/ER/Gantt whitelist, legend sync, version diff, media_hero one-click.
