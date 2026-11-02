"""Patch one TeX itemize/enumerate from Liber Preview edit."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from case3.render import RenderError
from case3.run_rebuild import rebuild_run_docs
from case3.tex_preview import find_list_spans
from case3.tex_safe import escape_tex_text

log = logging.getLogger("case3.list_edit")

_MAX_ITEMS = 80
_MAX_ITEM_CHARS = 2_000
_BEGIN_ENV = re.compile(r"\\begin\{(itemize|enumerate)\}", re.I)


class ListEditError(RuntimeError):
    pass


def validate_list_items(items: list[str]) -> list[str]:
    if not items:
        raise ListEditError("список пуст")
    if len(items) > _MAX_ITEMS:
        raise ListEditError(f"слишком много пунктов (макс. {_MAX_ITEMS})")
    cleaned: list[str] = []
    for raw in items:
        t = (raw or "").strip()
        if not t:
            continue
        if len(t) > _MAX_ITEM_CHARS:
            raise ListEditError(
                f"слишком длинный пункт (макс. {_MAX_ITEM_CHARS})"
            )
        cleaned.append(t)
    if not cleaned:
        raise ListEditError("список пуст")
    return cleaned


def serialize_list_tex(
    items: list[str], *, ordered: bool
) -> str:
    env = "enumerate" if ordered else "itemize"
    lines = [rf"\begin{{{env}}}"]
    for it in items:
        lines.append(rf"  \item {escape_tex_text(it)}")
    lines.append(rf"\end{{{env}}}")
    return "\n".join(lines)


def patch_list_in_tex(
    tex: str,
    list_index: int,
    items: list[str],
    *,
    ordered: bool | None = None,
) -> str:
    """Replace the ``list_index``-th (1-based) preview list block."""
    cleaned = validate_list_items(items)
    spans = find_list_spans(tex)
    if list_index < 1 or list_index > len(spans):
        raise ListEditError(
            f"список {list_index} не найден (всего {len(spans)})"
        )
    start, end = spans[list_index - 1]
    old = tex[start:end]
    m = _BEGIN_ENV.search(old)
    if not m:
        raise ListEditError("не удалось разобрать окружение списка")
    was_ordered = m.group(1).lower() == "enumerate"
    use_ordered = was_ordered if ordered is None else bool(ordered)
    new_block = serialize_list_tex(cleaned, ordered=use_ordered)
    return tex[:start] + new_block + tex[end:]


def edit_list_in_run(
    out_dir: Path,
    list_index: int,
    *,
    items: list[str],
    ordered: bool | None = None,
    formats: set[str] | None = None,
) -> dict[str, Any]:
    """Patch TeX list and rebuild PDF/DOCX."""
    out_dir = out_dir.resolve()
    cleaned = validate_list_items(items)

    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        raise ListEditError("no .tex in run")
    from case3.run_undo import capture_before_edit

    capture_before_edit(out_dir, kind="list", target=str(list_index))
    tex_path = texs[0]
    tex_bak = tex_path.read_text(encoding="utf-8")

    meta_path = out_dir / "meta.json"
    meta_bak = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else None

    try:
        patched = patch_list_in_tex(
            tex_bak, list_index, cleaned, ordered=ordered
        )
        tex_path.write_text(patched, encoding="utf-8")
    except ListEditError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ListEditError(f"patch failed: {exc}") from exc

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta["last_list_edit"] = {
        "index": list_index,
        "items": len(cleaned),
        "preview": cleaned[0][:240] if cleaned else "",
        "ts": int(time.time()),
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    try:
        artifacts = rebuild_run_docs(out_dir, formats=formats)
    except FileNotFoundError as exc:
        raise ListEditError(str(exc)) from exc
    except RenderError as exc:
        tex_path.write_text(tex_bak, encoding="utf-8")
        if meta_bak is not None:
            meta_path.write_text(meta_bak, encoding="utf-8")
        from case3.run_undo import clear_undo

        clear_undo(out_dir)
        raise ListEditError(f"document rebuild failed: {exc}") from exc

    v = int(time.time())
    from case3.run_undo import undo_meta

    return {
        "list_index": list_index,
        "items": cleaned,
        "artifacts": {k: str(p) for k, p in artifacts.items()},
        "version": v,
        "media_status": meta.get("media_status") or {},
        "undo": undo_meta(out_dir),
    }
