# Liber Premium UI Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: executing-plans / subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Full Liber web UI → premium Atelier product (structure from Julius, brand Liber).

**Architecture:** Keep flat `web/src/*.tsx`; split CSS into `web/src/styles/*` imported from `main.tsx`; one deck style sheet; token-first chrome.

**Tech:** Vite + React 19 + Framer Motion + CSS variables. Spec: `docs/superpowers/specs/2026-10-22-liber-premium-ui-refactor-design.md`.

---

## File map

| Path | Role |
|------|------|
| `web/src/styles/tokens.css` | `:root` tokens + reset + reduced-motion |
| `web/src/styles/shell.css` | app / sidebar / desk-split |
| `web/src/styles/chat.css` | messages / empty / bubbles |
| `web/src/styles/composer.css` | composer / modes / packs |
| `web/src/styles/deck.css` | template gallery / slide mocks / deck canvas bits used empty-home |
| `web/src/styles/rail.css` | artifact rail |
| `web/src/styles/presentation.css` | presentation pane / FS / export |
| `web/src/styles/modals.css` | settings / sheets / focus |
| `web/src/styles.css` | `@import` aggregator (or delete after switch) |
| `web/src/ChatComposer.tsx` | send right; open DeckStyleSheet; no inline palette |
| `web/src/DeckStyleSheet.tsx` | sole style surface |
| `web/src/DeckTemplateGallery.tsx` | Julius-stage cards |
| `web/src/EmptyState.tsx` | wider hero for presentation |
| `web/src/useFocusTrap.ts` | shared focus trap |
| `web/src/SettingsModal.tsx` / sheets | use focus trap |
| `.agents/knowledge/KI-liber-ui.md` | update invariants |

---

### Task 1: Tokens + motion vocabulary

- [x] Expand `:root` with `--space-*`, `--dur-fast/mid/slow`, unify shadow aliases
- [x] Add `@media (prefers-reduced-motion: reduce)` kill-switch block
- [x] Verify no visual regression on empty home

### Task 2: Empty-home composition

- [x] Widen empty hero; keep composer 44rem; gallery 68–72rem
- [x] Desk `overflow-y: auto` on `is-empty-home` (already); pin toolbar feel
- [x] Cull leftover narrow `28rem` / `22ch` caps where they fight premium

### Task 3: Composer + single style surface

- [x] Remove inline pack/hex/fonts from `ChatComposer` when presentation
- [x] Palette button → `onDeckStyleOpen` → `DeckStyleSheet`
- [x] Keep send inside composer right; settings left of modes

### Task 4: Template gallery craft

- [x] Slide mocks no overlap with name scrim
- [x] Optional blurb under name or in tooltip
- [x] Selected = olive outline; hover lift

### Task 5: Retoken presentation + rail chrome

- [x] Replace slate/sky hex in presentation/rail CSS with tokens
- [x] Align buttons/pills with composer language

### Task 6: a11y focus traps

- [x] `useFocusTrap.ts`
- [x] Wire SettingsModal, DeckStyleSheet, PresentationFullscreen, DiagramFullscreen, ImageEditModal, ChartEditSheet

### Task 7: CSS split

- [x] Extract sections into `web/src/styles/*.css`
- [x] `main.tsx` imports aggregator
- [x] Delete dead `.topbar` / `.panel` shelf CSS

### Task 8: Sidebar / settings polish

- [x] Density, focus rings, history accordion calm state
- [x] Settings modal visual alignment with DeckStyleSheet

### Task 9: Verify + memory

- [x] `npx tsc --noEmit`
- [x] Browser: empty → presentation → settings → template apply → scroll
- [x] Update KI-liber-ui.md + MEMORY pointer if needed
