# Liber polish batch A — handoff for coding agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Before coding:** Read `docs/MEMORY.md`, `AGENTS.md`, then the KI cards listed per task. Do not invent chart types, env vars, or pipeline stages.

**Goal:** Ship six selected polish items from the Oct-24 feature audit (local chart type, live chart preview, sticky TOC, section collapse, PPTX title/body fonts, gallery→Slide). Leave everything else untouched.

**Architecture:** Mostly harden existing paths (chart edit already has local coerce + `/preview`; rail already has `RailToc`; PresentationPane already has gallery→Slide). Real greenfield work is **section collapse** and **PPTX font role fix**. Prefer verify → gap-fix → test over rewrite.

**Tech Stack:** FastAPI (`src/case3/`), Chart.js HTML coerce, React/Vite Liber UI (`web/src/`), python-pptx (`slides_pptx_native.py`), deck theme JSON (`src/case3/deck_themes/*.json`).

**Product owner decisions (2026-10-25) — binding:**

| # | Item | Decision |
|---|------|----------|
| 1 | Local-first chart type (G3) | **DO** |
| 2 | Style chips → deterministic patches (G5) | **DEFER** — owner sets up LLM memory later |
| 3 | PNG-first edit / docs async (G6) | **DO NOT** |
| 4 | Live preview in ChartEditSheet (G9) | **DO** |
| 5 | Sticky TOC (C7) | **DO** |
| 6 | Collapse sections (C11) | **DO** |
| 7 | Print-mode preview (C9) | out of this batch |
| 8 | Click figure → PDF page (C10) | out of this batch |
| 9 | Two report styles Liber/strict (D9) | **REJECT** — only one report style forever for now |
| 10 | PPTX fonts not Calibri-only | **DO** |
| 11 | Native OOXML charts ≥1 | **DEFER** (soon, not this batch) |
| 12 | Save/timeout toast | out of this batch |
| 13 | Gallery → Slide not Edit | **DO** |
| 14 | Surface `deck_pdf_mode` | out of this batch |
| 15 | Visual regression PDF (D11) | out of this batch |

## Global Constraints

- Windows desk + Qwen + Image API — no new native deps; don’t break `scripts\api.cmd` / `scripts\web.cmd`.
- Numbers/facts only from Source; chart types only from `chart_html.CHART_TYPES` whitelist.
- Palettes: editorial / ocean / sunset / mono / atelier — no purple neuroslop.
- PDF remains print truth; chat preview ≈ TeX blocks.
- Report style: **single** Liber style only — do not add Settings toggle for “strict”.
- Do not implement deferred/rejected rows above “while you’re there”.
- Do not commit `runs/`, `.env`, secrets, PDF/DOCX artifacts.
- After each task: relevant `pytest` + `cd web && npm run build` when UI touched.
- Announce: «Using [skill] to [purpose]»; TDD where logic is non-trivial.
- Persist durable decisions in ADR/KI only if behavior contract changes (fonts ADR note optional).

## Current codebase reality (read before coding)

**Already partially present — verify and close gaps, do not rip out:**

1. **G3 local type** — `edit_chart_in_run` in `src/case3/chart_edit.py`: if `style_notes` empty and type/palette change → `apply_type_to_chart` / local palette, **no LLM**. KPI path is local. LLM only when free-text style notes present.
2. **G9 live preview** — `POST /api/runs/{id}/charts/{id}/preview` → `preview_chart_html` (local only). `ChartEditSheet.tsx` debounces and calls `onPreviewHtml` to swap the figure above the sheet.
3. **C7 TOC** — `web/src/RailToc.tsx` + sticky `.rail-toc` in `web/src/styles/rail.css`; used from `ArtifactRail.tsx` when preview tab + ≥2 headings. Chat inline `ReportView` has **no** TOC.
4. **C13 gallery** — `PresentationPane.tsx` `DeckGallery.onSelect` already does `setView("slide"); setEditing(false)`. Comment: «Julius: open in Slide view; Edit is explicit.» Still audit all entry points for regressions.

**Not present:**

- Section collapse in `ReportView` / rail preview.
- Reliable Office fonts: `_fonts_from_style` prefers `fallback_pptx` for **body**; many packs set `fallback_pptx: Calibri`. Title `"Liber Serif"` is not an Office font. Gap audit P0 still open.

## File map

