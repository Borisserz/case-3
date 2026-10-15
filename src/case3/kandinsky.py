"""Kandinsky / OpenAI-compatible image API client."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("case3.kandinsky")


def _env(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return default


@dataclass(frozen=True)
class KandinskyConfig:
    base_url: str
    api_key: str | None
    endpoint_path: str
    timeout_s: float
    model: str | None
    size: str
    max_images: int

    @property
    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        path = self.endpoint_path if self.endpoint_path.startswith("/") else f"/{self.endpoint_path}"
        return f"{base}{path}"

    @classmethod
    def from_env(cls) -> KandinskyConfig:
        max_images = int(_env("KANDINSKY_MAX_IMAGES", default="0") or "0")
        base = _env("KANDINSKY_API_BASE_URL", "IMAGE_API_BASE_URL") or ""
        return cls(
            base_url=base,
            api_key=_env("KANDINSKY_API_KEY", "IMAGE_API_KEY"),
            endpoint_path=_env("KANDINSKY_ENDPOINT_PATH", default="/v1/images/generations") or "/v1/images/generations",
            timeout_s=float(_env("KANDINSKY_TIMEOUT_S", default="120") or "120"),
            model=_env("KANDINSKY_MODEL"),
            size=_env("KANDINSKY_SIZE", default="1024x1024") or "1024x1024",
            max_images=max(0, max_images),
        )


def generate_png(cfg: KandinskyConfig, prompt: str, dest: Path) -> None:
    """POST OpenAI-like images API; write PNG to dest."""
    if not cfg.base_url:
        raise RuntimeError("KANDINSKY_API_BASE_URL is empty")
    body: dict[str, Any] = {"prompt": prompt, "n": 1, "size": cfg.size}
    if cfg.model:
        body["model"] = cfg.model
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    req = urllib.request.Request(cfg.endpoint, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=cfg.timeout_s) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        # alternate shapes
        b64 = payload.get("b64_json") or payload.get("image")
        if isinstance(b64, str):
            dest.write_bytes(base64.b64decode(b64))
            return
        raise RuntimeError(f"unexpected image response: {str(payload)[:200]}")

    first = items[0]
    if not isinstance(first, dict):
        raise RuntimeError("unexpected image data item")
    if "b64_json" in first:
        dest.write_bytes(base64.b64decode(first["b64_json"]))
        return
    if "url" in first:
        url = first["url"]
        with urllib.request.urlopen(url, timeout=cfg.timeout_s) as img:
            dest.write_bytes(img.read())
        return
    raise RuntimeError("no b64_json/url in image response")


def generate_all_figures(
    figures: list[dict[str, Any]],
    figures_dir: Path,
    *,
    cfg: KandinskyConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or KandinskyConfig.from_env()
    figures_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {}
    if cfg.max_images <= 0:
        return status
    for fig in figures[: cfg.max_images]:
        fid = fig["id"]
        dest = figures_dir / f"{fid}.png"
        try:
            generate_png(cfg, fig["prompt"], dest)
            status[fid] = {"ok": True, "path": str(dest)}
            log.info("image ok %s → %s", fid, dest)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
            status[fid] = {"ok": False, "error": str(exc)}
            log.warning("image failed %s: %s", fid, exc)
            if dest.exists():
                dest.unlink()
    return status
