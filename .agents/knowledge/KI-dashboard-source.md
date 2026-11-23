# KI: Dashboard source (PNG + PDF → markdown)

## What
Turns a Stimulsoft screen and a born-digital table PDF into markdown. This is the data the analysis chat will read. Not Liber Source ingest, not Image API.

## Entry
- `POST /api/dashboard/parse` — multipart `png` and/or `pdf`. Composer: «Выбрать данные» → «В данные». Settings has no Stimulsoft block
- `dashboard_source.parse_dashboard(png=..., pdf=..., vision=...)`
- `dashboard_source.read_dashboard_png(png, client=...)` — Qwen only
- `dashboard_source.table_block` / `join_page_tables` — cell markdown, no I/O
- Prompt: `prompts.load("dashboard_png")`
- Vision client: `LLMConfig.from_env()` (`VISION_*`), temperature forced to 0.1, reasoning off, max_tokens min(4096, env)

## Invariants
- PDF numbers are the cell strings. Neighbour duplicates stay. No 12-column cut from `source_ingest`
- Caps: 64 columns, 500 rows, 20 MB PDF, 15 MB PNG. Over the cap, the markdown itself says «Таблица обрезана: было …, осталось …». The same sentence is a warning.
- PNG must be PNG magic. JPEG is not accepted on this path
- A PDF without a usable text layer raises `DashboardSourceError` code `scan_pdf`
- Combined markdown has `# Данные дашборда`, then `## Экран` and/or `## Таблица PDF`, then `## Производные` when a numeric column has two or more rows.
- Shares are one decimal and sum to 100%. A row whose label starts with «Итого», «Всего», «Total», «Sum» or «Сумма» is not divided. «Итоговый» stays a row. A year column is not divided. A column that is already a percent is left alone. `105865` without thousand spaces is still one number and gets a share.
- One side may fail and the other still returns: the failure text is in `warnings`. Both empty → error
- Ruled grid (lines) wins over a noisier text-split of the same page

## Gotchas
- `source_ingest._cells_to_tsv` still drops a repeated neighbour and cuts at 12 columns. Do not point the dashboard at it
- Ruled lines win when they keep each printed number whole. A Stimulsoft pivot often has only horizontal rules, so the cells come from word positions: `105 865,2` stays one cell, and a wrapped header joins (`Выполнение` + `плана (%)`). The text strategy is only a fallback: it was splitting those into 12–13 columns.
- Beside a PDF, the screen block is filters, cards and the chart. A section named like «таблица на экране» and any grid wider than four columns is dropped, because the PDF cells are the numbers. A screenshot with no PDF keeps that grid, and the vision prompt is `dashboard_png_only`.
- The settings modal that drew an HTML grid is gone. The viewer is `DashboardPickModal` («Выбрать данные»)
- Composer paperclip PDF uses the same cell markdown as «В данные» (64×500, repeated neighbours stay). A PNG on the paperclip is read as dashboard text. A JPEG stays a photo. If the PNG read fails, the file is not attached as a photo. The toast says the snapshot was not read.
- A drop whose target is inside `.stimul-modal` must not reach the desk `onDrop`. Otherwise the PDF becomes a report Source
- Composer «Выбрать данные» iframes his `/viewer`. «В данные» calls `POST /api/dashboard/service-capture` → `GET {base}/shot`. Paths are read on the same machine. `parse_dashboard` once: PNG plus joined table PDFs. One markdown (`# Данные дашборда`, `## Экран`, `## Таблица PDF`).
- A chat sentence that asks for dashboard data (`POST /api/dashboard/phrase`) calls `GET /filters` on the Stimulsoft service (queries on, so `filters_mrt.extract_filters` fills choices and `value`). «Открой дашборд» with no named filter still opens: the POST body is every filter's current `value`, coerced to the choice key (`month: 2`, `vtypevd: "0000000"`). A named choice overrides only that field. The phrase path `POST`s `{"filters": {...}}` to `/open?open=0` and the iframe loads `/open` (the page that POST raises). `GET /shot` runs only when the user presses «В данные». The button path stays on `/viewer` and does not call `/filters` or `/open`. `filters_mrt.py` lives in the Stimulsoft repo and is imported by that service from `local/`.

## See
ADR-0014 · `prompt/dashboard_png.md` · `tests/test_dashboard_source.py`
