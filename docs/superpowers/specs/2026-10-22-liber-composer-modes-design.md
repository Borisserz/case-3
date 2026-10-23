# Liber composer modes + diagram-only — Design

**Date:** 2026-10-22  
**Status:** approved (user: B pills + B schema-only)  
**Amends:** KI-liber-ui · ADR-0007 (diagrams stay UI-only)

## Goal

Julius-like start without purple clone: mode pills under composer, presentation pack presets on empty, palette toggle; **Схема** = Mermaid + short description, no PDF/DOCX.

## UX (B + Julius center empty)

```
Empty (centered mid-viewport, like Julius):
  Liber mark + «Чем займёмся?»
  Composer: [+] [input] [palette] [send]
  Pills: (Отчёт) (Схема) (Презентация)
  Presets: only mode=Презентация → pack cards

After first message: composer docks bottom; presets hide; pills stay
```

| Mode | Behavior |
|------|----------|
| none / Отчёт | Full report PDF+DOCX (current) |
| Схема | `output_mode=diagram`: max_charts/images=0, max_diagrams≥1, `formats=none`, rail opens on «Схема» |
| Презентация | Full report + intent note; selected pack stored in `liber.deckStyle`; CTA «Сделать презентацию» after |

## API

- Form `output_mode`: `report` \| `diagram` \| `presentation` \| `auto` (default `auto`)
- `formats=none` → empty set → pipeline skips `render_tex` (no Docker TeX)
- Diagram intent: Mermaid 1–3 + short LaTeX stub (title + 1–2 paragraphs); no charts/figs

## Non-goals

- Separate Diagram workspace IA
- Auto-generate PPTX on send in presentation mode (still CTA after report)
- Julius purple chrome / full landing clone when chat has messages
