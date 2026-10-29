# Liber report depth C1/C2/C4 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` or implement in-session with TDD. Spec: `docs/superpowers/specs/2026-10-25-liber-report-depth-c1-c2-c4-design.md`.

**Goal:** Ship paragraph Preview edit, Source-only citations, landscape wide tables.

## File map

| Area | Files |
|------|--------|
| C1 backend | `src/case3/paragraph_edit.py` (new), `tex_preview.py` (para ids), `api.py` |
| C1 UI | `web/src/ParagraphEditSheet.tsx`, `ReportView.tsx`, `App.tsx`, `ArtifactRail.tsx`, styles |
| C2 | `prompt/system_tex.md`, `api.py` intent hints, optional `tex_preamble.py` / harden |
| C4 | `prompt/system_tex.md`, `generate.py` hints, `tex_preamble.py` (pdflscape + wrap) |
| Tests | `tests/test_paragraph_edit.py`, `tests/test_landscape_tables.py`, `tests/test_citations_source.py` |
| KI | `.agents/knowledge/KI-liber-ui.md`, `KI-tex-render.md` |

## Tasks

### Task 1: C1 paragraph TeX spans + preview ids
- [ ] Assign `id: para-N` in `_flush_paragraphs` / `tex_to_preview_blocks`
- [ ] `find_paragraph_spans` + `patch_paragraph_in_tex` + `edit_paragraph_in_run`
- [ ] Tests RED→GREEN

### Task 2: C1 API + Liber UI
- [ ] `POST …/paragraphs/{n}/edit`
- [ ] `ParagraphEditSheet` + ReportView/App wiring
- [ ] `npm run build`

### Task 3: C2 citations prompt + harden
- [ ] Prompt rules; intent hint when Source has URLs
- [ ] Unit test: no invented cite instruction; source-url → allow footnote

### Task 4: C4 landscape
- [ ] `pdflscape` in REQUIRED_PACKAGES; wrap-wide-table harden
- [ ] Prompt allow landscape for wide tables only
- [ ] Tests for wrap / leave tabularx alone

### Task 5: Verify
- [ ] pytest touched + web build; KI notes; short summary
