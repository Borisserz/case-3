# Plan: Recommendation B — sheet + quiet hero + grid under modes

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans / subagent-driven-development to implement this plan task-by-task.

**Goal:** Liber empty home = lifted sheet composer + quiet hero + starter grid under modes (all three modes). Palette unchanged.

**Architecture:** Keep presentation `DeckTemplateGallery`. Add quiet text/card starters for report + diagram under the same composer mount. Modes stay inside sheet inner-bar; grids sit below the sheet.

**Tech stack:** React + existing CSS modules (`composer.css`, `chat.css`, `shell.css`, `deck.css`).

---

### Task 1: Spec lock (done in chat)

Recommendation B approved. Spec: `docs/superpowers/specs/2026-10-23-julius-premium-chat-ui-design.md`.

### Task 2: Report + diagram starter grid

**Files:**
- Create: `web/src/modeStarters.ts` (6–8 quiet prompts per mode)
- Create: `web/src/ModeStarterGrid.tsx`
- Modify: `web/src/ChatComposer.tsx` — show grid when `showModes && workMode` is report|diagram
- Modify: `web/src/styles/composer.css` — quiet 2-col starter cards
- Modify: `web/src/App.tsx` — `onPickStarter(prompt)` → `setChat` if empty or replace

**Step:** Click starter fills composer; does not auto-send.

### Task 3: Visual QA

Empty: report (starters), diagram (starters), presentation (deck gallery). Thread: modes hidden, sheet still clean.

### Task 4: Update design spec

Note grids for all modes; palette locked.
