"""Patch one TeX prose paragraph from Liber Preview edit, then rebuild docs."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from case3.render import RenderError, render_tex
from case3.tex_preview import find_paragraph_spans
from case3.tex_safe import escape_tex_text

log = logging.getLogger("case3.paragraph_edit")

_MAX_CHARS = 12_000


class ParagraphEditError(RuntimeError):
    pass


def validate_paragraph_text(text: str) -> str:
    t = (text or "").strip()
    if len(t) < 1:
        raise ParagraphEditError("текст абзаца пуст")
    if len(t) > _MAX_CHARS:
        raise ParagraphEditError(f"слишком длинный абзац (макс. {_MAX_CHARS})")
    return t


def serialize_paragraph_tex(text: str) -> str:
    """Plain Liber prose → TeX (blank lines → separate paragraphs)."""
    t = validate_paragraph_text(text)
    parts = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    if not parts:
        raise ParagraphEditError("текст абзаца пуст")
    return "\n\n".join(escape_tex_text(p) for p in parts)


def patch_paragraph_in_tex(tex: str, paragraph_index: int, text: str) -> str:
    """Replace the ``paragraph_index``-th (1-based) preview paragraph."""
    new_tex_body = serialize_paragraph_tex(text)
    spans = find_paragraph_spans(tex)
    if paragraph_index < 1 or paragraph_index > len(spans):
        raise ParagraphEditError(
            f"абзац {paragraph_index} не найден (всего {len(spans)})"
        )
    start, end = spans[paragraph_index - 1]
    return tex[:start] + new_tex_body + tex[end:]


def edit_paragraph_in_run(
    out_dir: Path,
    paragraph_index: int,
    *,
    text: str,
    formats: set[str] | None = None,
) -> dict[str, Any]:
    """Patch TeX paragraph and rebuild PDF/DOCX."""
    out_dir = out_dir.resolve()
    validate_paragraph_text(text)

    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        raise ParagraphEditError("no .tex in run")
    from case3.run_undo import capture_before_edit

    capture_before_edit(out_dir, kind="paragraph", target=str(paragraph_index))
    tex_path = texs[0]
    tex_bak = tex_path.read_text(encoding="utf-8")

    meta_path = out_dir / "meta.json"
    meta_bak = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else None

    try:
        patched = patch_paragraph_in_tex(tex_bak, paragraph_index, text)
        tex_path.write_text(patched, encoding="utf-8")
    except ParagraphEditError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ParagraphEditError(f"patch failed: {exc}") from exc

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta["last_paragraph_edit"] = {
        "index": paragraph_index,
        "chars": len(text or ""),
        "preview": (text or "")[:240],
        "ts": int(time.time()),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    fmt = formats or {"pdf", "docx"}
    figs_dir = out_dir / "figures"
    try:
        artifacts = render_tex(
            tex_path,
            out_dir=out_dir,
            formats=fmt,
            extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
            log_dir=out_dir / "logs",
            force=True,
            project_root=out_dir.resolve().parents[2],
        )
    except RenderError as exc:
        tex_path.write_text(tex_bak, encoding="utf-8")
        if meta_bak is not None:
            meta_path.write_text(meta_bak, encoding="utf-8")
        from case3.run_undo import clear_undo

        clear_undo(out_dir)
        raise ParagraphEditError(f"document rebuild failed: {exc}") from exc

    v = int(time.time())
    from case3.run_undo import undo_meta

    return {
        "paragraph_index": paragraph_index,
        "text": text,
        "artifacts": {k: str(p) for k, p in artifacts.items()},
        "version": v,
        "media_status": meta.get("media_status") or {},
        "undo": undo_meta(out_dir),
    }
