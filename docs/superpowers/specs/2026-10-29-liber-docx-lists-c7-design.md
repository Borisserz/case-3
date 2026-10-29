# Liber C7 — DOCX lists (itemize / enumerate)

**Status:** Approved (owner 2026-10-29)  
**Backlog:** [`docs/knowledge/backlog-deferred-2026-10-25.md`](../../knowledge/backlog-deferred-2026-10-25.md) §C7

## Goal

After pandoc, Word lists from TeX `itemize` / `enumerate` use Liber `List Bullet` / `List Number` styles (reference.docx), with correct bullet vs 1.2.3. numbering and nesting depth ≤2 — not plain Normal paragraphs.

## Approach

Post-pandoc soft-fail pass `docx_lists.try_fix_docx_lists` (same pattern as `docx_polish` / `docx_charts`), called from `render.render_tex` after polish, before native charts.

## Behavior

1. Walk body paragraphs; detect list items via existing `w:numPr`, pandoc list styles, or plain-text markers (`- `, `• `, `1. `, `1)`).
2. Apply `List Bullet` or `List Number`; set/ensure numbering (`numId` / `ilvl` 0–1).
3. Strip leading marker text when promoting plain paragraphs so Word does not double-prefix.
4. Soft-fail: exception → log warning; DOCX still returned.

## Non-goals

- Nesting >2, custom bullet glyphs, pixel-perfect PDF spacing parity, changing PDF/TeX path.

## Verification

- pytest: fixture DOCX with itemize/enumerate-like paragraphs → styles + numPr.
- Optional: one TeX→pandoc smoke if Docker available (not required for unit green).
