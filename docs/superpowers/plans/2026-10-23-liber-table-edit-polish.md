# Table edit polish — plan

**Goal:** Spreadsheet-feel sheet; preview mirrors draft; less chrome clutter.

| # | Change |
|---|--------|
| 1 | Live draft в таблице выше (как live chart) через `onDraftChange` |
| 2 | Delete × только на hover строки/столбца |
| 3 | `+` на краю grid (+ строка / + столбец); кнопки снизу — дубль |
| 4 | Keyboard: focus caption on open · ⌘/Ctrl+Enter save · Tab по клеткам |
| 5 | Header sheet: без дубля title; badge `N×M` |
| 6 | Numeric cols `text-align:right` в editor |
| 7 | `is-tuning` / busy: dim read table + clearer busy |
| 8 | Guard: пустой заголовок → не Apply, err в sheet |

Non-goals: Excel paste, drag-reorder, merge.
