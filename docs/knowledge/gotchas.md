# Gotchas (living list)

1. **Preview ≠ PDF** — Liber shows TeX blocks; trust PDF slider / download.  
2. **Sticky downloads** — must stay `position: static` at end of report.  
3. **horizontal_bar + pale rgba** — harden solidifies; don't regress canvas height.  
4. **tabularx cell-per-line** — without `repair_tabularx_row_breaks` → Misplaced `&`.  
5. **Orphan `&` / `\midrule` outside tabular** — `strip_orphan_table_markup` escapes/drops before latexmk.  
6. **api --reload** — kills long pipelines; prod desk off.  
7. **KPI type + bar canvas** — coerce rebuilds KPI HTML.  
8. **Chart type badge** — hidden from users; keep in `title=` / edit sheet only.  
9. **Image edit fallback** — worker may regenerate without ref photo.  
10. **Fonts** — PDF DejaVu; DOCX Liberation via `reference.docx` (D1).  
11. **PPTX** — not in product; see parked-pptx.md.
