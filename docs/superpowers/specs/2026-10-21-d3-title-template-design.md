# D3 — титул-шаблон + auto title (2026-10-21)

## Goal

Hard TeX title block so the model improvises less on the masthead; when Settings «Название» is empty, the model invents a topical `\title` from Source.

## Behavior (approved A)

1. Settings title empty → model must emit topical Russian `\title{…}` (prompt).
2. Settings title set → `CASE3_DOC_TITLE` + `apply_doc_title` after LLM (override).
3. Post-pass always: `ensure_title_block(tex)` → `\title` + `\author{}` + `\date{\today}` + `\maketitle` (repair/fill; do not invent title if model already provided a non-empty one).
4. Keep `scrub_project_branding` (no case-3 in title/author).

## Out of scope

- Heuristic title from Source (option B).
- Removing Settings field (option C).
- D4 REPORT_STYLE spacing (separate).

## Files

- `prompt/system_tex.md`
- `src/case3/generate.py` — `ensure_title_block`
- `tests/test_doc_title.py`

## Success

- Empty override: model title preserved; author empty; `\date{\today}`; `\maketitle` present.
- Non-empty override: UI title forced.
- Missing pieces repaired without wiping a good model title.
