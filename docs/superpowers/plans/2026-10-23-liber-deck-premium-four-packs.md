# Liber deck premium four packs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans. Spec: `docs/superpowers/specs/2026-10-23-liber-deck-premium-four-packs-design.md`

**Goal:** Premium HTML+PPTX craft for `signal` / `relay` / `ink` / `botanical` + 10–12 slide gallery decks.

## File map

| File | Role |
|------|------|
| `src/case3/slides_html.py` + embedded/frame CSS | Twin craft per pack |
| `src/case3/slides_pptx_native.py` | PPTX craft parity |
| `scripts/render_template_previews.py` | 10–12 slides × 4 |
| `web/src/deckTemplatePreviews.ts` | Modal mock density |
| `.agents/knowledge/KI-liber-deck.md` | Note premium craft |

## Tasks

1. Pack CSS signatures in twin (top foil bar, kicker underline, dark card chrome, ink blue accent, botanical veil).
2. PPTX parity (top bar, foil borders, title spacing).
3. Expand DECKS for performance/qbr/investor/launch to 10–12 slides.
4. Render + visual QA all four.