| Area | Files |
|------|--------|
| Chart local + preview | `src/case3/chart_edit.py`, `chart_types_coerce.py`, `api.py` (`/preview`, `/edit`), `tests/test_coerce_chart_types.py`, chart edit tests |
| Chart UI | `web/src/ChartEditSheet.tsx`, `ReportView.tsx` (preview HTML swap), styles |
| TOC + collapse | `web/src/RailToc.tsx`, `ArtifactRail.tsx`, `ReportView.tsx`, `web/src/styles/rail.css`, `chat.css` |
| PPTX fonts | `src/case3/slides_pptx_native.py` (`_fonts_from_style`, `_set_run`), `src/case3/deck_theme.py`, `src/case3/deck_themes/*.json`, tests under `tests/` for pptx if any |
| Gallery | `web/src/PresentationPane.tsx`, `DeckGallery.tsx` |
| Memory | `.agents/knowledge/KI-charts.md`, `KI-liber-ui.md`, `KI-liber-deck.md`; gap audit `docs/superpowers/specs/2026-10-22-liber-vs-julius-gap-audit.md` |

---

### Task 1: G3 — Local-first chart type (harden)

**Files:**
- Modify: `src/case3/chart_edit.py`
- Modify: `src/case3/chart_types_coerce.py` (only if coerce gaps found)
- Test: `tests/test_coerce_chart_types.py` and/or new `tests/test_chart_edit_local_type.py`
- KI: `.agents/knowledge/KI-charts.md` (short note if contract clarified)

**Interfaces:**
- Consumes: `apply_type_to_chart(chart, want)`, `edit_chart_in_run(..., chart_type=, style=, palette=)`
- Produces: type/palette-only edits never call `rewrite_chart_html_with_llm`; response/`modes` includes `local_type` / `local_palette`

**Acceptance:**
- Changing type **without** style notes → no LLM client call (mock/spy in test).
- Changing palette only → local path.
- Style notes non-empty → LLM path still allowed (do not remove).
- Coerce preserves data arrays; harden still runs.
- Common transforms work locally: bar↔horizontal_bar, bar↔grouped_bar/stacked_bar where coerce already supports, donut↔bar when coerce supports; if unsupported, **fail clearly** or keep previous type — do not silently call LLM for type-only.

- [x] **Step 1:** Read `edit_chart_in_run` + `preview_chart_html` + `_local_restyle_html`. List any branch where type-only still hits LLM.
- [x] **Step 2:** Write failing test: type change bar→horizontal_bar (or similar fixture HTML) with empty style → assert LLM not invoked; HTML/type updated; PNG path can be mocked.
- [x] **Step 3:** Fix any leak; extend coerce only if test proves a missing local transform that UI offers in catalog.
- [x] **Step 4:** Run `pytest tests/test_coerce_chart_types.py tests/test_chart_edit_local_type.py -v` (adjust names to what you create).
- [x] **Step 5:** Manual note in KI: «type/palette without style notes = local; style notes = LLM».

**Out of scope for Task 1:** style chips (G5), PNG-first async docs (G6), live preview UI (Task 2).

---

### Task 2: G9 — Live ChartEditSheet preview (complete + harden)

**Files:**
- Modify: `web/src/ChartEditSheet.tsx`
- Modify: `web/src/ReportView.tsx` (ensure `onPreviewHtml` swaps the open figure; revert on cancel/close)
- Modify: `src/case3/api.py` / `chart_edit.preview_chart_html` only if API gaps
- Styles: chart-edit classes in `web/src/styles/` as needed

**Interfaces:**
- Consumes: `POST /api/runs/{run_id}/charts/{chart_id}/preview` body `{ palette, chart_type }`
- Produces: figure above sheet shows local preview HTML; Apply still uses full edit endpoint; Cancel restores original

**Acceptance:**
- Open edit sheet → change type/palette → within ~300ms debounce, figure **above** updates (existing design: no second chart inside sheet).
- Loading: eyebrow already shows «обновляю превью…» — keep or clarify.
- Preview **errors**: do not silently blank forever; show short error in sheet (`error` prop or local) and keep last good preview or original.
- Style notes field does **not** drive live preview (LLM deferred to Apply) — optional muted hint under notes: «превью без текста стиля; текст применится при сохранении».
- Close/Cancel clears preview override.
- Race: rapid type clicks only apply latest seq (already `previewSeq` — verify).

- [x] **Step 1:** Trace `onPreviewHtml` from `ChartEditSheet` through `ReportView` / rail. Confirm swap + restore paths.
- [x] **Step 2:** Add/adjust UI for preview error (failing test via component test only if project already has RTL; else manual checklist in PR notes).
- [x] **Step 3:** Fix restore-on-cancel and error surfacing.
- [x] **Step 4:** `cd web && npm run build`
- [x] **Step 5:** Smoke: open report with chart → Изменить → switch type → see live swap → Cancel → original PNG/html back → Apply type-only → persists.

**Out of scope:** async PDF rebuild after edit (G6 rejected).

---

### Task 3: C7 — Sticky TOC that actually works for long reports

