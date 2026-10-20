# Liber Image API (office FastAPI wrapper)

## Goal

Replace OpenAI-like “Kandinsky” client with the office image service:

- `POST {base}/generate` — JSON `{prompt, width, height, steps, guidance, seed}` → `string` (image bytes as base64 / data-URL / URL)
- `POST {base}/edit` — multipart `prompt` + `image` (+ same knobs) → `string`

Figures appear in chat preview, PDF, and DOCX. Liber chat: **Изменить** on a photo opens a modal with two actions — **Новая генерация** / **Внести изменения**.

## Env

- `IMAGE_API_BASE_URL` (primary), aliases `KANDINSKY_API_BASE_URL`
- `IMAGE_MAX_IMAGES` / `KANDINSKY_MAX_IMAGES` (ceiling)
- `IMAGE_WIDTH`, `IMAGE_HEIGHT`, `IMAGE_STEPS`, `IMAGE_GUIDANCE`, `IMAGE_SEED`, `IMAGE_TIMEOUT_S`
- Private LAN hosts allowed for the API base (office `192.168.x.x`)

## Pipeline

Unchanged flow: LLM emits `figures[]` with EN `prompt` → `generate_all_figures` → inject → render. Client calls `/generate`.

## Liber edit

`POST /api/runs/{run_id}/figures/{fig_id}/edit` body `{mode: "generate"|"edit", prompt: str}` → rewrite PNG + rebuild PDF/DOCX (same path as chart edit).

## Prompts

System + UI intent: when max_images > 0 and Intent asks for photos, emit high-quality photographic English prompts; never use figures for KPI numbers.
