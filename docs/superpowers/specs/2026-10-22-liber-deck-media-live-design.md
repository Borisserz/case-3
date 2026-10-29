# Liber deck — live LLM + run media (photos / diagrams)

**Date:** 2026-10-22  
**Status:** approved by user (continue A+B + mini media)

## Goal

1. Live LLM path on real `runs/out/*` (not only curated IR).
2. Charts/photos/diagrams from **that run** only.
3. Stronger headings (`kicker` + title).

## Layouts (add)

| Layout | Fields |
|--------|--------|
| `media_hero` | `media_id`, optional `kicker`, `caption` |
| `media_split` | `media_id`, optional `kicker`, `body`/`bullets`, `caption` |

`media_id` ∈ available `{cht_*, fig_*, usr_*, dia_*}` from run `figures/` + `figures.json` diagrams.

## Resolution

- `cht_*` / `fig_*` / `usr_*` → `out/figures/{id}.png`
- `dia_*` → render Mermaid from `figures.json` → PNG via Playwright + local `mermaid.min.js` (from `web/node_modules` or vendored template)

## Prompt

Pass `{{CHART_IDS}}`, `{{FIGURE_IDS}}`, `{{DIAGRAM_IDS}}`. LLM must not invent ids.

## Out of scope

Editable PPTX; new theme skins.
