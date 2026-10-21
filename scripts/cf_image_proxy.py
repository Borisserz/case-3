#!/usr/bin/env python3
"""Local office-shaped Image API → Cloudflare Workers AI REST (no Worker deploy).

Env (repo .env — never .env.example):
  CLOUDFLARE_ACCOUNT_ID
  CLOUDFLARE_API_TOKEN   (API Token with Account → Workers AI:Edit)
  IMAGE_PROXY_PORT=8787  (optional)

case-3:
  IMAGE_API_BASE_URL=http://127.0.0.1:8787
  IMAGE_MAX_IMAGES=2
"""

from __future__ import annotations

import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, parse, request

GEN_MODEL = "@cf/black-forest-labs/flux-1-schnell"
EDIT_MODEL = "@cf/runwayml/stable-diffusion-v1-5-img2img"

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _cfg() -> tuple[str, str]:
    acc = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    tok = (os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    if not acc or not tok:
        raise SystemExit(
            "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env "
            "(Dash → My Profile → API Tokens → Create → Workers AI Edit)"
        )
    return acc, tok


def _ai_run(account_id: str, token: str, model: str, payload: dict[str, Any]) -> Any:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            body = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"CF AI {exc.code}: {err}") from exc

    if "application/json" in ctype or body[:1] in (b"{", b"["):
        parsed = json.loads(body.decode("utf-8"))
        if isinstance(parsed, dict) and parsed.get("success") is False:
            raise RuntimeError(f"CF AI error: {parsed.get('errors')}")
        if isinstance(parsed, dict) and "result" in parsed:
            return parsed["result"]
        return parsed
    return body


def _to_b64(result: Any) -> str:
    if isinstance(result, (bytes, bytearray)):
        return base64.b64encode(bytes(result)).decode("ascii")
    if isinstance(result, str):
        s = result.strip()
        if s.startswith("data:"):
            return s.split(",", 1)[1]
        return "".join(s.split())
    if isinstance(result, dict):
        for k in ("image", "b64_json", "png"):
            if k in result:
                return _to_b64(result[k])
        raise RuntimeError(f"unexpected result keys: {list(result)[:8]}")
    raise RuntimeError(f"unexpected result type: {type(result).__name__}")


def _strip_b64(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        s = s.split(",", 1)[1]
    return "".join(s.split())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, obj: Any) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path in {"/", "/health"}:
            self._send(
                200,
                {
                    "ok": True,
                    "service": "cf-image-proxy",
                    "generate_model": GEN_MODEL,
                    "edit_model": EDIT_MODEL,
                },
            )
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b""
        acc, tok = _cfg()
        try:
            if path == "/generate":
                body = json.loads(raw.decode("utf-8") or "{}")
                prompt = str(body.get("prompt") or "").strip()
                if not prompt:
                    self._send(400, {"error": "prompt required"})
                    return
                steps = max(1, min(8, int(body.get("steps") or 4)))
                payload: dict[str, Any] = {"prompt": prompt, "steps": steps}
                seed = int(body.get("seed") or 0)
                if seed > 0:
                    payload["seed"] = seed
                result = _ai_run(acc, tok, GEN_MODEL, payload)
                self._send(200, {"image": _to_b64(result)})
                return

            if path == "/edit":
                ctype = (self.headers.get("Content-Type") or "").lower()
                prompt = ""
                image_b64 = ""
                steps = 10
                strength = 0.75
                seed = 0
                if "multipart/form-data" in ctype:
                    # case-3 also sends file multipart; extract crude base64/file parts
                    self._send(
                        400,
                        {
                            "error": "use form-urlencoded image=<base64> "
                            "(case-3 default) or application/json"
                        },
                    )
                    return
                if "application/x-www-form-urlencoded" in ctype:
                    fields = parse.parse_qs(raw.decode("utf-8"), keep_blank_values=True)
                    prompt = (fields.get("prompt") or [""])[0].strip()
                    image_b64 = (fields.get("image") or fields.get("images") or [""])[0]
                    steps = int((fields.get("steps") or ["10"])[0] or 10)
                    strength = float((fields.get("strength") or ["0.75"])[0] or 0.75)
                    seed = int((fields.get("seed") or ["0"])[0] or 0)
                else:
                    body = json.loads(raw.decode("utf-8") or "{}")
                    prompt = str(body.get("prompt") or "").strip()
                    image_b64 = str(body.get("image") or body.get("images") or "")
                    steps = int(body.get("steps") or 10)
                    strength = float(body.get("strength") or 0.75)
                    seed = int(body.get("seed") or 0)

                if not prompt:
                    self._send(400, {"error": "prompt required"})
                    return
                image_b64 = _strip_b64(image_b64)
                if len(image_b64) < 32:
                    self._send(400, {"error": "edit requires source image"})
                    return
                payload = {
                    "prompt": prompt,
                    "image_b64": image_b64,
                    "strength": max(0.05, min(1.0, strength)),
                    "num_steps": max(1, min(20, steps)),
                }
                if seed > 0:
                    payload["seed"] = seed
                result = _ai_run(acc, tok, EDIT_MODEL, payload)
                self._send(200, {"image": _to_b64(result)})
                return

            self._send(404, {"error": "not found", "path": path})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"error": str(exc)[:400]})


def main() -> None:
    _load_dotenv()
    _cfg()
    port = int(os.environ.get("IMAGE_PROXY_PORT") or "8787")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"cf-image-proxy on http://127.0.0.1:{port}  (Ctrl+C stop)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
