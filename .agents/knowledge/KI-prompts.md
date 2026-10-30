# KI — LLM prompts

**Каталог:** [`prompt/MANIFEST.md`](../../prompt/MANIFEST.md)  
**Код:** `src/case3/prompts.py` → `load(id, **vars)` · `load_theme(kind, pack)` · `list_prompt_ids()`

## Invariants

- Prose lives under `prompt/` (md). Python wires vars / calls the model.
- `{{KEY}}` substitution only (same as legacy system_tex).
- New core role → file + `PROMPT_FILES` + MANIFEST row + catalog test.
- Gold = `prompt/gold/` via `gold_select` (appended after `system_tex`).
- Image brand-safe / pack lock = `image_prompt.py` (not catalog prose).

## Gotchas

- Source markers `<<<CASE3_SOURCE_*>>>` must stay in sync with `generate.SOURCE_BEGIN/END`.
- `SUMMARY_SYSTEM` is loaded once at import from `summary_system.md`.
- Themes: `themes/slides_{pack}.md`, `themes/structure_{id}.md` — path-based, not in `PROMPT_FILES`.
