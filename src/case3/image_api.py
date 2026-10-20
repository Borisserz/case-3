"""Office Image API client: POST /generate + POST /edit (FastAPI wrapper).

Not Kandinsky / OpenAI images — local service e.g. http://192.168.4.101:8000
"""

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

import httpx

log = logging.getLogger("case3.image_api")

_MAX_IMAGE_BYTES = 12 * 1024 * 1024


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
class ImageApiConfig:
    base_url: str
    timeout_s: float
    max_images: int
    width: int
    height: int
    steps: int
    guidance: float
    seed: int
    allow_url_download: bool
    api_key: str | None = None

    @property
    def generate_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/generate"

    @property
    def edit_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/edit"

    @classmethod
    def from_env(cls) -> ImageApiConfig:
        max_images = int(
            _safe_number(
                _env("IMAGE_MAX_IMAGES", "KANDINSKY_MAX_IMAGES", default="0"),
                0,
                int,
            )
        )
        allow_url = (_env("IMAGE_ALLOW_URL_DOWNLOAD", "KANDINSKY_ALLOW_URL_DOWNLOAD", default="0") or "0").lower() in {
            "1",
            "true",
            "yes",
        }
        w, h = 1024, 1024
        size = _env("IMAGE_SIZE", "KANDINSKY_SIZE", default="1024x1024") or "1024x1024"
        if "x" in size.lower():
            try:
                a, b = size.lower().split("x", 1)
                w, h = int(a), int(b)
            except ValueError:
                pass
        w = int(_safe_number(_env("IMAGE_WIDTH", default=str(w)), w, int))
        h = int(_safe_number(_env("IMAGE_HEIGHT", default=str(h)), h, int))
        return cls(
            base_url=_env("IMAGE_API_BASE_URL", "KANDINSKY_API_BASE_URL") or "",
            timeout_s=_safe_number(_env("IMAGE_TIMEOUT_S", "KANDINSKY_TIMEOUT_S", default="180"), 180.0, float),
            max_images=max(0, max_images),
            width=max(64, min(w, 2048)),
            height=max(64, min(h, 2048)),
            steps=int(_safe_number(_env("IMAGE_STEPS", default="4"), 4, int)),
            guidance=_safe_number(_env("IMAGE_GUIDANCE", default="3"), 3.0, float),
            seed=int(_safe_number(_env("IMAGE_SEED", default="0"), 0, int)),
            allow_url_download=allow_url,
            api_key=_env("IMAGE_API_KEY", "KANDINSKY_API_KEY"),
        )


def image_api_configured() -> bool:
    return bool(ImageApiConfig.from_env().base_url)


def max_images_from_env() -> int:
    return ImageApiConfig.from_env().max_images


def _headers(cfg: ImageApiConfig) -> dict[str, str]:
    h: dict[str, str] = {}
    if cfg.api_key:
        h["Authorization"] = f"Bearer {cfg.api_key}"
    return h


