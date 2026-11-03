# Liber DOCX — center media + `Рис. N.` captions

**Date:** 2026-11-03  
**Status:** approved (owner: approach A — post-pandoc in `docx_polish`)  
**Depends on:** D5 `docx_polish` · pandoc figure → drawing + following caption para

## Goal

Downloaded `{stem}.docx`: every figure/chart image (and native chart drawing) is **centered**; the following caption reads **`Рис. N. …`**, centered, 11pt black ink (not gray/tiny). Match PDF naming (`Рис.` + number + period).

## Flow

1. Pandoc TeX → DOCX (unchanged).
2. `try_polish_docx` (tables + **media/captions**).
3. lists / native charts (unchanged) — caption paras stay after media.

## Rules

- Media para = contains `w:drawing` / `w:pict` / chart graphic; set `jc=center`.
- Caption = next non-empty non-Heading para without media, length ≤300; set center + ink + 11pt.
- If text lacks `Рис.|Рисунок|Fig.|Figure` prefix → rewrite to `Рис. {n}. {text}` (n = 1… in document order).
- Soft-fail; never break package.

## Out of scope

- Table captions, PDF path, changing pandoc/reference Caption style as primary path.
