# Chat summary stream — Design

**Date:** 2026-10-21  
**Status:** approved (LLM summary · prose · SSE parallel with PDF)

## Goal

When a report finishes generating, Liber chat shows a **Cursor/DeepSeek-style assistant message**: short prose about what was built and what is inside, ending with a cue to open the full document — not a bare «Отчёт готов». Tokens stream into the bubble while PDF/DOCX render in parallel.

## Behavior

1. After `inject` (final TeX + media), pipeline starts **two parallel jobs**:
   - A: `render_tex` (stages `latex` / `docx` as today)
   - B: short LLM call grounded on a compact **outline** (title, headings, figure/chart captions, table titles) — not raw TeX preamble
2. Tokens from B publish to an in-process queue keyed by `run_id`.
3. UI: when poll sees stage `latex` (or later), opens `GET /api/runs/{id}/summary/stream` (SSE) and appends deltas into the pending bot bubble with light markdown + caret.
4. On run `ok`: bubble keeps final `chat_summary`; ArtifactCard + rail open as today. Footer line of the summary must invite reading the full document.
5. Failures: if summary LLM fails or times out, fall back to «Отчёт готов» + card. PDF path must not fail because of summary.

## API

| Piece | Contract |
|-------|----------|
| `meta.chat_summary` | Final plain/markdown string (also in status/`_run_result_payload`) |
| `meta.summary_status` | `pending` \| `streaming` \| `ok` \| `error` \| `skipped` |
| SSE `GET /api/runs/{run_id}/summary/stream` | `text/event-stream`: `event: delta` data=JSON `{"text":"…"}`; `event: done` data=JSON `{"text":"…","status":"ok\|error"}`; late joiners get replay of full text then `done` |
| Poll payload | Adds `chat_summary`, `summary_status` |

## Prompt constraints

- Language: same as document / Intent (default RU).
- Length: ~80–180 words, 2–4 short paragraphs; light markdown (`**bold**`, optional short list) OK.
- Facts/numbers only from outline; no invention.
- Tone: calm Liber desk, not hype; end with one sentence pointing to the full document / Preview / PDF.
- `max_tokens` capped (~400); `reasoning=off`.

## UI

- Replace hardcoded `text: "Отчёт готов"` with streamed / final summary.
- Light markdown render in bot bubble (reuse SourcePane-style helper, extracted).
- Streaming: soft caret / pulse on last line; pending stage label can stay under ThinkingBar.
- History restore: show stored `chat_summary` if present, else «Отчёт готов».

## Out of scope (v1)

- Editing regenerating the summary
- Streaming the TeX generation itself
- Multi-language forced switcher
- Persisting SSE across server restart mid-run (meta file is enough after complete)

## ADR / KI

Extends ADR-0003 chat-first: summary is conversation, artifact stays in rail. Update KI-liber-ui + KI-pipeline briefly.
