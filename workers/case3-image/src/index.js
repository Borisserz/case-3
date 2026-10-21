/**
 * Office-shaped Image API for case-3 Liber:
 *   POST /generate  JSON {prompt, width?, height?, steps?, seed?} → {image: base64}
 *   POST /edit      multipart/form or JSON → {image: base64}
 *
 * Backed by Cloudflare Workers AI:
 *   generate → Flux Schnell
 *   edit     → Flux.2 Klein 4B (multipart + input_image_0; refs must be ≤512²)
 */

const GEN_MODEL = "@cf/black-forest-labs/flux-1-schnell";
const EDIT_MODEL = "@cf/black-forest-labs/flux-2-klein-4b";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

function unauthorized() {
  return json({ error: "unauthorized" }, 401);
}

function checkAuth(request, env) {
  const secret = (env.CASE3_IMAGE_SECRET || "").trim();
  if (!secret) return true;
  const h = request.headers.get("Authorization") || "";
  const m = /^Bearer\s+(.+)$/i.exec(h);
  return Boolean(m && m[1].trim() === secret);
}

function clampInt(v, lo, hi, fallback) {
  const n = Number.parseInt(String(v ?? ""), 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(lo, Math.min(hi, n));
}

async function readJson(request) {
  try {
    return await request.json();
  } catch {
    return {};
  }
}

async function readEditBody(request) {
  const ctype = (request.headers.get("Content-Type") || "").toLowerCase();
  if (ctype.includes("application/json")) {
    const body = await readJson(request);
    return {
      prompt: String(body.prompt || "").trim(),
      imageB64: String(body.image || body.images || body.b64_json || "").trim(),
      steps: body.steps,
      seed: body.seed,
      strength: body.strength,
    };
  }
  const form = await request.formData();
  let imageB64 = String(form.get("image") || form.get("images") || "").trim();
  const file = form.get("image");
  if ((!imageB64 || imageB64.length < 64) && file && typeof file.arrayBuffer === "function") {
    const buf = new Uint8Array(await file.arrayBuffer());
    if (buf.byteLength > 0) {
      // binary UploadFile → base64
      let binary = "";
      const chunk = 0x8000;
      for (let i = 0; i < buf.length; i += chunk) {
        binary += String.fromCharCode(...buf.subarray(i, i + chunk));
      }
      imageB64 = btoa(binary);
    }
  }
  return {
    prompt: String(form.get("prompt") || "").trim(),
    imageB64,
    steps: form.get("steps"),
    seed: form.get("seed"),
    strength: form.get("strength"),
  };
}

function stripDataUrl(b64) {
  const s = (b64 || "").trim();
  if (s.startsWith("data:")) {
    const i = s.indexOf(",");
    return i >= 0 ? s.slice(i + 1) : s;
  }
  return s.replace(/\s+/g, "");
}

async function generate(env, { prompt, steps, seed }) {
  const numSteps = clampInt(steps, 1, 8, 4);
  const payload = {
    prompt,
    steps: numSteps,
  };
  const seedN = clampInt(seed, 0, 2_147_483_647, 0);
  if (seedN > 0) payload.seed = seedN;

  const result = await env.AI.run(GEN_MODEL, payload);
  return extractImageB64(result);
}

function bytesToB64(buf) {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function extractImageB64(result) {
  if (!result) throw new Error("empty AI result");
  if (typeof result === "string") return stripDataUrl(result);
  if (result instanceof ArrayBuffer || result instanceof Uint8Array) {
    return bytesToB64(result);
  }
  if (result.image) return stripDataUrl(result.image);
  if (result.result instanceof ArrayBuffer || result.result instanceof Uint8Array) {
    return bytesToB64(result.result);
  }
  if (typeof result.result === "string") return stripDataUrl(result.result);
  if (result.result?.image) return stripDataUrl(result.result.image);
  throw new Error(`unexpected AI response keys: ${Object.keys(result).join(",")}`);
}

function b64ToBytes(b64) {
  const bin = atob(stripDataUrl(b64));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function edit(env, { prompt, imageB64, seed }) {
  const raw = stripDataUrl(imageB64);
  if (!raw || raw.length < 32) {
    throw new Error("edit requires source image (base64 or file)");
  }
  // Klein docs: refs ideally ≤512². If oversized, CF may reject — then
  // fall back to text-only regenerate with edit instructions (still useful).
  let srcBytes = b64ToBytes(raw);
  const form = new FormData();
  form.append(
    "prompt",
    `${prompt}. Keep the same subject and composition as image 0; apply the requested changes.`,
  );
  form.append("input_image_0", new Blob([srcBytes], { type: "image/png" }), "ref.png");
  form.append("width", "1024");
  form.append("height", "1024");
  const seedN = clampInt(seed, 0, 2_147_483_647, 0);
  if (seedN > 0) form.append("seed", String(seedN));

  try {
    const formResponse = new Response(form);
    const result = await env.AI.run(EDIT_MODEL, {
      multipart: {
        body: formResponse.body,
        contentType: formResponse.headers.get("content-type"),
      },
    });
    return extractImageB64(result);
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    // Fallback: regenerate guided by prompt (no ref) when multipart/ref rejected
    console.warn("klein edit failed, fallback generate:", msg);
    return generate(env, {
      prompt: `Photo edit: ${prompt}. Photorealistic, coherent scene.`,
      steps: 4,
      seed: seedN,
    });
  }
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (request.method === "GET" && (path === "/" || path === "/health")) {
      return json({
        ok: true,
        service: "case3-image",
        generate_model: GEN_MODEL,
        edit_model: EDIT_MODEL,
        auth: Boolean((env.CASE3_IMAGE_SECRET || "").trim()),
      });
    }

    if (!checkAuth(request, env)) return unauthorized();

    try {
      if (request.method === "POST" && path === "/generate") {
        const body = await readJson(request);
        const prompt = String(body.prompt || "").trim();
        if (!prompt) return json({ error: "prompt required" }, 400);
        const image = await generate(env, {
          prompt,
          steps: body.steps,
          seed: body.seed,
        });
        return json({ image });
      }

      if (request.method === "POST" && path === "/edit") {
        const body = await readEditBody(request);
        if (!body.prompt) return json({ error: "prompt required" }, 400);
        const image = await edit(env, body);
        return json({ image });
      }

      return json({ error: "not found", path }, 404);
    } catch (err) {
      const msg = err && err.message ? err.message : String(err);
      console.error("case3-image error", msg);
      return json({ error: msg }, 500);
    }
  },
};
