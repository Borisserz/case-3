# KI: Charts

## What
LLM HTML (Chart.js) → sanitize → Playwright PNG → inject; Liber edit restyles.

## Entry
- Gen: `charts.generate_all_charts` after coerce/`polish_charts`
- Edit: `POST /api/runs/{id}/charts/{cid}/edit` → `chart_edit.edit_chart_in_run`
- Types: `chart_html.CHART_TYPES`; coerce: `chart_types_coerce.py`
- Palette: `chart_style.apply_palette_to_html` + `palette_from_intent` (vivid ladders 2026-10-21; area α≈0.34); D10 `palette_fallback_table` → prompt `{{PALETTE_TABLE}}`
- G2: `charts[].palette` stamped in polish/edit → preview `palette` seeds ChartEditSheet
- Print legend: `.valued-legend` ≥18px in `chart_frame.html`; D7 width ≤0.92`\textwidth`, canvas h≤560
- Multi-chart (≥2): polish clamps width to 0.82; donut legend col `minmax(320px,1fr)`

## Invariants
- Whitelist types only; donut = Chart.js `doughnut`; hbar = `indexAxis:'y'`
- KPI = HTML cards, not canvas
- Frame CSP + abort non-file routes in Playwright
- After gen: polish palette + harden hbar geometry/fill

## Gotchas
- Type change often triggers LLM even when coerce enough (UX roadmap G3)
- G8: model picks concrete `charts[].type` + matching HTML (prompt playbook); coerce only safety net
- KPI palette via CSS vars (`apply_kpi_palette_vars`) — frame `.kpi` uses `--kpi-value`, not hardcoded orange; palette-only edit on KPI skips Chart.js remap
- Donut premium: `enhance_donut_html` after polish when labels/data parseable; else prompt `.donut-layout` recipe
- Tall `#mount` min-height removed — don't bring back 600px empty band
- Edit rebuilds full PDF/DOCX by default

## See
ADR-0002 · `prompt/system_tex.md` chart recipes · tests `test_harden_horizontal_bar`, `test_coerce_*`
