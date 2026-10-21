# Design: Vivid chart palettes (print ≈ Liber preview)

**Date:** 2026-10-21  
**Status:** Approved (approach A, intensity «как превью»)  
**ADR/KI:** updates `KI-charts.md`; no new ADR (palette values only)

## Goal

Make Chart.js colors (LiveChart + Playwright PNG → PDF/DOCX) noticeably more saturated so print charts feel closer to the Liber site preview. Same palette ids; no purple/indigo slop.

## Decision

Rewrite `_PALETTES` in `src/case3/chart_style.py`:

- Punchier primary + accents (editorial / ocean / sunset / atelier; mono higher contrast)
- Area fill alpha **0.16 → ~0.34**
- Grid stays soft (~0.09–0.10)

Sync: `prompt/system_tex.md` fallback table + recipes, tests, KI one-liner. `/api` swatches come from `palette_public()`.

## Out of scope

PDF/DOCX typography (REPORT_STYLE), Playwright DSF, soft/vivid UI toggle, new palette ids.

## Target hex (no purple)

| id | primary | accents (first 3) | area |
|----|---------|-------------------|------|
| editorial | `#0F3D3E` | `#F07A3A` `#2EC4B6` `#E8B84A` | `rgba(46,196,182,0.34)` |
| ocean | `#0B4F8C` | `#1E8AD4` `#2EC4E0` `#5ED4F0` | `rgba(46,196,224,0.34)` |
| sunset | `#8B2E4A` | `#F04545` `#FF8C2A` `#F0C040` | `rgba(255,140,42,0.34)` |
| atelier | `#2E4208` | `#4F6B14` `#7A9A28` `#B8D45A` | `rgba(122,154,40,0.34)` |
| mono | `#1A1F28` | `#3A4250` `#5C6570` `#8B939E` | `rgba(26,31,40,0.18)` |

## Verification

- `pytest tests/test_apply_palette.py tests/test_harden_horizontal_bar.py -q`
- Visual: Liber preview + PDF after one re-run with ocean/atelier
