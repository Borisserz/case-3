# case3-image (Cloudflare Worker)

Office-shaped shim: `POST /generate` + `POST /edit` → Workers AI (Flux Schnell / SD img2img).

**Negative prompt:** Liber may send `negative_prompt` in JSON/form; this worker currently **ignores** it — brand-safe bans are baked into `prompt` (`Avoid: …`) by `case3.image_prompt`.

## One-time: workers.dev subdomain

Account needs a `*.workers.dev` name (Wrangler cannot create it non-interactively):

1. Open https://dash.cloudflare.com/9e770da88324002391a432105430bf31/workers/onboarding  
2. Pick a subdomain (e.g. `case3barys`) → continue  
3. Back here:

```bash
cd workers/case3-image
npm install
npx wrangler login   # once
npm run dev          # http://127.0.0.1:8787
```

## Repo `.env` only (not `.env.example`)

```
IMAGE_API_BASE_URL=http://127.0.0.1:8787
IMAGE_MAX_IMAGES=2
IMAGE_STEPS=4
CLOUDFLARE_ACCOUNT_ID=9e770da88324002391a432105430bf31
```

Optional Worker auth: `npx wrangler secret put CASE3_IMAGE_SECRET` + matching `IMAGE_API_KEY`.

## Fallback without Worker (same :8787)

If subdomain is not ready yet — API token + REST proxy:

```bash
# .env: CLOUDFLARE_API_TOKEN=...  (Workers AI Edit)
python3 scripts/cf_image_proxy.py
```

## Deploy (optional)

```bash
npm run deploy
# IMAGE_API_BASE_URL=https://case3-image.<subdomain>.workers.dev
```
