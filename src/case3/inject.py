"""Replace %CASE3_FIG:<id>% slots with figure envs or strip them."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from case3.tex_safe import escape_tex_text, sanitize_width

_SLOT = re.compile(r"(?m)^[ \t]*%CASE3_FIG:([a-z][a-z0-9_]{0,31})%[ \t]*\r?\n?")


def _ensure_graphicx(tex: str) -> str:
    if r"\usepackage{graphicx}" in tex:
        return tex
    return re.sub(
        r"(\\documentclass[^\n]*\n)",
        r"\1\\usepackage{graphicx}\n",
        tex,
        count=1,
    )


def inject_figures(
    tex: str,
    figures: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    rel_dir: str = "figures",
) -> str:
    by_id = {f["id"]: f for f in figures}

    def repl(m: re.Match[str]) -> str:
        fid = m.group(1)
        st = status.get(fid) or {}
        meta = by_id.get(fid)
        if not st.get("ok") or not meta:
            return ""
        width = sanitize_width(meta.get("width"))
        caption = escape_tex_text(str(meta.get("caption") or fid))
        path = f"{rel_dir}/{fid}.png"
        return (
            "\\begin{figure}[H]\n"
            "  \\centering\n"
            f"  \\includegraphics[width={width}]{{{path}}}\n"
            f"  \\caption{{{caption}}}\n"
            f"  \\label{{fig:{fid}}}\n"
            "\\end{figure}\n"
        )

    out = _SLOT.sub(repl, tex)
    if any(status.get(f["id"], {}).get("ok") for f in figures):
        out = _ensure_graphicx(out)
    out = _SLOT.sub("", out)
    return out


def write_injected(tex_path: Path, figures: list[dict[str, Any]], status: dict[str, Any]) -> Path:
    raw = tex_path.read_text(encoding="utf-8")
    new = inject_figures(raw, figures, status)
    tex_path.write_text(new, encoding="utf-8")
    return tex_path
