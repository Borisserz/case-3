# HTML charts for case-3

## Goal

LLM emits offline HTML chart fragments; Playwright Chromium screenshots → PNG → `%CASE3_CHART:id%` inject (parallel to Kandinsky figures). Chart types catalog from prototip-repo. If Intent is silent on charts but Source has numbers, model may add charts (type/count/placement). If Intent forbids or names a type — honor it.

## Non-goals

- No `exec` of Python from the model
- No TeX Docker image changes
- No CDN in rendered pages

## Flow

Intent+Source → Qwen (latex + json with `figures` + `charts`) → Kandinsky PNGs → HTML→PNG charts → inject → latexmk/pandoc.

## Env

- `CASE3_MAX_CHARTS` (0 = off)
- `CASE3_CHART_TIMEOUT_S` (default 15)
