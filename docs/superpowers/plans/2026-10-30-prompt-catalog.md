# Prompt catalog (A) Implementation Plan

> **For agentic workers:** TDD; verify with full pytest before «готово».

**Goal:** Central `prompts.load` + MANIFEST + extract user/continuation/summary into `prompt/*.md`.

**Spec:** [`../specs/2026-10-30-prompt-catalog-design.md`](../specs/2026-10-30-prompt-catalog-design.md)

## Tasks

1. RED: `tests/test_prompts_catalog.py` — load known ids, replace vars, missing id raises, MANIFEST lists ids.
2. GREEN: `src/case3/prompts.py` + md files + MANIFEST.
3. Wire `generate.load_system_prompt` / `build_user_prompt` / `build_continuation_prompt` + `chat_summary.SUMMARY_SYSTEM`.
4. Prefer `prompts.load` in slides/diagram loaders (same text).
5. Verify: pytest green; `test_chat_summary_outline` / `test_palette_tokens` still pass.
