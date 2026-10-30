# KI — LLM prompts

**Каталог:** [`prompt/MANIFEST.md`](../../prompt/MANIFEST.md)  
**Код:** `src/case3/prompts.py` → `load(id, **vars)` · `load_theme` · `dump_prompts` · `list_prompt_ids()`

## Invariants

- Prose lives under `prompt/` (md). Python wires vars / calls the model.
- `system_tex` = join of `parts/tex/*.md` (`PROMPT_COMPOSITES`); stub `system_tex.md` is not the body.
- `{{KEY}}` substitution only.
- New core role → file / part + register + MANIFEST + catalog/smoke test.
- Gold = `prompt/gold/` via `gold_select` (appended after `system_tex`).
- Image brand-safe / pack lock = `image_prompt.py` (not catalog prose).
- `CASE3_DUMP_PROMPTS=1` → `out/prompts_used/{system,user,continuation}.md`.

## Gotchas

- Source markers `<<<CASE3_SOURCE_*>>>` must stay in sync with `generate.SOURCE_BEGIN/END`.
- `SUMMARY_SYSTEM` is loaded once at import from `summary_system.md`.
- Themes: `themes/slides_{pack}.md`, `themes/structure_{id}.md` — path-based.
- Do not paste full prose back into `system_tex.md` stub.
