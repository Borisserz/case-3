# Analysis: PDF quality — verification of recent work + path to max quality

**Date:** 2026-10-21  
**Status:** Verified (unit suite) · live Qwen e2e not re-run this session

---

## 1. What shipped this session (delta)

| Slice | Change | Files |
|-------|--------|--------|
| Vivid palettes | Punchier hex; area α≈0.34 | `chart_style.py`, `system_tex.md`, UI fallbacks |
| Legend size | `.valued-legend` 18px / swatch 14px; Chart.js legend 16–17 | `chart_frame.html`, `LiveChart.tsx` |
| **D4** | Title `\rule` under `\maketitle` + float/caption skips | `tex_preamble.py` (`ensure_liber_print_chrome`) |
| **D7** | `width` clamp ≤0.92; canvas height ≤560 | `tex_safe.py`, `chart_types_coerce.py` |
| **D6** | Prompt: itemize/enumerate/emph/textbf first-class | `system_tex.md` |
| Docs/KI | Specs + KI + roadmap D4/D6/D7 done | `.agents/knowledge/*`, `docs/superpowers/*` |

Offline proof artifact: `runs/vivid_demo/out/vivid_demo.pdf` (valid `%PDF-1.5`, ~211 KB).

---

## 2. Pipeline safety — does it break the chain?

### Pipeline path (unchanged topology)

```
LLM → parse → polish_charts (palette+harden+D7 height)
    → Playwright PNG (frame CSS legend)
    → inject (sanitize_width / D7)
    → ensure_document_preamble (D4 chrome) → latexmk / pandoc
```

No new stages, env vars, or chart types. Soft-fail charts still soft-fail.

### Touch points vs risk

| Module | Called from | Risk | Verdict |
|--------|-------------|------|---------|
| `apply_palette_to_html` / `_PALETTES` | `polish_charts` | Visual only; same ids | **Safe** — old soft hex tests updated |
| `harden` height clamp | `polish_charts` | Tall canvases shrink | **Safe** — hbar path unchanged (own height) |
| `sanitize_width` | `inject` / parse | Widths >0.92 → 0.92 | **Safe** — invalid still → 0.85 default |
| `ensure_liber_print_chrome` | `ensure_report_style` → prepare_tex | Idempotent (1 chrome block) | **Safe** — tested |
| `chart_frame` CSS | Playwright only | Larger legend → taller PNG | **Low** — may add vertical space; D7 caps canvas |
| D6 prompt | Qwen only | Better lists if model obeys | **No runtime risk** |

### Idempotency note

`\CaseThreeMaketitle` appears **twice in one block** (`\let` + call) — not a double wrap. Marker `% --- Liber print chrome` appears once after re-harden. Test: `test_liber_print_chrome_idempotent`.

### Residual risks (not blockers)

1. **LLM still emits soft hex** → polish remaps on named palette; `auto` can still look soft until model picks a preset.
2. **D6 is prompt-only** — no TeX rewriter for walls of prose; quality depends on Qwen.
3. **Larger legend** can push donut figure taller on A4 — acceptable; watch dense multi-chart pages.
4. **Live Qwen + Docker desk** not re-run in this verification pass — unit + offline PDF only.
5. Branch also has large unrelated `App.tsx` churn — keep PDF polish commits separate from UI shell.

### Verification evidence (this session)

```text
pytest tests/  →  144 passed in 6.54s
Idempotent D4 chrome: 1 block after double ensure_document_preamble
vivid_demo.pdf: %PDF-1.5, chrome+rule present when re-hardened
```

Catch fixed during verification: `test_chart_premium_layouts.test_palettes_are_softer_ladders` still expected soft `#3F5210` → updated to vivid `#2E4208`.

---

## 3. Current PDF quality — gap map

### Already strong

- A4 + DejaVu Cyrillic + fancyhdr + «Рис.»/«Таблица»
- Chart whitelist + palette polish + Playwright PNG
- Vivid colors + readable donut legend
- D4 title rule + float breathing room
- D7 geometry clamps
- Tabularx harden / wide-table repair (partial)

### Gaps to «max quality»

| Layer | Gap | Severity |
|-------|-----|----------|
| Typography | One report look only; section hierarchy still generic | Med |
| Tables | Booktabs uneven; DOCX tables worse than PDF | Med–High |
| Charts | No shared print tokens with Liber UI chrome; KPI/donut density on multi-chart pages | Med |
| Prose | D6 prompt not enforced; lists/emphasis still miss | Med |
| Figures | Photo + chart vertical rhythm; orphan captions | Low–Med |
| DOCX | D5/D8 parity with PDF | Med (if Word matters) |
| QA | No visual regression on PDF pages (D11) | High for «max» |
| Brand | Soft-premium UI olive vs print tokens still dual | Low–Med |

---

## 4. Definition of «max quality» (acceptance)

A Liber PDF is «max quality» when:

1. **First page:** clear title + rule + short lead; no case-3 branding.
2. **Body:** sections with air; lists for list-like Source; tables fit A4 without overflow.
3. **Charts:** vivid palette, readable legend/axes, no giant empty canvas, width ≤0.92.
4. **Chrome:** consistent fancyhdr; captions «Рис./Таблица»; floats not colliding.
5. **Parity:** chat preview not required equal, but not embarrassing vs PDF.
6. **Regression:** fixture PDFs page-diff or screenshot gate on CI/local matrix.

---

## 5. Recommended roadmap (see plan file)

Phased plan: `docs/superpowers/plans/2026-10-21-pdf-max-quality.md`

Priority order:

1. **Stabilize** — visual fixtures (D11 lite) + fix any desk smoke gaps  
2. **Print chrome 2.0** — section/table rhythm, chart float defaults  
3. **Content quality** — light TeX post-pass for lists (beyond D6 prompt)  
4. **DOCX parity** — D5/D8 if Word is in the contract  
5. **Tokens / dual style** — D10 + optional D9 Liber/strict  

---

## 6. Do / Don't for agents

**Do:** change `_PALETTES`, `REPORT_STYLE`, `sanitize_width`, frame CSS with tests.  
**Don't:** invent chart types; commit `runs/`; skip full `pytest` after palette hex changes; couple PDF chrome to Liber soft-premium CSS blindly.
