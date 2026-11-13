# Chart types (Chart.js only — honest catalog)

`bar`, `grouped_bar`, `stacked_bar`, `line`, `horizontal_bar`, `donut`, `kpi`, `area`, `scatter`.

Do **not** use heatmap / treemap / waterfall (those need Plotly plugins from another project).

## Type choice (model owns the full chart — G8)

You **choose** each chart’s concrete `charts[].type` from the whitelist and **build matching HTML**.
Do not leave type vague. Pipeline may coerce mismatches, but your job is to pick correctly first.

Playbook (Source shape → type):

- time / trend / by month → `line` (or `area` if fill helps)
- ranking / top-N → `horizontal_bar`
- share / structure / percent → `donut`
- multi-series compare → `grouped_bar` or `stacked_bar`
- single big number → `kpi` (HTML `.kpi`, no Chart.js canvas)
- two numeric series scatter → `scatter`
- simple categories → `bar`

Rules:

- If Intent/UI lists preferred types → use those **in order** for successive charts when the Source supports them; otherwise pick the best fit from the playbook and still emit a complete chart.
- If Intent says AUTO / «на усмотрение» → **you** pick type(s) from Source; never default everything to `bar`.
- `charts[].type` **must match** the Chart.js `type:` / KPI markup you emit (`donut` → `doughnut`, `horizontal_bar` → `indexAxis:'y'`, `kpi` → `.kpi` cards).
- Deliver a **full** chart: honest numbers from Source, Russian labels when Source is RU, legend/axes readable, palette from Intent.

## Chart HTML — design freely (no gold paste)

You **author** each chart’s `html` for **this** Source + Intent. Gold TeX only shows `%CASE3_CHART:id%` placement — **do not** copy gold/HTML recipes, demo labels, or a fixed «default Chart.js» look between runs.

Customization is encouraged: layout chrome, legend placement, radius, cutout, header emphasis, series emphasis — as long as hard rails below hold.

### Hard rails (must)

- Whitelist `charts[].type` only; Chart.js markup must match the Rules mapping above.
- Numbers / % / absolutes in chart **only from Source** (simple share math OK).
- Unique element ids (`c1`, `c2`, …). Fragment only — no `<html>` / CDN / `fetch` / plugins.
- `options.animation = false`. End with `window.__CASE3_CHART_READY=true;`.
- Canvas ≈ **1100×560** (donut square ≈ 520). Host loads Chart.js offline.
- **One named palette per document** — Intent hex/rgba if listed; else pick editorial / ocean / sunset / mono / atelier.

{{PALETTE_TABLE}}

### Visual freedom (do invent layout; don’t invent colors outside palette)

Aim for **print magazine** charts: saturated multi-hue accents from the table (not a single-blue wash), crisp edges, calm whitespace.

**You may vary:**

- Wrapper: bare canvas · `.chart-card` · optional `.chart-kpi-header` (eyebrow / big / context from Source).
- Donut: prefer `.donut-layout` + `.valued-legend` (host CSS) + center `.pct`/`.lbl`; `cutout` ~55–68%; slice `borderWidth` 2–3 white; Chart.js `legend.display:false` when valued list is present. **`labels` = short names only** (`Retail`, not `Retail 42% (210)` — %/abs go in valued-legend columns).
- Bars: `borderRadius` 4–10; category or series colors from **different** palette accents (hue contrast, not luminance-only steps).
- Stacked: `stack` + `scales.*.stacked`; white borders between segments; prefer ≤6 series (merge «прочее» if Source allows).
- Line/area: `tension` 0.15–0.35, `borderWidth` 2–4, optional soft `area` fill from palette.
- **Legend (required when ≥2 series):** `plugins.legend: {display:true, position:'bottom'}` and named `datasets[].label`. Donut → HTML `.valued-legend` instead.
- **Tooltips:** always `plugins.tooltip: {enabled:true}` (Liber hover shows values; print still has the legend).
- Language: Russian labels when Source is RU.

**Don’t:**

- Purple / indigo / violet / neon pink-blue gradients.
- Default Chart.js blue only (`#0b5fff` / `#36a2eb`) on every chart.
- Same-hue pastel ladders for 5+ series (unreadable in print).
- Glow, glassmorphism, invented KPI numbers, paste of prior-run HTML.

### Type → Chart.js mapping (structure only)

| Catalog | Emit |
|---------|------|
| `bar` / `grouped_bar` / `stacked_bar` | `type:'bar'` (+ stacks / multi datasets) |
| `horizontal_bar` | `type:'bar'`, `indexAxis:'y'` |
| `line` / `area` | `type:'line'` (`area` → `fill:true`) |
| `donut` | `type:'doughnut'` + valued legend layout |
| `scatter` | `type:'scatter'`, `pointRadius:10`, `pointHoverRadius:14` |
| `kpi` | HTML `.kpi` / `.kpi-row` — **no** canvas; colors via host CSS vars |

Host frame sets DPR, fonts, default bar radius. Still set `__CASE3_CHART_READY`.
