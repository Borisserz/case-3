# Prompt catalog (Approach A) — design

**Status:** approved (owner 2026-10-30) — implement without chat memory.  
**Goal:** One place to find / edit / add Liber LLM prose prompts; no product features.

## Scope

- Add `src/case3/prompts.py`: `prompt_dir()`, `load(name, **vars)`, `list_prompt_ids()`.
- Add `prompt/MANIFEST.md` (human + agent catalog: id → path → caller → vars).
- Move **inline** LLM prose out of Python into `prompt/`:
  - `user_tex.md` ← `build_user_prompt` static scaffold
  - `continuation_tex.md` ← `build_continuation_prompt`
  - `summary_system.md` ← `SUMMARY_SYSTEM`
- Existing md (`system_tex`, `system_slides`, themes, diagrams, gold) stay; loaders may call `prompts.load`.
- **Out of scope:** split `system_tex.md` (B); Prompt Studio UI (C); `image_prompt.py` ban/style dicts (code policy); chat memory.

## Vars convention

Replace `{{NAME}}` only (same as today for `system_tex`). Missing keys → leave placeholder or raise in tests for known ids.

## Verify

pytest + existing prompt-related tests; no FE change required.