**Files:**
- Modify: `web/src/RailToc.tsx`, `ArtifactRail.tsx`, `web/src/styles/rail.css`
- Optionally: `web/src/ReportView.tsx` if headings lack stable ids outside rail
- Chat path: if long reports are primarily read **in chat** (not only rail), add a compact sticky TOC above chat `ReportView` **or** document that TOC is rail-only and improve rail entry — **prefer making rail TOC undeniable** (sticky, visible, jump works) first; add chat TOC only if rail-only is insufficient for the owner’s flow

**Interfaces:**
- Consumes: `buildToc(preview.blocks)` → ids `rail-h-N` matching heading `id`s in `ReportView`
- Produces: sticky nav; click scrolls; active chip tracks scroll

**Acceptance:**
- With ≥2 headings, TOC visible while scrolling preview body (sticky does not scroll away under chrome).
- Click chip → smooth scroll to heading; heading not hidden under sticky TOC (offset/scroll-margin).
- Active chip updates via IntersectionObserver (already sketched — fix if broken when `root` is rail body).
- Works for level-1 and level-2 headings from preview JSON.
- No TOC when &lt;2 headings.

- [x] **Step 1:** Reproduce: open artifact rail Preview on a long report; scroll; check sticky + jump + active.
- [x] **Step 2:** Fix CSS (`position: sticky` + z-index + top offset under rail header) and `scroll-margin-top` on `.report-h`.
- [x] **Step 3:** Fix IO root / id mismatch if jump or active is wrong.
- [x] **Step 4:** If chat-only reading is still painful, add minimal sticky TOC for chat ReportView reusing `buildToc` — same ids scheme.
- [x] **Step 5:** `npm run build`; manual scroll checklist.

**Out of scope:** print-mode (C9), figure→PDF jump (C10).

---

### Task 4: C11 — Collapse sections in preview

**Files:**
- Modify: `web/src/ReportView.tsx` (primary)
- Modify: `web/src/styles/chat.css` and/or `rail.css`
- Optionally small helper `web/src/reportSections.ts` if grouping logic is non-trivial

**Interfaces:**
- Consumes: ordered `PreviewBlock[]`
- Produces: each `heading` toggles visibility of following blocks until next heading of same or higher level (define: collapse under `h2` hides until next `h2`; nested `h3` can collapse independently if easy — minimum viable = collapse by top-level section)

**Acceptance:**
- Click heading (or a chevron control next to it) collapses/expands that section’s body.
- Collapsed state: heading remains visible; figures/tables/paragraphs in section hidden.
- Optional toolbar: «Свернуть всё» / «Развернуть всё» near TOC or report top — nice-to-have, not required.
- Persist collapse state in `sessionStorage` keyed by `runId` + heading id (so tab switch doesn’t wipe) — preferred.
- Keyboard: heading button focusable, Enter/Space toggles.
- Does not break chart/table edit sheets or figure click handlers.

- [x] **Step 1:** Group blocks into sections in a pure function; unit-test grouping if extracted.
- [x] **Step 2:** Render collapsible sections in `ReportView`.
- [x] **Step 3:** Wire sessionStorage + a11y.
- [x] **Step 4:** `npm run build`; smoke with multi-section preview.

**Out of scope:** editing prose inside collapsed sections; changing TeX structure.

---

### Task 5: PPTX title + body fonts (gap audit P0)

**Files:**
- Modify: `src/case3/slides_pptx_native.py` — `_fonts_from_style`, `_set_run`, any OOXML font helpers
- Modify: `src/case3/deck_themes/*.json` font fields if needed (Office-safe names)
- Modify: `src/case3/deck_theme.py` defaults if they force Calibri titles
- Test: new `tests/test_pptx_fonts.py` (build minimal deck IR → open pptx → assert `a:latin` / run font names on title vs body)

**Interfaces:**
- Consumes: `deck.style.fonts.title`, `.body`, `.fallback_pptx`
- Produces: title runs use **title** role; body runs use **body** role; `fallback_pptx` only when title/body missing or unmappable

**Acceptance (binding):**
- Stop preferring `fallback_pptx` over `body` for body text (current bug in `_fonts_from_style`).
- Map web/Liber face names to Office-safe families, e.g.:
  - `Liber Serif` / Fraunces / Libre Baskerville / Playfair → `Georgia`
  - `Liber Sans` / Source Sans / Inter / Manrope → `Calibri` or `Arial` (pick one rule and document)
  - `Aptos Display` → `Aptos` (or documented fallback if Aptos unavailable — still not silent Calibri for titles when pack says Aptos/Georgia)
