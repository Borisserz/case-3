# Liber Premium Craft Pass v2 — Design

**Date:** 2026-10-22  
**Status:** implemented  
**Parent:** [premium-ui-refactor](2026-10-22-liber-premium-ui-refactor-design.md)

## Goal

Second craft pass: empty-home and templates must feel **editorial Atelier**, not CSS demos. Keep olive/paper; borrow Julius stage structure only.

## Signature

**Template cards as real slide frames** — caption under the frame (ink), mock type large enough to read, pack colors only (no sky/teal/SaaS blue). Empty home gets a soft olive radial stage so the desk doesn’t feel blank paper.

## Changes (v2)

1. Template mocks: bigger type, fewer elements, caption under card  
2. Kill sky/blue/teal hardcodes in mocks + selected ring = olive  
3. Empty-home atmosphere + type scale  
4. Composer `:focus-within` + mode pills in inset track  
5. Gallery title → quiet mono eyebrow; tone filter Atelier  
6. Sidebar primary CTA filled olive  
7. Motion uses `--dur-*` + `useReducedMotion` on gallery  
8. Presentation stage warm ink (not cool slate)

## Changes (v3 — continue)

1. Empty-home: center when plain; top when deck stage; space tokens  
2. Sidebar foot hairline + denser history; live label bump  
3. Composer attach = ghost (no paper chip)  
4. Diagram strip / zoom → Atelier tokens (no `system-ui` / `#fff`)  
5. Rail head denser + olive rule  
6. DeckStyleSheet packs: 14px radius + capsule swatches  
7. Stage wider (`--deck-stage-max: 76rem`); gallery gaps larger  

## Out of scope

App.tsx split, durable history API, photographic slide thumbs, mobile drawer.
