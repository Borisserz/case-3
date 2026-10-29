# Liber PPTX native charts — Implementation Plan

> **For agentic workers:** Use TDD; verify with pytest + zipfile `ppt/charts/`.

**Goal:** Every eligible `cht_*` in the deck PPTX is a native OOXML chart with pack colors.

**Architecture:** Persist ChartSeriesIR on `figures.json` charts; PPTX reads stored series first; style via pack `chart_series`; ensure ≥1 chart slide when run has eligible data.

**Tech Stack:** python-pptx, existing `slides_pptx_*`, pytest

## Global Constraints

- Numbers only from Source / existing chart HTML (no invented series).
- Chart types whitelist only; KPI/scatter → PNG.
- No Mermaid native.
- Windows desk compatible; no new native deps.

---

### Task 1: Prefer + persist series IR

- Tests in `tests/test_slides_chart_data.py`
- `attach_series_ir`, `series_from_figures_json` prefer `chart["series"]`
- Call attach from chart finalize paths

### Task 2: Multi-chart PPTX + pack colors

- Tests: 2× `cht_*` → 2× `ppt/charts/`
- Improve `add_native_chart` point/series colors

### Task 3: Ensure deck has chart when eligible

- `ensure_deck_chart_slides` in slides_job (or slides_chart_data)
- Inject `chart_hero` if deck has zero `cht_*` but series map non-empty

### Task 4: Wire + docs

- pipeline / chart_edit persist
- KI-liber-deck + backlog A11 → done
- pytest green