- Pack `botanical`: titles render as Georgia in PPTX; `atelier`: titles Georgia (mapped), not Calibri; `relay`: Aptos/Aptos Display path, not Calibri titles.
- Set python-pptx font so PowerPoint sees latin typeface (if needed set `r.font.name` and OOXML `a:latin/@typeface` — known pptx quirk).
- Twin HTML may still use woff2 — do not attempt pixel-perfect; PPTX must not look “all Calibri” when theme declares serif titles.
- Do **not** start native chart work (Task 11 deferred).

- [x] **Step 1:** Write failing test on font resolution helper (pure function) + one pptx smoke if feasible offline.
- [x] **Step 2:** Fix `_fonts_from_style` priority: `title` ← fonts.title; `body` ← fonts.body then fallback_pptx.
- [x] **Step 3:** Expand `_first` / mapper for Liber Serif, Liber Sans, Aptos Display, Arial Black, etc.
- [x] **Step 4:** Verify `_set_run(..., title=True)` used for slide titles/kickers consistently; body for bullets.
- [x] **Step 5:** Rebuild a fixture deck or run existing slides unit test; open XML or assert font names.
- [x] **Step 6:** Short note in `KI-liber-deck.md` under fonts.

**Out of scope:** native OOXML charts (item 11); twin woff2 embedding; new report styles (item 9 rejected).

---

### Task 6: Gallery → Slide (not Edit) — verify + lock

**Files:**
- Modify: `web/src/PresentationPane.tsx`, possibly `DeckGallery.tsx`, `ArtifactRail.tsx` / `App.tsx` open handlers
- No backend

**Interfaces:**
- Consumes: gallery select index; chrome segments Preview(grid) / Slide / Edit
- Produces: selecting a thumbnail always enters **Slide** with `editing === false`; Edit only via Edit segment (or explicit control)

**Acceptance:**
- From grid/gallery click → `view === "slide"` && `!editing`.
- Opening presentation artifact / PPTX tab does **not** start in Edit.
- Edit segment still enables editing; leaving Edit to Slide turns editing off.
- No path where gallery click sets `setEditing(true)`.
- If already correct: add a short comment + checklist; optional React test only if harness exists. Do not churn UI chrome.

- [x] **Step 1:** Grep `setEditing(true)` and all `PresentationPane` mount props; list entry points.
- [x] **Step 2:** Fix any leak (e.g. remount restoring edit, live canvas forcing edit).
- [x] **Step 3:** Manual: grid → click slide → Slide segment on, fields not contentEditable → click Edit → editable → Gallery → click other → back to non-edit Slide.
- [x] **Step 4:** `npm run build`.

**Out of scope:** Present mode polish, save toast (12), deck_pdf_mode badge (14).

---

## Explicit DO NOT list (agent must not do)

- G5 style chips deterministic patches (deferred — LLM memory later).
- G6 PNG-first / async PDF-DOCX after chart edit.
- D9 second report style / Settings Liber vs strict.
- Item 11 native chart forcing / OOXML chart smoke (deferred next).
- Items 7, 8, 12, 14, 15 from the original A-list.
- Section **B** edit cycle (rewrite section / versions / compare / pinned Source / batch recolor / partial regen / undo) — parked until LLM chat memory; see [`docs/knowledge/backlog-deferred-2026-10-25.md`](../../knowledge/backlog-deferred-2026-10-25.md).
- PPTX purple Julius chrome; freeform canvas; new chart types outside whitelist.
- Large unrelated refactors of `App.tsx` / pipeline.

## Suggested order

1. Task 1 (G3) — backend, quick confidence  
2. Task 2 (G9) — depends on local preview correctness  
3. Task 5 (fonts) — independent backend  
4. Task 6 (gallery) — tiny UI audit  
5. Task 3 (TOC) + Task 4 (collapse) — ReportView UX together  

## Definition of done (batch)

- [x] All six tasks acceptance criteria met  
- [x] `pytest` for touched Python green  
- [x] `cd web && npm run build` green  
- [x] KI notes updated where contracts changed (charts local path, deck fonts)  
- [x] No deferred/rejected items sneaked in  
- [x] Owner can hand off item 11 (native charts) as a **separate** later plan  

## Handoff blurb (paste to coding agent)

```text
Implement docs/superpowers/plans/2026-10-25-liber-polish-batch-a-handoff.md
exactly. Scope = tasks 1,2,3,4,5,6 only (G3, G9, sticky TOC, section
collapse, PPTX fonts, gallery→Slide). Obey the DO NOT list. Read MEMORY.md
+ AGENTS.md + KI cards first. Prefer harden existing local chart preview /
RailToc / gallery→Slide over rewrites. Report style stays single Liber.
When done: pytest + web build + short summary of gaps closed vs already-present.
```
