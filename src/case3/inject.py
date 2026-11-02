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
# LLM sometimes writes \includegraphics{fig_02.png} instead of a CASE3 slot.
_MEDIA_INCLUDEGRAPHICS = re.compile(
    r"\\includegraphics(\[[^\]]*\])?\{(?:figures/)?((?:fig|cht|usr)_[a-z0-9_]+)\.png\}",
    re.I,
)


def rewrite_media_includegraphics_paths(tex: str, *, rel_dir: str = "figures") -> str:
    """Force media PNG paths under ``rel_dir/`` (bare fig_02.png → figures/fig_02.png)."""

    def _repl(m: re.Match[str]) -> str:
        opts = m.group(1) or ""
        mid = m.group(2)
        return f"\\includegraphics{opts}{{{rel_dir}/{mid}.png}}"

    return _MEDIA_INCLUDEGRAPHICS.sub(_repl, tex or "")


def strip_failed_media_includes(tex: str, status: dict[str, Any]) -> str:
    """Remove \\includegraphics for media ids marked not ok in status."""
    failed = {
        mid
        for mid, st in (status or {}).items()
        if isinstance(st, dict) and not st.get("ok")
    }
    if not failed or not tex:
        return tex or ""

    def _repl(m: re.Match[str]) -> str:
        mid = m.group(2)
        if mid in failed:
            return ""
        return m.group(0)

    return _MEDIA_INCLUDEGRAPHICS.sub(_repl, tex)


def _drop_hollow_figures(tex: str) -> str:
    """Remove figure envs that no longer contain includegraphics / TikZ / tables."""

    def _drop(m: re.Match[str]) -> str:
        body = m.group(0)
        if r"\includegraphics" in body:
            return body
        if re.search(
            r"\\begin\{(?:tikzpicture|tabularx|tabular|minipage)\}", body
        ):
            return body
        return ""

    return _EMPTY_FIGURE_LOOSE.sub(_drop, tex or "")


def strip_missing_media_includes(tex: str, work_dir: Path) -> str:
    """Remove media \\includegraphics whose PNG is absent under ``work_dir``.

    Soft safety net before latexmk (avoids graphics Division-by-0).
    """
    root = Path(work_dir)
    if not tex:
        return tex or ""

    def _repl(m: re.Match[str]) -> str:
        mid = m.group(2)
        # Match rewritten form figures/<id>.png or bare (rewrite should run first).
        for cand in (root / "figures" / f"{mid}.png", root / f"{mid}.png"):
            if cand.is_file():
                return m.group(0)
        return ""

    out = _MEDIA_INCLUDEGRAPHICS.sub(_repl, tex)
    return _drop_hollow_figures(out)


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


def _enclosing_figure_span(tex: str, start: int) -> tuple[int, int] | None:
    """Return [begin, end_after) of the figure env containing ``start``, if any."""
    begin = tex.rfind(r"\begin{figure}", 0, start)
    end_before = tex.rfind(r"\end{figure}", 0, start)
    if begin == -1 or begin < end_before:
        return None
    end = tex.find(r"\end{figure}", start)
    if end == -1:
        return None
    return begin, end + len(r"\end{figure}")


def _slot_inside_figure(tex: str, start: int) -> bool:
    """True if match start sits between \\begin{figure} and \\end{figure}."""
    return _enclosing_figure_span(tex, start) is not None


def _inner_slot_replacement(
    tex: str,
    start: int,
    fid: str,
    meta: dict[str, Any],
    *,
    rel_dir: str,
    label_prefix: str,
) -> str:
    """Inside an existing figure: image + caption/label if the shell has none."""
    body = _includegraphics_line(fid, meta, rel_dir=rel_dir)
    span = _enclosing_figure_span(tex, start)
    if span is None:
        return body
    shell = tex[span[0] : span[1]]
    if r"\caption" in shell:
        return body
    caption = escape_tex_text(str(meta.get("caption") or fid))
    return (
        body
        + f"  \\caption{{{caption}}}\n"
        + f"  \\label{{{label_prefix}:{fid}}}\n"
    )


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
            return _inner_slot_replacement(
                tex, m.start(), fid, meta, rel_dir=rel_dir, label_prefix="fig"
            )
        return _figure_env(fid, meta, rel_dir=rel_dir, label_prefix="fig")

    out = _FIG_SLOT.sub(repl_fig, tex)

    def repl_chart(m: re.Match[str]) -> str:
        cid = m.group(1)
        st = status.get(cid) or {}
        meta = by_chart.get(cid)
        if not st.get("ok") or not meta:
            return ""
        # Positions are relative to `out` (post-figure inject), not original `tex`.
        if _slot_inside_figure(out, m.start()):
            return _inner_slot_replacement(
                out, m.start(), cid, meta, rel_dir=rel_dir, label_prefix="chart"
            )
        return _figure_env(cid, meta, rel_dir=rel_dir, label_prefix="chart")

    out = _CHART_SLOT.sub(repl_chart, out)
    out = strip_orphan_slots(out)
    out = rewrite_media_includegraphics_paths(out, rel_dir=rel_dir)
    out = strip_failed_media_includes(out, status)
    out = _drop_hollow_figures(out)
    out = ensure_document_preamble(out)
    return out


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
