"""Patch one TeX section/subsection title from Liber Preview edit."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from case3.render import RenderError
from case3.run_rebuild import rebuild_run_docs
from case3.tex_preview import find_heading_spans
from case3.tex_safe import escape_tex_text

log = logging.getLogger("case3.heading_edit")

_MAX_CHARS = 400
_CMD = re.compile(r"^\\((?:sub)*section\*?)\{\s*([^{}]*)\}")


class HeadingEditError(RuntimeError):
    pass


def validate_heading_text(text: str) -> str:
    t = (text or "").strip()
    if len(t) < 1:
        raise HeadingEditError("заголовок пуст")
    if len(t) > _MAX_CHARS:
        raise HeadingEditError(f"слишком длинный заголовок (макс. {_MAX_CHARS})")
    if "\n" in t:
        raise HeadingEditError("заголовок должен быть одной строкой")
    return t


def patch_heading_in_tex(tex: str, heading_index: int, text: str) -> str:
    """Replace the ``heading_index``-th (1-based) preview heading title."""
    title = validate_heading_text(text)
    spans = find_heading_spans(tex)
    if heading_index < 1 or heading_index > len(spans):
        raise HeadingEditError(
            f"заголовок {heading_index} не найден (всего {len(spans)})"
        )
    start, end = spans[heading_index - 1]
    old = tex[start:end]
    m = _CMD.match(old)
    if not m:
        raise HeadingEditError("не удалось разобрать команду заголовка")
    cmd = m.group(1)
    new_tok = "\\" + cmd + "{" + escape_tex_text(title) + "}"
    return tex[:start] + new_tok + tex[end:]


def edit_heading_in_run(
    out_dir: Path,
    heading_index: int,
    *,
    text: str,
    formats: set[str] | None = None,
) -> dict[str, Any]:
    """Patch TeX heading and rebuild PDF/DOCX."""
    out_dir = out_dir.resolve()
    validate_heading_text(text)

    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        raise HeadingEditError("no .tex in run")
    from case3.run_undo import capture_before_edit

    capture_before_edit(out_dir, kind="heading", target=str(heading_index))
    tex_path = texs[0]
    tex_bak = tex_path.read_text(encoding="utf-8")

    meta_path = out_dir / "meta.json"
    meta_bak = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else None

    try:
        patched = patch_heading_in_tex(tex_bak, heading_index, text)
        tex_path.write_text(patched, encoding="utf-8")
    except HeadingEditError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HeadingEditError(f"patch failed: {exc}") from exc

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta["last_heading_edit"] = {
        "index": heading_index,
        "chars": len(text or ""),
        "preview": (text or "")[:240],
        "ts": int(time.time()),
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    try:
        artifacts = rebuild_run_docs(out_dir, formats=formats)
    except FileNotFoundError as exc:
        raise HeadingEditError(str(exc)) from exc
    except RenderError as exc:
        tex_path.write_text(tex_bak, encoding="utf-8")
        if meta_bak is not None:
            meta_path.write_text(meta_bak, encoding="utf-8")
        from case3.run_undo import clear_undo

        clear_undo(out_dir)
        raise HeadingEditError(f"document rebuild failed: {exc}") from exc

    v = int(time.time())
    from case3.run_undo import undo_meta

    return {
        "heading_index": heading_index,
        "text": text,
        "artifacts": {k: str(p) for k, p in artifacts.items()},
        "version": v,
        "media_status": meta.get("media_status") or {},
        "undo": undo_meta(out_dir),
    }
