# Liber table edit in Preview — Design

**Date:** 2026-10-23  
**Status:** shipped (Apply=A, delete=A, sheet=A, structured patch) + polish 2026-10-23  
**Related:** KI-liber-ui · `ReportView` · `table_edit.py` · `figure_edit` / `chart_edit` · ADR-0005 (TeX harden)  
**Polish:** live draft above · hover/always-visible row × · edge +col/+row · ⌘↵ · no «правка на столе» · centered caption · 404 run_id guard

## Goal

В Artifact Preview у каждой таблицы — кнопка «Изменить», как у графиков/фото. Юзер правит **подпись** и **сетку** (заголовки, клетки, +/− строки и столбцы). **Применить** обновляет превью и пересобирает PDF/DOCX (истина печати = превью).

## Decisions (locked)

| Тема | Выбор |
|------|--------|
| Apply | Preview + patch TeX + `render_tex` (как chart/figure) |
| Add/delete rows & cols | Да в v1; нельзя удалить последний столбец / последнюю data-строку |
| UX | Sheet под таблицей (`TableEditSheet`), не модалка и не free-inline |
| Approach | Structured patch — без LLM |
| Identity | 1-based `table_index` в порядке table-env в `.tex` / preview blocks; если есть `\label{tab:…}` — предпочтительно match по label (fallback index) |

## Non-goals (v1)

- LLM «перепиши таблицу»
- Merge cells, rich text, формулы
- Paste из Excel / drag-reorder
- Обязательные `\label{tab:…}` в generate (только opportunistic)
- Правка prose вокруг таблицы
- longtable multi-page edge-cases (best-effort)

## Architecture

```text
ReportView (table block)
  └─ «Изменить» → TableEditSheet
        caption + editable grid + Apply/Cancel
              │
              ▼
POST /api/runs/{run_id}/tables/{table_index}/edit
  { caption, headers, rows }
              │
              ▼
table_edit.edit_table_in_run
  find N-th table → patch caption + tabular(x) body
  → render_tex → build_report_preview
              │
              ▼
App updates preview + downloads (cache bust)
```

### Data model (existing)

```ts
{ type: "table"; caption?: string; headers: string[]; rows: string[][] }
```

API payload mirrors this. All cells plain strings. Empty cell in JSON (`""`) serializes to TeX `~` (keeps column alignment); parse back → `""`.

### Invariants

- No invented numbers: only user-edited / prior Source-derived cells.
- Shared busy lock with chart/figure edit (one edit at a time).
- Rollback `.tex` (and meta if touched) on render failure — same pattern as `figure_edit`.
- Escape all cell/caption text via `escape_tex_text`.

## UI

### Closed state

- `figure.report-table-wrap` + `report-fig-edit` «Изменить».
- Disabled while any run edit is in flight.

### `TableEditSheet`

1. **Подпись** — text input; preview still shows `Таблица N: …` (N from order).
2. **Grid** — header row + data rows; each cell `<input>` (plain).
3. **+ строка** / **+ столбец**; hover affordance to delete row/col with min-size guard.
4. **Отмена** | **Применить** (busy spinner; focus trap like `ChartEditSheet`).
5. Live edits stay in sheet draft; preview block updates only after successful Apply.

Numeric column alignment in read-only preview can keep existing `colIsNumeric` heuristic; after edit, rebuild preview from TeX.

## Backend

### Module `src/case3/table_edit.py`

| Function | Role |
|----------|------|
| `find_table_spans(tex) -> list[span]` | Locate `table` envs that contain `tabular` / `tabularx` |
| `serialize_tabular(headers, rows, *, style)` | booktabs header `\midrule`; colspec `l`/`r` by numeric heuristic |
| `patch_table_in_tex(tex, index, caption, headers, rows)` | Replace caption + body; preserve env kind (`tabular` vs `tabularx{\textwidth}`) when possible |
| `edit_table_in_run(out_dir, index, *, caption, headers, rows, formats?)` | Backup → patch → render → preview; raise `TableEditError` |

### API

`POST /api/runs/{run_id}/tables/{table_index}/edit`

**Body:** `{ "caption": string, "headers": string[], "rows": string[][] }`

**Validation:**

- `table_index` ≥ 1 and exists
- `len(headers) ≥ 1`
- every row length == `len(headers)`
- soft max ~40 columns × 20 rows (400 / payload size guard)

**Response:** same shape family as chart/figure edit (`preview`, downloads, ok/error).

**Errors:** 404 run/index · 400 validation · 500 render (after rollback) → UI shows durable error in sheet.

## Testing

1. **Unit** — parse → patch → parse round-trip (caption, cell edit, add/del row/col).
2. **Unit** — escape `& % _ #` in cells/caption.
3. **API** — 404 missing run; 400 bad shape.
4. **Manual QA** — edit caption + cell + geometry → PDF text matches preview.

## Open impl notes (not blockers)

- Prefer keeping original colspec width mode (`tabularx` + `X`/`p{}`) when only cell text changes; regenerate simple `l`/`r` colspec when column count changes.
- If multiple tables lack labels, index is authoritative for that Apply (document order).
- DOCX rebuild follows existing `formats` / render path used by figure edit.

## Approval trail

- Apply = A (preview + TeX + PDF/DOCX)
- Delete rows/cols = A
- UX sheet = A
- Approach = 1 (structured patch; opportunistic label later)
