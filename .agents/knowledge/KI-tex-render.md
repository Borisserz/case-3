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
- DOCX `reference.docx` = Liberation Serif, margins 2.2cm, footer PAGE (D8); rebuild via `scripts/build_reference_docx.py`
- After pandoc: `docx_polish.try_polish_docx` (D5: mist header fill, booktabs borders, pad, bold header, numeric right-align; soft-fail)
- Captions: `\captionsetup[figure]{name={Рис.}}` / table `Таблица` (D2)
- D4: title `\rule` under `\maketitle` + floatsep/captionskip (`ensure_liber_print_chrome`)
- Chrome 2.0: section titlespacing + `\parskip`/`\itemsep`; table rules via `tex_tables.harden_table_rules`
- PDF quality smoke: `tests/test_pdf_quality_smoke.py` (needs Docker `case-3:tex`)
- Chat preview ≠ PDF numbering/chrome

## See
ADR-0005 · `tests/test_repair_tabularx_rows.py` · `tests/test_harden_tables.py`
