# KI: TeX harden + Docker render

## What
Post-LLM TeX repair then `latexmk -xelatex` / pandoc in Docker `case-3:tex`.

## Entry
- Harden: `tex_preamble.ensure_document_preamble` (called from `render.prepare_tex_source`)
- Row repair: `repair_tabularx_row_breaks`
- Render: `render.render_tex` (`--net=none`, optional `reference.docx`)

## Invariants
- Cyrillic via DejaVu + polyglossia/fontspec
- Required packages injected if missing
- Brand `case-3` scrubbed from title/author
- Orphan `%CASE3_*` slots stripped before latexmk

## Gotchas
- Wide tables: cell-per-line `&` → Misplaced `&` without repair
- `titlespec` typo stripped; real package is `titlesec`
- DOCX `reference.docx` = Liberation Serif (+ Heading 3 / Quote / lists); rebuild via `scripts/build_reference_docx.py`
- Captions: `\captionsetup[figure]{name={Рис.}}` / table `Таблица` (D2)
- Chat preview ≠ PDF numbering/chrome

## See
ADR-0005 · `tests/test_repair_tabularx_rows.py` · `tests/test_harden_tables.py`
