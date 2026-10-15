"""Kandinsky / OpenAI-compatible image API client (SSRF-hardened)."""

from __future__ import annotations

import base64
import ipaddress
import json
import logging
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("case3.kandinsky")

_MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MiB


def _env(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return default


def _safe_number(raw: str | None, default: float, kind=float):
    try:
        return kind(raw) if raw is not None else default
    except (TypeError, ValueError):
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
    allow_url_download: bool

    @property
    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        path = self.endpoint_path if self.endpoint_path.startswith("/") else f"/{self.endpoint_path}"
        return f"{base}{path}"

    @classmethod
    def from_env(cls) -> KandinskyConfig:
        max_images = int(_safe_number(_env("KANDINSKY_MAX_IMAGES", default="0"), 0, int))
        allow_url = (_env("KANDINSKY_ALLOW_URL_DOWNLOAD", default="0") or "0").lower() in {
            "1",
            "true",
            "yes",
        }
        return cls(
            base_url=_env("KANDINSKY_API_BASE_URL", "IMAGE_API_BASE_URL") or "",
            api_key=_env("KANDINSKY_API_KEY", "IMAGE_API_KEY"),
            endpoint_path=_env("KANDINSKY_ENDPOINT_PATH", default="/v1/images/generations")
            or "/v1/images/generations",
            timeout_s=_safe_number(_env("KANDINSKY_TIMEOUT_S", default="120"), 120.0, float),
            model=_env("KANDINSKY_MODEL"),
            size=_env("KANDINSKY_SIZE", default="1024x1024") or "1024x1024",
            max_images=max(0, max_images),
            allow_url_download=allow_url,
        )


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_safe_image_url(url: str) -> urllib.parse.ParseResult:
    """Allow only http(s) to public hosts — blocks SSRF to LAN/metadata."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise RuntimeError(f"blocked image URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise RuntimeError("blocked image URL: empty host")
    host = parsed.hostname
    # Block obvious metadata / localhost names
    blocked_hosts = {"localhost", "metadata.google.internal"}
    if host.lower() in blocked_hosts or host.lower().endswith(".local"):
        raise RuntimeError(f"blocked image host: {host}")
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise RuntimeError(f"cannot resolve image host: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not _is_public_ip(ip):
            raise RuntimeError(f"blocked non-public image IP for {host}: {ip}")
    return parsed


def _write_png_bytes(dest: Path, data: bytes) -> None:
    if len(data) > _MAX_IMAGE_BYTES:
        raise RuntimeError(f"image too large: {len(data)} bytes")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("image is not PNG (need PNG for LaTeX path figures/<id>.png)")
    dest.write_bytes(data)


def _download_url(url: str, dest: Path, *, timeout_s: float) -> None:
    assert_safe_image_url(url)
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read(_MAX_IMAGE_BYTES + 1)
    if len(data) > _MAX_IMAGE_BYTES:
        raise RuntimeError("image download exceeded size limit")
    # keep .png name; if jpeg bytes, still write as .png path only if png magic
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        dest.write_bytes(data)
    elif data[:3] == b"\xff\xd8\xff":
        # pipeline expects .png path in TeX — convert not available; reject
        raise RuntimeError("JPEG URL not supported; API must return PNG b64_json")
    else:
        raise RuntimeError("downloaded bytes are not PNG")


def generate_png(cfg: KandinskyConfig, prompt: str, dest: Path) -> None:
    """POST OpenAI-like images API; prefer b64_json (no SSRF)."""
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

    # top-level b64
    b64 = payload.get("b64_json") or payload.get("image") if isinstance(payload, dict) else None
    if isinstance(b64, str):
        _write_png_bytes(dest, base64.b64decode(b64))
        return

    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"unexpected image response: {str(payload)[:160]}")

    first = items[0]
    if not isinstance(first, dict):
        raise RuntimeError("unexpected image data item")
    if "b64_json" in first:
        _write_png_bytes(dest, base64.b64decode(first["b64_json"]))
        return
    if "url" in first:
        if not cfg.allow_url_download:
            raise RuntimeError(
                "API returned url but KANDINSKY_ALLOW_URL_DOWNLOAD=0 "
                "(prefer b64_json; set =1 only if URL is public https)"
            )
        _download_url(str(first["url"]), dest, timeout_s=cfg.timeout_s)
        return
    raise RuntimeError("no b64_json in image response")


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
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            RuntimeError,
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            status[fid] = {"ok": False, "error": str(exc)[:300]}
            log.warning("image failed %s: %s", fid, exc)
            if dest.exists():
                dest.unlink()
    return status
