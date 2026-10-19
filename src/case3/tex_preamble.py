"""Ensure XeLaTeX documents have the packages case-3 actually needs."""

from __future__ import annotations

import re

# Order matches prompt/system_tex.md — inject after \\documentclass if missing.
REQUIRED_PACKAGES = (
    "fontspec",
    "polyglossia",
    "geometry",
    "booktabs",
    "tabularx",
    "longtable",
    "float",
    "graphicx",
    "hyperref",
)

# Match \documentclass[...]{name} even when the next token is on the same line.
_DOCCLASS = re.compile(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]+\})")
_GEOMETRY = re.compile(r"\\geometry\{[^}]*\}")
_A4_GEOMETRY = r"\geometry{a4paper,margin=2.5cm}"

# Plain l/c/r tabulars with ≥3 columns overflow A4 — promote to tabularx.
_TABULAR_BLOCK = re.compile(
    r"\\begin\{tabular\}\{([^}]*)\}([\s\S]*?)\\end\{tabular\}",
    re.M,
)


class TexStructureError(ValueError):
    """Document is missing required LaTeX structure."""


def _simple_lcr_count(colspec: str) -> int | None:
    """Return # of l/c/r columns, or None if spec already uses p/X/etc."""
    spec = (colspec or "").strip()
    if not spec:
        return None
    if re.search(r"[pXmbsS\*]|@{|!{", spec):
        return None
    cols = re.findall(r"[lcr]", spec)
    return len(cols) if cols else None


def harden_wide_tables(tex: str) -> str:
    """Rewrite wide ``tabular{lll…}`` into ``tabularx{\\textwidth}{lXX…}``."""

    def _repl(m: re.Match[str]) -> str:
        spec, body = m.group(1), m.group(2)
        n = _simple_lcr_count(spec)
        if n is None or n < 3:
            return m.group(0)
        letters = re.findall(r"[lcr]", spec)
        new_spec = letters[0] + ("X" * (len(letters) - 1))
        return (
            rf"\begin{{tabularx}}{{\textwidth}}{{{new_spec}}}"
            + body
            + r"\end{tabularx}"
        )

    return _TABULAR_BLOCK.sub(_repl, tex)


def assert_tex_structure(tex: str) -> None:
    if r"\documentclass" not in tex:
        raise TexStructureError("missing \\documentclass")
    if r"\begin{document}" not in tex:
        raise TexStructureError("missing \\begin{document}")
    if r"\end{document}" not in tex:
        raise TexStructureError("missing \\end{document}")


def _ensure_a4_documentclass(tex: str) -> str:
    """Force a4paper into \\documentclass options (default page size)."""

    def _fix(m: re.Match[str]) -> str:
        opts = (m.group(1) or "").strip()
        name = m.group(2)
        parts = [p.strip() for p in opts.split(",") if p.strip()] if opts else []
        parts = [
            p
            for p in parts
            if p.lower()
            not in {
                "a4paper",
                "a5paper",
                "letterpaper",
                "legalpaper",
                "executivepaper",
                "b5paper",
                "landscape",
            }
        ]
        parts.insert(0, "a4paper")
        if not any(re.fullmatch(r"\d+pt", p) for p in parts):
            parts.append("12pt")
        return rf"\documentclass[{','.join(parts)}]{{{name}}}"

    return re.sub(
        r"\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}",
        _fix,
        tex,
        count=1,
    )


def ensure_a4_layout(tex: str) -> str:
    """Pin page to A4 portrait with 2.5 cm margins."""
    out = _ensure_a4_documentclass(tex)
    if _GEOMETRY.search(out):
        # callable repl — avoid re.sub treating \g in \geometry as a group
        return _GEOMETRY.sub(lambda _m: _A4_GEOMETRY, out, count=1)
    if r"\usepackage{geometry}" in out:
        return out.replace(
            r"\usepackage{geometry}",
            r"\usepackage{geometry}" + "\n" + _A4_GEOMETRY,
            1,
        )
    return out


def ensure_document_preamble(tex: str) -> str:
    """Insert missing required packages + force A4 geometry + widen-safe tables."""
    m = _DOCCLASS.search(tex)
    if not m:
        return harden_wide_tables(ensure_a4_layout(tex))
    missing = [p for p in REQUIRED_PACKAGES if rf"\usepackage{{{p}}}" not in tex]
    out = tex
    if missing:
        block = "".join(rf"\usepackage{{{p}}}" + "\n" for p in missing)
        insert_at = m.end()
        # Always break after \documentclass so packages are not glued on the same line.
        out = out[:insert_at] + "\n" + block + out[insert_at:].lstrip("\n")
    return harden_wide_tables(ensure_a4_layout(out))


def strip_orphan_slots(tex: str) -> str:
    """Remove any leftover CASE3 media slots (safety before latexmk)."""
    return re.sub(
        r"(?m)^[ \t]*%CASE3_(?:FIG|CHART):[a-z][a-z0-9_]{0,31}%[ \t]*\r?\n?",
        "",
        tex,
    )
