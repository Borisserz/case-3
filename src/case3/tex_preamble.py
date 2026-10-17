"""Ensure XeLaTeX documents have the packages case-3 actually needs."""

from __future__ import annotations

import re

# Order matches prompt/system_tex.md — inject after \\documentclass if missing.
REQUIRED_PACKAGES = (
    "fontspec",
    "polyglossia",
    "geometry",
    "booktabs",
    "longtable",
    "float",
    "graphicx",
    "hyperref",
)

# Match \documentclass[...]{name} even when the next token is on the same line.
_DOCCLASS = re.compile(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]+\})")


class TexStructureError(ValueError):
    """Document is missing required LaTeX structure."""


def assert_tex_structure(tex: str) -> None:
    if r"\documentclass" not in tex:
        raise TexStructureError("missing \\documentclass")
    if r"\begin{document}" not in tex:
        raise TexStructureError("missing \\begin{document}")
    if r"\end{document}" not in tex:
        raise TexStructureError("missing \\end{document}")


def ensure_document_preamble(tex: str) -> str:
    """Insert missing required packages right after \\documentclass (stable order)."""
    m = _DOCCLASS.search(tex)
    if not m:
        return tex
    missing = [p for p in REQUIRED_PACKAGES if rf"\usepackage{{{p}}}" not in tex]
    if not missing:
        return tex
    block = "".join(rf"\usepackage{{{p}}}" + "\n" for p in missing)
    insert_at = m.end()
    prefix = "\n" if insert_at < len(tex) and tex[insert_at] != "\n" else ""
    return tex[:insert_at] + prefix + block + tex[insert_at:]


def strip_orphan_slots(tex: str) -> str:
    """Remove any leftover CASE3 media slots (safety before latexmk)."""
    return re.sub(
        r"(?m)^[ \t]*%CASE3_(?:FIG|CHART):[a-z][a-z0-9_]{0,31}%[ \t]*\r?\n?",
        "",
        tex,
    )
