"""Shared PDF/DOCX rebuild after Liber in-run edits."""

from __future__ import annotations

from pathlib import Path

from case3.paths import repo_root
from case3.render import render_tex


def rebuild_run_docs(
    out_dir: Path,
    *,
    formats: set[str] | None = None,
) -> dict[str, Path]:
    """Force-render TeX in ``out_dir`` for the requested print formats.

    ``formats`` empty → no artifacts (preview-only / formats=none).
    Raises ``RenderError`` from ``render_tex``; ``FileNotFoundError`` if no .tex.
    """
    out_dir = out_dir.resolve()
    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        raise FileNotFoundError("no .tex in run")
    fmt = formats if formats is not None else {"pdf", "docx"}
    figs_dir = out_dir / "figures"
    return render_tex(
        texs[0],
        out_dir=out_dir,
        formats=fmt,
        extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
        log_dir=out_dir / "logs",
        force=True,
        project_root=repo_root(),
    )
