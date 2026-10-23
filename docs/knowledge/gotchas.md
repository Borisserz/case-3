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
11. **PPTX / deck** — on-demand slides job; keys `pptx` + `deck_pdf` (not report `pdf`). `deck_pdf` prefers LibreOffice convert of PPTX (`CASE3_SOFFICE`); else PNG stitch. See ADR-0008 / KI-liber-deck.  
    If `slides_status` stuck at **`queued`** with null slides — job never started (old BackgroundTasks path). Fixed: daemon thread + `running/starting` before kick; crashes write `slides_error`. Restart `api.cmd`, retry Make presentation.  
12. **`\textbf{…**` / unclosed `\textbf{`** — LLM closes bold with Markdown or drops `}`; microtype → `Runaway argument` / `MT@prot@check@F@` / fake `enumerate ended by end{document}`. Fixed by `fix_markdown_bold_leaks` + `fix_unclosed_textbf` in `tex_prose.py`.  
13. **`figures failed/skipped: fig_*`** — Image worker (`IMAGE_API_BASE_URL`, usually `:8787`) was down during the run; slots strip from TeX. Start `workers/case3-image` before local runs; load `.env` so `KANDINSKY_MAX_IMAGES≥1`. Deck can still show `cht_*` / `dia_*`.  
14. **Tiny `dia_*` on 16:9** — Prefer `flowchart LR` + multiline labels (`<br/>`); capture crops to ink (see `slides_media.render_mermaid_png`). TD flows look like a thin column on `media_hero`.  
15. **PPTX Y ≈ 777240"** — `float(Inches(x))` is EMUs, not inches. Always `_as_inches` / `.inches` before arithmetic; PowerPoint then piles text top-left / “[Repaired]”.  
16. **Dark deck tables white body** — never hardcode `#FFFFFF` body fill; use theme `table.body_fill` / panel (botanical `#243D32`) or light ink vanishes.  
17. **Composer «Схема»** — `output_mode=diagram` + `formats=none` skips Docker TeX; only Mermaid + chat summary. Don’t expect PDF/DOCX keys.  
18. **Presentation / diagram send** — do **not** gate on Source length or «≥48 chars». Template «Взять» fills composer with `starterPrompt` **only if chat is empty**; otherwise keep user text. Empty chat still needs any non-empty brief or file.
