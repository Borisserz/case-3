# case-3 Deep cleanup — design

**Date:** 2026-10-29  
**Status:** Approved (owner: «окей окей»)  
**Goal:** Disk + git + code readable; product stays green (`pytest`, health, `npm build`).

## Scope

### In

- **A** Delete local junk (`runs/*` except gitkeeps, caches, `.playwright-browsers`, `.local-wrangler`).
- **B** Git hygiene: remove tracked `debug-bundle/`; fix `.gitignore` so `tests/`, `docs/`, `AGENTS.md`, `fixtures/` are not ignored; ignore local browser/wrangler caches and matrix run folders.
- **C** Move one-shot QA/matrix/gallery scripts → `scripts/archive/` (keep desk launchers at `scripts/` root).
- **D** Safe dead-code / small simplifications; add `docs/knowledge/repo-map.md`.
- **E** Verify: pytest + web build + health + dry-run.

### Out

- Angular rewrite, UX polish roadmap, pipeline API rewrite.
- Deleting ADR/KI/parked backlog without explicit ask.
- Changing chart whitelist / pipeline stages / env contract.

## Success

1. `runs/` only keeps structure + fresh outputs after cleanup.
2. `git ls-files debug-bundle` → empty.
3. Desk scripts still at `scripts/{api,web,run,setup,smoke}.cmd` + `mac-up.command`.
4. Full pytest green; `npm run build` OK; `/api/health` ok.
5. Repo map documents top-level dirs in one page.

## Risks

| Risk | Mitigation |
|------|------------|
| Delete needed run mid-debug | Only wipe known artifact trees; keep `.gitkeep` |
| Break script paths in docs | Archive + README note pointing to `scripts/archive/` |
| `.gitignore` change floods status | Force-add already-tracked; ignore only junk patterns |
