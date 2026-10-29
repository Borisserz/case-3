# DOCX lists (C7) + Resume failed stage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship post-pandoc DOCX list styles (C7) and same-`run_id` resume from failed images/charts/inject/latex/docx with a Liber «Продолжить» button.

**Architecture:** C7 = soft-fail `docx_lists` after `docx_polish` in `render_tex`. Resume = preserve `failed_stage` on pipeline error; `resume_pipeline` skips LLM, regenerates only missing/failed media, reinjects + renders; API + ArtifactCard button.

**Tech Stack:** python-docx, FastAPI, React Liber UI, existing pipeline/render.

## Global Constraints

- Windows desk + Qwen + Image API — no new native deps; don’t break `scripts\api.cmd` / `web.cmd`.
- Numbers/facts only from Source; soft-fail media stays soft-fail.
- Do not implement queue/retention/installer, LLM resume, or C6 academic skin.
- Soft-fail list polish never fails `render_tex`.
- TDD for list fixer + resume eligibility/media skip; pytest + `cd web && npm run build` when UI touched.
- Update backlog C7 + I resume → done; KI-tex-render / KI-pipeline.

---

### Task 1: C7 — `docx_lists` unit + wire into render

**Files:**
- Create: `src/case3/docx_lists.py`
- Create: `tests/test_docx_lists.py`
- Modify: `src/case3/render.py` (after `try_polish_docx`)
- Modify: `.agents/knowledge/KI-tex-render.md` (gotcha line)

**Interfaces:**
- Produces: `fix_docx_lists(path) -> Path`, `try_fix_docx_lists(path) -> bool`

- [ ] **Step 1:** Write failing tests: bullet + numbered paragraphs get List Bullet / List Number; marker text stripped; soft-fail returns False without raise.
- [ ] **Step 2:** Run `pytest tests/test_docx_lists.py -q` — expect FAIL (module missing).
- [ ] **Step 3:** Implement `docx_lists.py` (python-docx styles + numPr / ilvl ≤1).
- [ ] **Step 4:** Call `try_fix_docx_lists` from `render_tex` after polish, before native charts.
- [ ] **Step 5:** pytest green; note KI-tex-render.

---

### Task 2: Resume — preserve `failed_stage` + `can_resume` + `resume_pipeline`

**Files:**
- Modify: `src/case3/pipeline.py`
- Create: `tests/test_pipeline_resume.py`
- Optionally extract helpers in same module: `RESUME_STAGES`, `can_resume_run`, `resume_pipeline`

**Interfaces:**
- Produces: `can_resume_run(meta, *, work: Path, out: Path) -> bool`
- Produces: `resume_pipeline(run_id, *, project_root, on_stage=None) -> Path`
- On error path: set `meta["failed_stage"]` before `status=error`

- [ ] **Step 1:** Failing tests: can_resume true/false matrix; resume skips ok chart PNG (mock generate); failed_stage set on simulated error.
- [ ] **Step 2:** pytest FAIL.
- [ ] **Step 3:** Implement preserve failed_stage + can_resume + resume_pipeline (reuse media/inject/render blocks; no LLM).
- [ ] **Step 4:** pytest green.

---

### Task 3: Resume — API + status `can_resume`

**Files:**
- Modify: `src/case3/api.py` — `POST /api/runs/{id}/resume`; status payload field
- Create/modify: `tests/test_api_resume.py` (or extend existing API tests)

- [ ] **Step 1:** Failing test: 409 when not eligible; 200 starts background resume when eligible (tmpdir fixture).
- [ ] **Step 2:** Implement endpoint mirroring `_bg_run_pipeline` pattern; expose `can_resume` on status.
- [ ] **Step 3:** pytest green.

---

### Task 4: UI — «Продолжить» on failed card

**Files:**
- Modify: `web/src/ArtifactCard.tsx` (and/or ChatMessages / App handlers)
- Modify: `web/src/app/App.tsx` — `resumeRun(runId)` fetch + poll/SSE

- [ ] **Step 1:** Button when `status===error` && (`can_resume` or failed_stage in set).
- [ ] **Step 2:** POST resume; set card back to running; reuse existing status subscription.
- [ ] **Step 3:** `cd web && npm run build`.

---

### Task 5: Memory + verification

**Files:**
- Modify: `docs/knowledge/backlog-deferred-2026-10-25.md`
- Modify: `docs/MEMORY.md` (one line)
- Modify: `.agents/knowledge/KI-pipeline.md`

- [ ] **Step 1:** Mark C7 + I resume done; leave queue/retention/installer parked.
- [ ] **Step 2:** Run focused pytest + web build; summarize.

## Definition of done

- Lists in DOCX use Liber list styles after pandoc (unit-tested).
- Failed eligible run shows «Продолжить»; same run_id continues without LLM.
- Backlog/KI updated; no queue/installer scope creep.
