# Liber Premium UI Refactor — Design

**Date:** 2026-10-22  
**Status:** implemented (full desk pass 2026-10-22)  
**Extends:** [2026-10-21 soft-premium](2026-10-21-liber-soft-premium-ui-design.md) · ADR-0006  
**KI:** `.agents/knowledge/KI-liber-ui.md`

## Goal

Liber desk must read as a **finished premium product**, not a draft chat demo. Keep Atelier identity (warm paper, olive, DM Sans + Crimson). Borrow Julius **structure** (width ladder, template stage, deliberate style surface) — never Julius purple/blue chrome.

## Non-negotiables

1. **Width ladder:** hero/composer ~42–44rem; template/gallery stage ~64–72rem; shell stays wide (`~1760px`).
2. **One hierarchy on empty home:** Mark → one H1 → pill composer → mode pills → (optional) style sheet → template stage.
3. **Deck settings behind one control:** palette button opens **one** style surface of record (`DeckStyleSheet` with live mini preview). No skinny duplicate inline pack/hex panel.
4. **Send inside composer (right);** style control outside left of modes.
5. **Scroll owner:** empty-home `.desk` scrolls (`overflow-y: auto`); never clip packs/gallery.
6. **Tokens only:** no slate/sky hardcoded in product chrome; mock thumbs may use pack colors.
7. **Serif discipline:** Crimson only for brand/hero/slide titles; UI chrome = DM Sans.
8. **Focus:** Settings / DeckStyle / fullscreen sheets trap focus + restore; `focus-visible` on controls.
9. **Motion:** `--ease-out` / `--dur-*`; honor `prefers-reduced-motion` everywhere Framer/CSS animate.
10. **Preserve product rules:** Source-only numbers; chart whitelist; PDF print truth; no purple neuroslop.

## Surfaces in scope (all)

| Surface | Premium bar |
|---------|-------------|
| Empty home + composer + templates | Julius-width stage; rich 16:10 slide mocks; no overlap with name scrim |
| Deck style | Single `DeckStyleSheet`; packs as capsule swatches |
| Chat transcript | Quiet bubbles; thinking fold; artifact cards |
| Artifact rail | Focused workbench; retoken tabs/chrome |
| Presentation pane / FS / export | Olive tokens; clear View→Edit→Export |
| Diagram pane / FS | Same chrome language |
| Sidebar / history / settings | Dense but calm; focus trap |
| CSS architecture | Split `styles/` by surface; shared tokens; cull dead topbar/panel |

## Out of scope (explicit)

- Backend durable history API
- Mobile drawer rewrite (light responsive OK)
- 100+ seasonal templates / freeform shapes / Publish
- Rebrand away from Atelier

## Success criteria

- Empty → Презентация: scroll works; templates look like slide stages; settings not always-on.
- No duplicate deck-palette UIs.
- Presentation chrome uses `:root` tokens (spot-check no `#64748b` / `#7dd3fc` in chrome).
- `tsc` clean; visual pass empty + rail + presentation FS.
- KI + this spec updated when done.
