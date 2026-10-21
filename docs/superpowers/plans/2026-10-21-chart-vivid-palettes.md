# Chart vivid palettes — Implementation Plan

> **For agentic workers:** Steps use TDD. Spec: `docs/superpowers/specs/2026-10-21-chart-vivid-palettes-design.md`

**Goal:** Punchier `_PALETTES` + area alpha ~0.34; sync prompt/tests/KI.

**Files:** `src/case3/chart_style.py`, `prompt/system_tex.md`, `tests/test_apply_palette.py`, `.agents/knowledge/KI-charts.md`, optionally `web/src/App.tsx` fallback swatches.

## Task 1: Tests (RED)

Update `test_apply_palette.py` for new ocean/atelier hex; add assert on area alpha `0.34` when remapping low-alpha fills.

## Task 2: Palettes (GREEN)

Rewrite `_PALETTES` per spec table.

## Task 3: Prompt + KI + UI fallback

Sync `system_tex.md`; KI one-liner; App.tsx fallback swatches if hardcoded.
