# KI: Image API / photos

## What
Generate and edit report photos via office HTTP API; optional user uploads; chat-only edit mode.

## Entry
- Config: `ImageApiConfig.from_env()` — `IMAGE_API_BASE_URL` (alias Kandinsky env)
- Gen: `generate_all_figures` in pipeline images stage
- Edit in report: `figure_edit.edit_figure_in_run`
- Chat-only: `api` `photo_mode=edit` / `POST /api/photo/edit`
- Worker: `workers/case3-image` (optional)

## Invariants
- Upload budget ≤2 files, size caps in `user_photos`
- SSRF: no private IP redirects on remote image fetch
- User figures `source=upload` skip API generate
- Health: `image_api_configured` + **live** `image_api_ok` / `image_api_error` via `probe_image_api` (~1.5s)
- Prompts: `sanitize` → `apply_pack_style_lock` → `harden_brand_safe` (+ `Avoid:`) in `prepare_image_prompt` on generate **and** edit
- Pack id: report → `palette_from_intent` / `meta.image_style_pack`; slides → `slides_theme_pack`

## Gotchas
- Loopback URL rewrite for Docker/Windows host access
- Worker may fall back edit→generate silently; `negative_prompt` ignored by case3-image worker (baked into prompt)
- Empty / down Image API → soft-fail strip fig_*; UI chip + toast warn; report run not blocked

## See
ADR-0004 · `docs/superpowers/specs/2026-10-20-image-api-design.md` · `user-photos` spec  
Brand-safe + pack lock + health chip: `docs/knowledge/image-brand-safe-and-pack-lock.md`
