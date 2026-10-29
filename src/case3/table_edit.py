"""Patch one TeX table from Liber Preview structured edit, then rebuild docs."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from case3.render import RenderError
from case3.run_rebuild import rebuild_run_docs
from case3.tex_safe import escape_tex_text

log = logging.getLogger("case3.table_edit")

_MAX_COLS = 40
_MAX_ROWS = 20

_TABLE_ENV = re.compile(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", re.S)
_CAPTION = re.compile(r"(\\caption\{)([^{}]*)(\})")
_TABULARX = re.compile(
    r"(\\begin\{tabularx\}\{[^}]+\}\{)([^}]+)(\})([\s\S]*?)(\\end\{tabularx\})"
)
_TABULAR = re.compile(
    r"(\\begin\{tabular\}\{)([^}]+)(\})([\s\S]*?)(\\end\{tabular\})"
)


class TableEditError(RuntimeError):
    pass


def find_table_spans(tex: str) -> list[tuple[int, int]]:
    """Return (start, end) spans for each ``table`` environment (document order)."""
    return [(m.start(), m.end()) for m in _TABLE_ENV.finditer(tex or "")]


def validate_table_payload(
    *,
    caption: str,
    headers: list[str],
    rows: list[list[str]],
) -> None:
    del caption  # caption may be empty
    if not headers:
        raise TableEditError("нужен хотя бы один столбец")
    if len(headers) > _MAX_COLS:
        raise TableEditError(f"слишком много столбцов (макс. {_MAX_COLS})")
    if len(rows) > _MAX_ROWS:
        raise TableEditError(f"слишком много строк (макс. {_MAX_ROWS})")
    n = len(headers)
    for i, row in enumerate(rows):
        if len(row) != n:
            raise TableEditError(
                f"строка {i + 1}: ожидалось {n} ячеек, получено {len(row)}"
            )


def _looks_numeric(s: str) -> bool:
    t = (s or "").strip().replace(" ", "").replace(",", ".")
    if not t:
        return False
    return bool(
        re.match(r"^-?\d+(\.\d+)?%?$", t)
        or re.match(r"^-?\d{1,3}([. ]\d{3})+(,\d+)?%?$", t)
    )


def _col_is_numeric(headers: list[str], rows: list[list[str]], ci: int) -> bool:
    n = 0
    total = 0
    for row in rows:
        if ci >= len(row):
            continue
        cell = row[ci]
        if cell is None or not str(cell).strip():
            continue
        total += 1
        if _looks_numeric(str(cell)):
            n += 1
    if total == 0:
        return False
    if n / total >= 0.6:
        return True
    h = (headers[ci] if ci < len(headers) else "").lower()
    return bool(
        re.search(r"\d|%|год|года|шт|руб|млн|тыс|доля|рост", h)
        and n / total >= 0.35
    )


def _cell_tex(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "~"
    return escape_tex_text(t)


def serialize_tabular_body(
    headers: list[str],
    rows: list[list[str]],
    *,
    use_tabularx: bool,
    width_arg: str = r"\textwidth",
) -> str:
    """Build begin…end tabular(x) with booktabs rules."""
    ncols = len(headers)
    specs: list[str] = []
    for ci in range(ncols):
        if use_tabularx:
            specs.append("X" if not _col_is_numeric(headers, rows, ci) else "r")
        else:
            specs.append("r" if _col_is_numeric(headers, rows, ci) else "l")
    # Prefer first col left for label-like headers when mixed
    if use_tabularx and specs and specs[0] == "r":
        specs[0] = "l"
    elif not use_tabularx and specs:
        specs[0] = "l"
    colspec = "".join(specs)
    lines: list[str] = []
    if use_tabularx:
        lines.append(rf"\begin{{tabularx}}{{{width_arg}}}{{{colspec}}}")
    else:
        lines.append(rf"\begin{{tabular}}{{{colspec}}}")
    lines.append(r"  \toprule")
    lines.append("  " + " & ".join(_cell_tex(h) for h in headers) + r" \\")
    lines.append(r"  \midrule")
    for row in rows:
        lines.append("  " + " & ".join(_cell_tex(c) for c in row) + r" \\")
    lines.append(r"  \bottomrule")
    if use_tabularx:
        lines.append(r"\end{tabularx}")
    else:
        lines.append(r"\end{tabular}")
    return "\n".join(lines)


def _replace_caption(block: str, caption: str) -> str:
    esc = escape_tex_text((caption or "").strip())
    if _CAPTION.search(block):
        return _CAPTION.sub(rf"\g<1>{esc}\g<3>", block, count=1)
    # insert caption after \centering if present, else after \begin{table}...
    m = re.search(r"(\\begin\{table\*?\}(?:\[[^\]]*\])?\s*)", block)
    if not m:
        return block
    insert = m.end()
    centering = re.match(r"\\centering\s*", block[insert:])
    if centering:
        insert += centering.end()
    return block[:insert] + rf"\caption{{{esc}}}" + "\n  " + block[insert:]


def _replace_tabular(block: str, headers: list[str], rows: list[list[str]]) -> str:
    mx = _TABULARX.search(block)
    if mx:
        # recover width from full match prefix: \begin{tabularx}{WIDTH}{
        full = mx.group(0)
        wm = re.match(r"\\begin\{tabularx\}\{([^}]+)\}", full)
        width_arg = wm.group(1) if wm else r"\textwidth"
        body = serialize_tabular_body(
            headers, rows, use_tabularx=True, width_arg=width_arg
        )
        return block[: mx.start()] + body + block[mx.end() :]
    mt = _TABULAR.search(block)
    if mt:
        body = serialize_tabular_body(headers, rows, use_tabularx=False)
        return block[: mt.start()] + body + block[mt.end() :]
    raise TableEditError("в таблице нет tabular/tabularx")


def patch_table_in_tex(
    tex: str,
    table_index: int,
    *,
    caption: str,
    headers: list[str],
    rows: list[list[str]],
) -> str:
    """Replace the ``table_index``-th (1-based) table env caption + body."""
    validate_table_payload(caption=caption, headers=headers, rows=rows)
    spans = find_table_spans(tex)
    if table_index < 1 or table_index > len(spans):
        raise TableEditError(f"таблица {table_index} не найдена (всего {len(spans)})")
    start, end = spans[table_index - 1]
    block = tex[start:end]
    block = _replace_caption(block, caption)
    block = _replace_tabular(block, headers, rows)
    return tex[:start] + block + tex[end:]


def edit_table_in_run(
    out_dir: Path,
    table_index: int,
    *,
    caption: str,
    headers: list[str],
    rows: list[list[str]],
    formats: set[str] | None = None,
) -> dict[str, Any]:
    """Patch TeX table and rebuild PDF/DOCX."""
    out_dir = out_dir.resolve()
    validate_table_payload(caption=caption, headers=headers, rows=rows)

    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        raise TableEditError("no .tex in run")
    from case3.run_undo import capture_before_edit

    capture_before_edit(out_dir, kind="table", target=str(table_index))
    tex_path = texs[0]
    tex_bak = tex_path.read_text(encoding="utf-8")

    meta_path = out_dir / "meta.json"
    meta_bak = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else None

    try:
        patched = patch_table_in_tex(
            tex_bak,
            table_index,
            caption=caption,
            headers=headers,
            rows=rows,
        )
        tex_path.write_text(patched, encoding="utf-8")
    except TableEditError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TableEditError(f"patch failed: {exc}") from exc

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta["last_table_edit"] = {
        "index": table_index,
        "caption": (caption or "")[:300],
        "cols": len(headers),
        "rows": len(rows),
        "ts": int(time.time()),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        artifacts = rebuild_run_docs(out_dir, formats=formats)
    except FileNotFoundError as exc:
        raise TableEditError(str(exc)) from exc
    except RenderError as exc:
        tex_path.write_text(tex_bak, encoding="utf-8")
        if meta_bak is not None:
            meta_path.write_text(meta_bak, encoding="utf-8")
        from case3.run_undo import clear_undo

        clear_undo(out_dir)
        raise TableEditError(f"document rebuild failed: {exc}") from exc

    v = int(time.time())
    from case3.run_undo import undo_meta

    return {
        "table_index": table_index,
        "caption": caption,
        "headers": headers,
        "rows": rows,
        "artifacts": {k: str(p) for k, p in artifacts.items()},
        "version": v,
        "media_status": meta.get("media_status") or {},
        "undo": undo_meta(out_dir),
    }
