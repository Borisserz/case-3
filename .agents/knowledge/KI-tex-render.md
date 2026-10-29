# KI: TeX harden + Docker render

## What
Post-LLM TeX repair then `latexmk -xelatex` / pandoc in Docker `case-3:tex`.

## Entry
- Harden: `tex_preamble.ensure_document_preamble` (called from `render.prepare_tex_source`)
- Row repair: `repair_tabularx_row_breaks` (trigger: ≥1 trailing-`&` line)
- Orphan table chrome: `strip_orphan_table_markup` (bare `&` → `\&`, drop midrule outside tabular)
- Prose lists: `tex_prose.harden_prose_lists` (`- `/`• ` → itemize)
- Render: `render.render_tex` (`--net=none`, optional `reference.docx`)
- C8 errors: `pipeline._attach_error_diagnostics` → `failed_charts` + `latex_log_tail` on status

## Invariants
- Cyrillic via DejaVu + polyglossia/fontspec
- Required packages injected if missing
- Brand `case-3` scrubbed from title/author
- Orphan `%CASE3_*` slots stripped before latexmk

## Report depth (C1/C2/C4)
- C1 paragraph edit: `paragraph_edit.py` + Preview `para-N` (`tex_preview.find_paragraph_spans`)
- C2 citations: prompt + `citations.citation_intent_hint`; harden `strip_invented_cites` drops `\cite{…}` without allowed keys; footnotes with URLs kept
- C4 landscape: `pdflscape` in preamble; `maybe_landscape_wide_tables` wraps wide `table` envs; prompt allows per-table landscape only

## Gotchas
- Wide tables: cell-per-line `&` → Misplaced `&` without repair
- `titlespec` typo stripped; real package is `titlesec`
- DOCX `reference.docx` = Liberation Serif, margins 2.2cm, footer PAGE (D8); rebuild via `scripts/build_reference_docx.py`
- After pandoc: `docx_polish.try_polish_docx` (D5: mist header fill, booktabs borders, pad, bold header, numeric right-align; soft-fail)
- Then `docx_lists.try_fix_docx_lists` (C7: plain `- `/`1.` + pandoc lists → Liber `List Bullet` / `List Number` + numPr; soft-fail)
- Then `docx_charts.try_replace_docx_native_charts`: each eligible `cht_*` PNG → native `word/charts/` (Series IR + pack colors); KPI/scatter/photos stay images. Soft-fail. Drops replaced PNG media+rels; suppresses OOXML auto-title (pandoc caption only). Spec `2026-10-26-liber-docx-native-charts-design`.
- Captions: `\captionsetup[figure]{name={Рис.}}` / table `Таблица` (D2)
- D4: title `\rule` under `\maketitle` + floatsep/captionskip (`ensure_liber_print_chrome`)
- Chrome 2.0: section titlespacing + `\parskip`/`\itemsep`; table rules via `tex_tables.harden_table_rules`
- PDF quality smoke: `tests/test_pdf_quality_smoke.py` (needs Docker `case-3:tex`)
- Chat preview ≠ PDF numbering/chrome

## See
ADR-0005 · `tests/test_repair_tabularx_rows.py` · `tests/test_harden_tables.py` · `tests/test_orphan_table_markup.py` · `tests/test_tex_prose_lists.py`
