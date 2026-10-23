# Liber vs Julius — presentation gap audit

**Date:** 2026-10-22  
**Sources:** repo code + botanical smoke + prior reviews ([frontend](b36a905b-c034-45a4-879a-a8f941bd2c9b), [backend](c20a8cad-e275-45a9-b74a-67ec82f2d497), [product](f934e52d-e84a-4014-b1ab-2c3ff78d38b1)); Julius live UI blocked pending user login in Cursor browser.

## What “copy Julius” means for Liber

| Julius craft | Liber lock |
|--------------|------------|
| Editable PPTX as truth | ADR-0008: PPTX = visual truth; web = token twin |
| Theme packs + situational style | 5 packs: atelier/board/signal/relay/botanical |
| Dense narrative layouts | IR: title, section, card_row, scorecard, table_hero, bullets, charts, media, callout, closing |
| Chat → slides in one flow | Report first, then «Сделать презентацию» |
| Purple chrome | **Do not copy** — Liber Atelier DNA |

## Already product-grade (spine)

- On-demand slides job → `deck.json` + native PPTX + twin PNG + LO PDF path
- ThemeTokens frozen into `deck.style`; style sheet UI (packs + hex + fonts)
- PresentationPane: Preview/Slide/Edit segment, filmstrip, gallery, Present
- Botanical smoke: 12-slide IR, fern OOXML bg, card_row + gold gate
- Dark table `body_fill` wired (botanical `#243D32`) — no longer hardcoded white-only path
- Liber shell: Julius empty (centered) + modes + focused workbench rail

## Gaps vs Julius (ranked)

### P0 — breaks “PPTX = truth” or trust

1. **Title fonts in PPTX** — themes declare Georgia/Aptos/Liber Serif, but `_PPTX_FONT` still prefers `fallback_pptx` (usually Calibri). Office looks “generic Calibri.”
2. **Native charts underused** — `add_native_chart` exists; botanical product smoke had **0** `chart_*` → charts as PNG. Julius board decks feel “Excel-native.”
3. **Twin ≠ Office typography** — HTML/React woff2 vs PPTX Calibri; Edit preview can lie about fonts.
4. **Save/patch UX** — long poll without clear fail toast (reviewer); silent “Сохраняю…” risk.
5. **Gallery → Edit default** — reviewer: opens Edit always; Julius opens Slide/view first.

### P1 — craft density

6. Pack motifs uneven (botanical rich; board/signal thinner chrome).
7. Bleed/veil geometry: HTML/React vs PPTX photo+rect diverge.
8. `deck_pdf_mode` not surfaced — LO missing → PNG stitch without rail warning.
9. Present mode polish (Space only in Present, click-to-advance, idle chrome).

### P2 — do not chase

- Freeform canvas / LLM CSS / Julius purple
- Pixel-perfect Office AA
- Fake rich-text B/I before IR supports runs

## Liber UX we already took from Julius (correctly)

- Empty: centered «Чем займёмся?» + composer
- Mode pills: Отчёт · Схема · Презентация
- Pack presets when mode=Презентация
- Palette toggle on composer
- Focused workbench: wide rail, one Export, Presentation CTA primary

## Recommended next sprint (deep craft B)

1. PPTX title+body font roles (stop Calibri-only titles)
2. Force ≥1 native chart when Source has series (smoke assert OOXML `charts/`)
3. Gallery default → Slide; Edit on explicit click
4. Save error + timeout UI
5. Surface LO PDF mode in rail

## Live Julius poke

Cookie/login wall at `https://julius.ai/chat` in Cursor browser tab. **User must sign in**; agent cannot complete OAuth without approval + credentials. After login, re-audit empty modes / style sheet / slide editor.
