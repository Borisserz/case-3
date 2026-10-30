# Liber prompt catalog

**Edit prose here.** Python only assembles vars / calls the model.  
Loader: `case3.prompts.load(id, **VARS)` · `list_prompt_ids()` · themes via `load_theme`.

| id | file | caller | vars |
|----|------|--------|------|
| `system_tex` | `system_tex.md` | `generate.load_system_prompt` → report LLM | `MAX_IMAGES` `MAX_CHARTS` `MAX_DIAGRAMS` `PALETTE_TABLE` |
| `user_tex` | `user_tex.md` | `generate.build_user_prompt` | `INTENT_BLOCK` `MAX_*` `DIAGRAM_COLOR_TABLE` `SOURCE` |
| `continuation_tex` | `continuation_tex.md` | `generate.build_continuation_prompt` | `MAX_CHARTS` `PARTIAL_TAIL` `SOURCE` |
| `summary_system` | `summary_system.md` | `chat_summary` (system role) | — |
| `system_slides` | `system_slides.md` | `slides_job.load_slides_system_prompt` | `PALETTE` `THEME_OVERLAY` `STRUCTURE_OVERLAY` `CHART_IDS` `FIGURE_IDS` `DIAGRAM_IDS` `MEDIA_CATALOG` `INTENT` `SOURCE` |
| `diagram_generate` | `diagram_generate.md` | `diagram_edit` regenerate | `DIAGRAM_COLOR_TABLE` (+ file placeholders) |
| `diagram_repair` | `diagram_repair.md` | pipeline `diagram_repair` stage | color table appended in code |

## Themes (path-based, not in `PROMPT_FILES`)

| pattern | loader | note |
|---------|--------|------|
| `themes/slides_{pack}.md` | `prompts.load_theme("slides", pack, fallback="atelier")` | deck visual tone |
| `themes/structure_{id}.md` | `deck_structure.structure_overlay` | narrative arc |

## Gold exemplars

| path | loader | note |
|------|--------|------|
| `gold/index.yaml` + `*.tex` | `gold_select` → appended to system after `system_tex` | Intent tag overlap; see `gold/README.md` |

## Not prompt files (code policy)

- `src/case3/image_prompt.py` — brand-safe / pack style-lock / banned n-grams (validators, not LLM system prose).
- `chart_style.palette_fallback_table` / `diagram_style.format_diagram_color_prompt` — generated tables injected as vars.

## How to add a prompt

1. Add `prompt/<name>.md`.
2. Register in `PROMPT_FILES` (`src/case3/prompts.py`).
3. Add a row to this MANIFEST.
4. Call `prompts.load("<id>", ...)`.
5. Extend `tests/test_prompts_catalog.py` if it’s a core role.
