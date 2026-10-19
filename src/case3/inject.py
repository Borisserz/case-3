"""Replace %CASE3_FIG / %CASE3_CHART slots with figure envs or strip them."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from case3.tex_preamble import ensure_document_preamble, strip_orphan_slots
from case3.tex_safe import escape_tex_text, sanitize_width

_FIG_SLOT = re.compile(r"(?m)^[ \t]*%CASE3_FIG:([a-z][a-z0-9_]{0,31})%[ \t]*\r?\n?")
_CHART_SLOT = re.compile(r"(?m)^[ \t]*%CASE3_CHART:([a-z][a-z0-9_]{0,31})%[ \t]*\r?\n?")
# Model sometimes wraps a slot in figure; after a failed chart we must drop the shell.
_EMPTY_FIGURE = re.compile(
    r"\\begin\{figure\}(?:\[[^\]]*\])?\{?\}?\s*"
    r"(?:\\centering\s*)?"
    r"(?:\\caption\{[^}]*\}\s*)?"
    r"(?:\\label\{[^}]*\}\s*)?"
    r"\\end\{figure\}\s*",
    re.S,
)
_EMPTY_FIGURE_LOOSE = re.compile(
    r"\\begin\{figure\}.*?\\end\{figure\}",
    re.S,
)


def _includegraphics_line(fid: str, meta: dict[str, Any], *, rel_dir: str) -> str:
    width = sanitize_width(meta.get("width"))
    path = f"{rel_dir}/{fid}.png"
    return f"  \\includegraphics[width={width}]{{{path}}}\n"


def _figure_env(fid: str, meta: dict[str, Any], *, rel_dir: str, label_prefix: str) -> str:
    caption = escape_tex_text(str(meta.get("caption") or fid))
    return (
        "\\begin{figure}[H]\n"
        "  \\centering\n"
        + _includegraphics_line(fid, meta, rel_dir=rel_dir)
        + f"  \\caption{{{caption}}}\n"
        f"  \\label{{{label_prefix}:{fid}}}\n"
        "\\end{figure}\n"
    )


def _slot_inside_figure(tex: str, start: int) -> bool:
    """True if match start sits between \\begin{figure} and \\end{figure}."""
    begin = tex.rfind(r"\begin{figure}", 0, start)
    end = tex.rfind(r"\end{figure}", 0, start)
    return begin != -1 and begin > end


def inject_media(
    tex: str,
    figures: list[dict[str, Any]],
    charts: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    rel_dir: str = "figures",
) -> str:
    by_fig = {f["id"]: f for f in figures}
    by_chart = {c["id"]: c for c in charts}

    def repl_fig(m: re.Match[str]) -> str:
        fid = m.group(1)
        st = status.get(fid) or {}
        meta = by_fig.get(fid)
        if not st.get("ok") or not meta:
            return ""
        if _slot_inside_figure(tex, m.start()):
            return _includegraphics_line(fid, meta, rel_dir=rel_dir)
        return _figure_env(fid, meta, rel_dir=rel_dir, label_prefix="fig")

    def repl_chart(m: re.Match[str]) -> str:
        cid = m.group(1)
        st = status.get(cid) or {}
        meta = by_chart.get(cid)
        if not st.get("ok") or not meta:
            return ""
        if _slot_inside_figure(tex, m.start()):
            return _includegraphics_line(cid, meta, rel_dir=rel_dir)
        return _figure_env(cid, meta, rel_dir=rel_dir, label_prefix="chart")

    out = _FIG_SLOT.sub(repl_fig, tex)
    out = _CHART_SLOT.sub(repl_chart, out)
    out = strip_orphan_slots(out)
    # Drop figure envs that no longer contain \includegraphics (failed/stripped slot)
    def _drop_empty_fig(m: re.Match[str]) -> str:
        body = m.group(0)
        return body if r"\includegraphics" in body else ""

    out = _EMPTY_FIGURE_LOOSE.sub(_drop_empty_fig, out)
    out = ensure_document_preamble(out)
    return out


def inject_figures(
    tex: str,
    figures: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    rel_dir: str = "figures",
) -> str:
    """Backward-compatible: figures only."""
    return inject_media(tex, figures, [], status, rel_dir=rel_dir)


def write_injected(
    tex_path: Path,
    figures: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    charts: list[dict[str, Any]] | None = None,
) -> Path:
    raw = tex_path.read_text(encoding="utf-8")
    new = inject_media(raw, figures, charts or [], status)
    tex_path.write_text(new, encoding="utf-8")
    return tex_path
