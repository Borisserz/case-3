"""Save Liber-attached photos and turn them into figure slots (usr_XX)."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any

log = logging.getLogger("case3.user_photos")

_MAX_BYTES = 4 * 1024 * 1024
_MAX_COUNT = 2
_NAME_OK = re.compile(r"^[a-zA-Z0-9._ -]{1,120}$")


class UserPhotoError(ValueError):
    pass


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def _is_jpeg(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff"


def bytes_to_png(data: bytes) -> bytes:
    if len(data) > _MAX_BYTES:
        raise UserPhotoError(f"photo too large (>{_MAX_BYTES // (1024 * 1024)} MiB)")
    if _is_png(data):
        return data
    if _is_jpeg(data):
        try:
            from PIL import Image  # type: ignore
        except ImportError as exc:
            raise UserPhotoError("JPEG needs pillow — pip install pillow") from exc
        im = Image.open(BytesIO(data))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        buf = BytesIO()
        im.save(buf, format="PNG")
        out = buf.getvalue()
        if len(out) > _MAX_BYTES:
            raise UserPhotoError("converted PNG too large")
        return out
    raise UserPhotoError("photo must be PNG or JPEG")


def save_user_photos(
    upload_dir: Path,
    items: list[tuple[str, bytes]],
    *,
    captions: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Write PNGs to upload_dir/user_photos/ and return figure metas (source=upload)."""
    if len(items) > _MAX_COUNT:
        raise UserPhotoError(f"at most {_MAX_COUNT} photos")
    dest_dir = upload_dir / "user_photos"
    dest_dir.mkdir(parents=True, exist_ok=True)
    caps = list(captions or [])
    out: list[dict[str, Any]] = []
    for i, (filename, raw) in enumerate(items, start=1):
        name = Path(filename or f"photo_{i}.png").name
        if not _NAME_OK.match(name):
            name = f"photo_{i}.png"
        png = bytes_to_png(raw)
        fid = f"usr_{i:02d}"
        path = dest_dir / f"{fid}.png"
        path.write_bytes(png)
        cap = (caps[i - 1] if i - 1 < len(caps) else "").strip() or f"Фото {i}"
        out.append(
            {
                "id": fid,
                "caption": cap,
                "prompt": f"user upload: {name}",
                "width": r"0.85\textwidth",
                "source": "upload",
                "path": str(path),
            }
        )
        log.info("user photo %s ← %s (%d bytes)", fid, name, len(png))
    return out


def materialize_user_figures(
    figures: list[dict[str, Any]],
    figs_dir: Path,
) -> dict[str, Any]:
    """Copy upload-sourced figures into figs_dir; return media status entries."""
    figs_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {}
    for fig in figures:
        if str(fig.get("source") or "") != "upload":
            continue
        fid = str(fig.get("id") or "")
        src = Path(str(fig.get("path") or ""))
        if not fid or not src.is_file():
            status[fid or "?"] = {
                "ok": False,
                "error": "missing upload path",
                "kind": "figure",
            }
            continue
        dest = figs_dir / f"{fid}.png"
        dest.write_bytes(src.read_bytes())
        status[fid] = {"ok": True, "path": str(dest), "kind": "figure", "source": "upload"}
    return status


def merge_user_figures(
    llm_figures: list[dict[str, Any]],
    user_figures: list[dict[str, Any]],
    *,
    max_images: int,
) -> list[dict[str, Any]]:
    """User uploads first; then LLM figures that fit remaining budget."""
    budget = max(0, int(max_images))
    if budget <= 0:
        return []
    users = user_figures[:budget]
    rest = budget - len(users)
    llm = [f for f in llm_figures if str(f.get("source") or "") != "upload"]
    # avoid id clashes with usr_*
    llm = [f for f in llm if not str(f.get("id") or "").startswith("usr_")]
    return users + llm[:rest]


def ensure_user_slots_in_tex(tex: str, user_figures: list[dict[str, Any]]) -> str:
    """If LLM omitted %CASE3_FIG:usr_XX%, append slots before \\end{document}."""
    if not user_figures:
        return tex
    missing = [
        f for f in user_figures if f"%CASE3_FIG:{f['id']}%" not in tex and f"figures/{f['id']}.png" not in tex
    ]
    if not missing:
        return tex
    block = "\n".join(f"%CASE3_FIG:{f['id']}%" for f in missing) + "\n"
    marker = r"\end{document}"
    idx = tex.rfind(marker)
    if idx == -1:
        return tex.rstrip() + "\n\n" + block
    return tex[:idx] + "\n" + block + "\n" + tex[idx:]