def _knobs(cfg: ImageApiConfig) -> dict[str, Any]:
    return {
        "width": cfg.width,
        "height": cfg.height,
        "steps": cfg.steps,
        "guidance": cfg.guidance,
        "seed": cfg.seed,
    }


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def _is_jpeg(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff"


def _jpeg_to_png(data: bytes) -> bytes:
    try:
        from io import BytesIO

        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "image API returned JPEG; install pillow or configure API for PNG"
        ) from exc
    im = Image.open(BytesIO(data))
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _write_image_bytes(dest: Path, data: bytes) -> None:
    if len(data) > _MAX_IMAGE_BYTES:
        raise RuntimeError(f"image too large: {len(data)} bytes")
    if _is_jpeg(data):
        data = _jpeg_to_png(data)
    if not _is_png(data):
        raise RuntimeError("image is not PNG/JPEG")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def _host_allowed_for_download(url: str, *, api_base: str) -> bool:
    """Allow public https OR same host as IMAGE_API_BASE_URL (office LAN)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    api = urllib.parse.urlparse(api_base if "://" in api_base else f"http://{api_base}")
    if api.hostname and parsed.hostname.lower() == api.hostname.lower():
        return True
    # public only
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 80)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    return True


def _download_url(url: str, dest: Path, *, cfg: ImageApiConfig) -> None:
    # Always enforce host policy (office same-host OR public when allow flag).
    if not _host_allowed_for_download(url, api_base=cfg.base_url):
        if not cfg.allow_url_download:
            raise RuntimeError(
                "API returned url but download blocked "
                "(prefer base64 string; set IMAGE_ALLOW_URL_DOWNLOAD=1 for public https)"
            )
        # flag on → still require public host (no LAN/metadata)
        parsed = urllib.parse.urlparse(url)
        if not parsed.hostname:
            raise RuntimeError("blocked empty image host")
        try:
            infos = socket.getaddrinfo(parsed.hostname, parsed.port or 80)
        except socket.gaierror as exc:
            raise RuntimeError(f"cannot resolve image host: {parsed.hostname}") from exc
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise RuntimeError(f"blocked non-public image IP: {ip}")
    # No redirect follow → prevents SSRF via 302 to metadata/LAN
    with httpx.Client(timeout=cfg.timeout_s, follow_redirects=False) as client:
        resp = client.get(url)
        if resp.is_redirect:
            raise RuntimeError("image URL redirects are not followed")
        resp.raise_for_status()
        data = resp.content
    if len(data) > _MAX_IMAGE_BYTES:
        raise RuntimeError("image download exceeded size limit")
    _write_image_bytes(dest, data)


def _looks_like_image_path(s: str) -> bool:
    """Relative paths from office wrappers: outputs/foo.png (not base64)."""
    low = s.lower()
    if any(low.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return True
    if "/" in s and not s.startswith("data:"):
        # path-ish: slash + dotted filename (`.` is not in the base64 alphabet)
        return "." in s.rsplit("/", 1)[-1]
    return False


def _join_api_path(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def decode_image_string(payload: Any, *, cfg: ImageApiConfig, dest: Path) -> None:
    """Decode FastAPI `str` (or dict) image response into dest PNG."""
    # JSON object wrappers
    if isinstance(payload, dict):
        for key in ("b64_json", "image", "data", "result", "png", "content", "url", "path"):
            if key in payload:
                return decode_image_string(payload[key], cfg=cfg, dest=dest)
        raise RuntimeError(f"unexpected image object keys: {list(payload)[:8]}")

    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
        if _is_png(raw) or _is_jpeg(raw):
            _write_image_bytes(dest, raw)
            return
        payload = raw.decode("utf-8", errors="replace")

    if isinstance(payload, list) and payload:
        return decode_image_string(payload[0], cfg=cfg, dest=dest)

    if not isinstance(payload, str):
        raise RuntimeError(f"unexpected image payload type: {type(payload).__name__}")

    s = payload.strip().strip('"').strip("'")
    if not s:
        raise RuntimeError("empty image string")

    # data URL
    if s.startswith("data:image"):
        try:
            b64 = s.split(",", 1)[1]
        except IndexError as exc:
            raise RuntimeError("bad data URL") from exc
        _write_image_bytes(dest, base64.b64decode(b64))
        return

    # Absolute or relative URL / path (join with Image API base)
    if s.startswith("http://") or s.startswith("https://"):
        _download_url(s, dest, cfg=cfg)
        return
    if cfg.base_url and (s.startswith("/") or _looks_like_image_path(s)):
        _download_url(_join_api_path(cfg.base_url, s), dest, cfg=cfg)
        return

    # raw base64 (with optional whitespace/newlines)
    compact = "".join(s.split())
    try:
        data = base64.b64decode(compact, validate=False)
    except Exception as exc:
        snip = s[:80].replace("\n", " ")
        raise RuntimeError(
            f"image string is not base64/data-URL/URL (got {snip!r})"
        ) from exc
    if len(data) < 32:
        raise RuntimeError("decoded image too small")
    _write_image_bytes(dest, data)


def _parse_http_body(resp: httpx.Response) -> Any:
    ctype = (resp.headers.get("content-type") or "").lower()
    raw = resp.content or b""
    if "image/" in ctype or _is_png(raw) or _is_jpeg(raw):
        return raw
    text = raw.decode("utf-8", errors="replace") if raw else (resp.text or "")
    if "application/json" in ctype or (text[:1] in "{\"[") :
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def generate_png(cfg: ImageApiConfig, prompt: str, dest: Path) -> None:
    """POST /generate — new image from prompt."""
    if not cfg.base_url:
        raise RuntimeError("IMAGE_API_BASE_URL is empty")
    body = {"prompt": (prompt or "").strip(), **_knobs(cfg)}
    if not body["prompt"]:
        raise RuntimeError("empty image prompt")
    with httpx.Client(timeout=cfg.timeout_s) as client:
        resp = client.post(cfg.generate_url, json=body, headers=_headers(cfg))
        resp.raise_for_status()
        payload = _parse_http_body(resp)
    decode_image_string(payload, cfg=cfg, dest=dest)


def edit_png(
    cfg: ImageApiConfig,
    prompt: str,
    source_png: Path,
    dest: Path,
) -> None:
    """POST /edit — multipart prompt + image file."""
    if not cfg.base_url:
        raise RuntimeError("IMAGE_API_BASE_URL is empty")
    if not source_png.is_file():
        raise RuntimeError(f"source image missing: {source_png}")
    prompt = (prompt or "").strip()
    if not prompt:
        raise RuntimeError("empty edit prompt")
    png_bytes = source_png.read_bytes()
    data = {"prompt": prompt, **{k: str(v) for k, v in _knobs(cfg).items()}}
    files = {"image": (source_png.name, png_bytes, "image/png")}
    with httpx.Client(timeout=cfg.timeout_s) as client:
        resp = client.post(cfg.edit_url, data=data, files=files, headers=_headers(cfg))
        # Some wrappers expect image as repeated form field of base64 strings
        if resp.status_code >= 400:
            b64 = base64.b64encode(png_bytes).decode("ascii")
            data2 = {**data, "image": b64}
            resp = client.post(cfg.edit_url, data=data2, headers=_headers(cfg))
        resp.raise_for_status()
        payload = _parse_http_body(resp)
    decode_image_string(payload, cfg=cfg, dest=dest)


def generate_all_figures(
    figures: list[dict[str, Any]],
    figures_dir: Path,
    *,
    cfg: ImageApiConfig | None = None,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    cfg = cfg or ImageApiConfig.from_env()
    figures_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {}
    if cfg.max_images <= 0 or not cfg.base_url:
        return status
    for fig in figures[: cfg.max_images]:
        fid = fig["id"]
        if on_progress:
            on_progress(fid)
        dest = figures_dir / f"{fid}.png"
        try:
            generate_png(cfg, str(fig.get("prompt") or ""), dest)
            status[fid] = {"ok": True, "path": str(dest), "kind": "figure"}
            log.info("image ok %s → %s", fid, dest)
        except (
            httpx.HTTPError,
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            RuntimeError,
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            status[fid] = {"ok": False, "error": str(exc)[:300], "kind": "figure"}
            log.warning("image failed %s: %s", fid, exc)
            if dest.exists():
                dest.unlink()
    return status


# Back-compat alias used by older imports / health checks
KandinskyConfig = ImageApiConfig
