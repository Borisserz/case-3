# Liber Deck → Julius parity — Design

**Date:** 2026-10-22  
**Status:** approved-in-principle (user: unlimited quality bar; deck-only style; start now)  
**Amends:** ADR-0008 (PPTX = visual truth)  
**Plan:** [`../plans/2026-10-22-liber-deck-julius-parity.md`](../plans/2026-10-22-liber-deck-julius-parity.md)  
**Refs (Downloads):** `Northstar_Q3_2026_Board_Update.pptx`, `Relay_Q3_2026_Investor_Update.pptx`, `marketing_performance_bold_signal.pptx`

## Goal

Довести Liber presentations до **того же уровня качества, удобства и красоты**, что у Julius:

- editable PPTX (native text / tables / charts),
- web preview на **тех же theme tokens**,
- situational style settings + later template gallery,
- Source-bound numbers only; report PDF/DOCX **untouched**.

## Non-goals

- Changing report Chart.js / TeX / DOCX palette pipeline.
- Pixel-perfect Office antialiasing match (token twin is enough).
- Cloning Julius purple UI chrome (keep Liber soft-premium / Atelier DNA).
- Freeform LLM CSS.

## Product locks

| Lock | Choice |
|------|--------|
| Style scope | **Deck only** |
| Visual truth | **PPTX** (ADR-0008 amended); Liber preview **twins tokens** |
| Placement | Split CTA on «Сделать презентацию» (gear → style sheet) |
| Quality path | Theme packs + enriched IR + native OOXML charts/tables |
| Time | Unbounded iterate until parity bar is met |

## Architecture

```text
DeckStyle UI (localStorage liber.deckStyle.v1)
        │
        ▼  POST /api/runs/{id}/slides  { theme_pack, style_settings }
resolve_deck_theme() → ThemeTokens  (frozen into deck.json.style)
        │
        ├─► system_slides.md + themes/slides_{pack}.md  (narrative only)
        ├─► slides_html / slide_frame  (--deck-* CSS)
        ├─► Liber PresentationPane twin
        └─► slides_pptx_native + charts + tables   ★ visual truth
```

Report path (`chart_style`, TeX, DOCX) stays isolated.

## Theme packs (v1 set)

| id | Julius ref | Motif |
|----|------------|--------|
| `atelier` | Liber default | cream / olive |
| `board` | Northstar | navy / teal, scorecard, Aptos→Calibri |
| `signal` | Bold Signal | charcoal / orange, chapter blocks |
| `relay` (M4) | Relay | ice blue / white |

Pack owns: colors, fonts (+ PPTX fallback), type scale, margins, chart series colors, table chrome, brand mark. LLM never invents hex.

## IR extensions

Keep existing layouts; add:

- `section`, `scorecard`, `callout`
- cross fields: `chapter?`, `takeaway?`, `appendix?`

Renderer owns paint; LLM owns layout choice + Source-bound copy.

## Phases

| Phase | Outcome |
|-------|---------|
| **0** | Spec/ADR/KI + this design |
| **1** | Theme resolve + token twin (HTML+PPTX) + Style sheet UI (no native charts yet) |
| **2** | Native OOXML charts from figures.json (PNG fallback) |
| **3** | Native tables + new layouts + prompt overlays |
| **4** | Pack parity (signal/relay) + gallery + eval goldens + visual QA loop |

## Success bar (parity checklist)

1. PPTX opens in PowerPoint: titles/bullets/KPIs editable; ≥1 native chart; ≥1 native table when Source has table.
2. Liber rail preview uses same primary/accent/paper/ink as PPTX.
3. Style sheet: 4 colors + 2 fonts + live mini preview; persists; applies on next generate.
4. Blind compare vs Northstar/Bold thumbs: density, takeaway titles, chrome motif — “same league”.
5. Report PDF/DOCX unchanged when deck style changes.

## Agent consensus (2026-10-22)

- Backend: token resolver + separate `slides_pptx_charts/tables`; don’t touch `charts.py`.
- Frontend: split CTA + `DeckStyleSheet`; composer Settings stay report-only.
- AI: thin theme overlays; overwrite `theme_id`/`palette` after LLM; numbers gated.
