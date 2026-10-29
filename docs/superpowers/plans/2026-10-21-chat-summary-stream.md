# Chat Summary Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stream a short LLM prose summary into Liber chat while PDF renders, grounded on a document outline.

**Architecture:** After inject, pipeline runs `render_tex` and `generate_chat_summary` in parallel. Summary tokens go to a per-run queue + final `meta.chat_summary`. FastAPI SSE endpoint fans out tokens; UI EventSource updates the bot bubble with light markdown.

**Tech Stack:** Python 3 + FastAPI StreamingResponse/SSE, existing `LLMClient`, React + Vite, fetch EventSource/polyfill via `fetch` stream if needed.

## Global Constraints

- Numbers/facts only from outline (Source-driven product rule).
- Summary failure must not fail the PDF run.
- No purple AI-slop UI; match soft-premium Liber tokens.
- Do not commit `runs/`, `.env`, secrets.

## File map

| File | Responsibility |
|------|----------------|
| `src/case3/chat_summary.py` | Outline from TeX/preview; prompt; stream/complete helpers |
| `src/case3/summary_bus.py` | Per-run token queues + replay buffer |
| `src/case3/llm_client.py` | Add `stream()` yielding text deltas |
| `src/case3/pipeline.py` | Parallel summary during latex |
| `src/case3/api.py` | SSE route; payload fields |
| `web/src/lightMd.tsx` | Shared light markdown → HTML |
| `web/src/App.tsx` | Open stream on latex; render summary |
| `web/src/styles.css` | `.msg-md`, streaming caret |
| `tests/test_chat_summary*.py` | Outline, prompt, bus, API SSE |
| `.agents/knowledge/KI-liber-ui.md` | Note summary stream |

---

### Task 1: Outline + prompt (TDD)

**Files:** `src/case3/chat_summary.py`, `tests/test_chat_summary_outline.py`

- [x] Write failing tests: outline extracts title, headings, captions; strips fluff; prompt mentions no-invention + CTA
- [x] Implement `build_outline(tex) -> str` and `SUMMARY_SYSTEM` / `build_summary_user(outline, intent)`
- [x] Run tests — pass

### Task 2: Summary bus + LLM stream (TDD)

**Files:** `src/case3/summary_bus.py`, `src/case3/llm_client.py`, `tests/test_summary_bus.py`, `tests/test_llm_stream.py`

- [x] Bus: `publish(run_id, delta)`, `finish(run_id, text, status)`, `subscribe` iterator with replay
- [x] `LLMClient.stream(...)` parses OpenAI SSE `data: {choices[0].delta.content}` until `[DONE]`
- [x] Tests with fake socket / mock — pass

### Task 3: Pipeline parallel (TDD)

**Files:** `src/case3/pipeline.py`, `tests/test_pipeline_summary_parallel.py` (mock LLM + render)

- [x] After inject: ThreadPool — render + summary; write `meta.chat_summary` / `summary_status`
- [x] dry_run or missing VISION → `summary_status=skipped`, no crash
- [x] Tests — pass

### Task 4: API SSE + payload

**Files:** `src/case3/api.py`, `tests/test_api_summary_stream.py`

- [x] `GET /api/runs/{run_id}/summary/stream` → SSE
- [x] `_run_result_payload` includes `chat_summary`, `summary_status`
- [x] Tests — pass

### Task 5: Liber UI stream + markdown

**Files:** `web/src/lightMd.tsx`, `web/src/App.tsx`, `web/src/styles.css`, `web/src/SourcePane.tsx` (optional reuse)

- [x] Extract light markdown helper
- [x] On poll stage `latex`/`docx`, open EventSource; update bot `text`; caret while streaming
- [x] On ok use `result.chat_summary`; fallback «Отчёт готов»
- [x] Manual or smoke: `?preview=artifact` still works

### Task 6: Docs + verify

- [x] Update KI-liber-ui (+ KI-pipeline one line)
- [x] Run focused pytest + `npm run build` (or tsc) for web
- [x] verification-before-completion

---
