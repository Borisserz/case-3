# Liber report depth — C1 paragraph edit · C2 Source citations · C4 landscape tables

**Status:** Approved (owner 2026-10-25; approach B for C1)  
**Backlog:** [`docs/knowledge/backlog-deferred-2026-10-25.md`](../../knowledge/backlog-deferred-2026-10-25.md) §C  
**Out of scope:** deferred B, rejected A3/A9, C3/C5/C6/C7

## Goals

1. **C1** — Edit prose paragraphs in Preview like tables: patch TeX → re-render PDF/DOCX → refresh preview. Numbers/facts not invented by the editor (user-supplied text only; escape for TeX).
2. **C2** — Footnotes/cites only when Source has explicit refs (URL, «см. …», bibliography). Never invent citations.
3. **C4** — Too-wide tables get a landscape page (`pdflscape`); normal `tabularx` stays portrait. Smart column-split only if landscape still overflows.

## Design

### C1 — Paragraph edit (mirror `table_edit`)

- Preview paragraphs carry stable `id: "para-N"` (1-based document order), same N as TeX paragraph spans.
- API: `POST /api/runs/{run_id}/paragraphs/{n}/edit` body `{ text, formats? }`.
- Backend `paragraph_edit.py`: find N-th prose span in body (same walk rules as `tex_preview._flush_paragraphs`); replace with escaped plain paragraphs; rebuild via `render_tex`; return fresh preview.
- UI: `ParagraphEditSheet` + «Изменить» on paragraph blocks in `ReportView` (sheet under block, ⌘↵ save) — same busy/`editingFigureId` lock pattern as tables (`para:N`).
- Complex TeX (math-heavy, multi-command) still editable as plain text; round-trip may lose rare markup (document as trade-off; prefer escape + newlines → `\par`).

### C2 — Citations from Source

- Prompt (`system_tex.md` + intent hints): use `\footnote{…}` / URL footnotes **only** for refs present in Source; if none → no footnotes/cites.
- Optional light harden: strip `\cite{…}` with empty/unknown keys; keep `\footnote` that look like URLs/titles (no invented bibliography DB).
- Do not add biblatex/biber — Liber stays footnote-first with `hyperref`.

### C4 — Landscape wide tables

- Prompt: remove blanket «Never landscape»; allow `pdflscape` `\begin{landscape}…\end{landscape}` wrapping a **single** `table` when columns/content need it.
- Preamble: ensure `pdflscape` package.
- Harden in `tex_preamble` / table post-pass: if table has ≥6 data columns **or** average cell length high **and** not already landscape → wrap that `table` env in landscape. Leave ordinary `tabularx{\textwidth}` alone.
- Split-to-two-tables: only if after landscape still pathological (optional v1 skip; document as follow-up). Prefer wrap-first.

## Non-goals

- Section rewrite (B15), async PDF (A3), second report style (A9).
- Editing headings/lists in this batch.
- Pixel-perfect DOCX landscape parity (best-effort via same TeX).

## Verification

- pytest: paragraph patch round-trip; citation prompt/harden unit; landscape wrap detection.
- `cd web && npm run build`.
- Manual: Preview → edit paragraph → PDF updates; Source-with-URL → footnote; wide table → landscape page.
