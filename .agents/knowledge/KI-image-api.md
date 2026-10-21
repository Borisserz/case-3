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
- Health: `image_api_configured` (+ legacy `kandinsky_configured`)

## Gotchas
- Loopback URL rewrite for Docker/Windows host access
- Worker may fall back edit→generate silently
- Empty `IMAGE_API_BASE_URL` → strip planned generated figures

## See
ADR-0004 · `docs/superpowers/specs/2026-10-20-image-api-design.md` · `user-photos` spec
