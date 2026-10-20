# User-attached photos (Liber)

## Goal

Two modes from composer paperclip (≤2 PNG/JPEG, ≤4 MiB each):

1. **document** — photos become `usr_01`… figures in the PDF/DOCX (no Image API `/generate` for those slots).
2. **edit** — photo + Intent prompt → Image API `/edit` → preview in chat (no full report required).

## API

- `POST /api/run` accepts repeated `photos` files; `photo_mode=document|edit` (default document).
- `POST /api/photo/edit` — multipart `image` + `prompt` (+ optional `caption`) → `{ url, caption, prompt, run_id }` for chat-only edit when UI uses standalone path; document mode can also call edit later via existing figure edit.

## Pipeline

- Saved under `runs/uploads/<stamp>/user_photos/`.
- Convert JPEG→PNG; ids `usr_01`, `usr_02`.
- Intent notes uploaded slots; figures with `source: "upload"` skip `/generate`, PNG copied into `figures/`.
- Remaining `max_images` budget may still call Image API for LLM-planned `fig_*`.

## UI

- Composer: attach button, thumb chips, mode toggle.
- `canSend`: document needs Source; edit needs ≥1 photo + Intent text.
