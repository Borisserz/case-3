"""Ensure XeLaTeX documents have the packages and report style we need."""

from __future__ import annotations

import re

# Order matches prompt/system_tex.md — inject after \\documentclass if missing.
# hyperref stays last among these; style packages before it.
REQUIRED_PACKAGES = (
    "fontspec",
    "polyglossia",
    "geometry",
    "booktabs",
    "tabularx",
    "longtable",
    "float",
    "graphicx",
    "setspace",
    "microtype",
    "titlesec",
    "fancyhdr",
    "caption",
    "hyperref",
)

# Match \documentclass[...]{name} even when the next token is on the same line.
_DOCCLASS = re.compile(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]+\})")
_GEOMETRY = re.compile(r"\\geometry\{[^}]*\}")
_A4_GEOMETRY = r"\geometry{a4paper,margin=2.2cm}"
_BEGIN_DOC = re.compile(r"\\begin\{document\}")

# Plain l/c/r tabulars with ≥3 columns overflow A4 — promote to tabularx.
_TABULAR_BLOCK = re.compile(
    r"\\begin\{tabular\}\{([^}]*)\}([\s\S]*?)\\end\{tabular\}",
    re.M,
)

_BRAND = re.compile(r"case[\s\-]?3", re.I)

# Injected once before \begin{document} if fancyhdr style missing.
REPORT_STYLE_BLOCK = r"""
% --- report style: typography + running header ---
\setstretch{1.15}
\captionsetup{font=small,labelfont=bf,skip=6pt,justification=centering}
\titleformat{\section}{\large\bfseries\raggedright}{\thesection.}{0.6em}{}
\titleformat{\subsection}{\normalsize\bfseries\raggedright}{\thesubsection.}{0.5em}{}
\titlespacing*{\section}{0pt}{1.35ex plus .2ex}{0.75ex plus .1ex}
\titlespacing*{\subsection}{0pt}{1.05ex plus .15ex}{0.45ex plus .05ex}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\itshape\leftmark}
\fancyhead[R]{\footnotesize\thepage}
\renewcommand{\headrulewidth}{0.35pt}
\renewcommand{\footrulewidth}{0pt}
\fancypagestyle{plain}{%
  \fancyhf{}%
  \fancyhead[R]{\footnotesize\thepage}%
  \renewcommand{\headrulewidth}{0pt}%
}
"""


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


_TABULARX_BLOCK = re.compile(
    r"\\begin\{tabularx\}\{\\textwidth\}\{([^}]*)\}([\s\S]*?)\\end\{tabularx\}",
    re.M,
)


def harden_wide_tables(tex: str) -> str:
    """Rewrite wide ``tabular{lll…}`` into ``tabularx{\\textwidth}{lXX…}``."""

    def _repl(m: re.Match[str]) -> str:
        spec, body = m.group(1), m.group(2)
        # Nested tabular: non-greedy match would break the outer env — skip.
        if r"\begin{tabular}" in body or r"\begin{tabularx}" in body:
            return m.group(0)
        n = _simple_lcr_count(spec)
        if n is None or n < 3:
            return m.group(0)
        # Only plain l/c/r (no | @{} etc.) — preserve ruled specs.
        if not re.fullmatch(r"[lcr\s]+", (spec or "").strip()):
            return m.group(0)
        letters = re.findall(r"[lcr]", spec)
        new_spec = letters[0] + ("X" * (len(letters) - 1))
        return (
            rf"\begin{{tabularx}}{{\textwidth}}{{{new_spec}}}"
            + body
            + r"\end{tabularx}"
        )

    return _TABULAR_BLOCK.sub(_repl, tex)


def harden_tabularx_colcount(tex: str) -> str:
    """Fix ``tabularx{…}{lrrrr}`` when the header has more ``&`` than columns."""

    def _repl(m: re.Match[str]) -> str:
        spec, body = m.group(1), m.group(2)
        if r"\begin{tabular" in body:
            return m.group(0)
        # Split on \\ row terminators (body may be one long line).
        ncol_body = 0
        chunks = re.split(r"\\\\", body)
        for chunk in chunks:
            s = chunk.strip()
            if not s or "&" not in s:
                continue
            s = re.sub(
                r"^\\(?:toprule|midrule|bottomrule|hline)\s*",
                "",
                s,
            )
            s = re.sub(
                r"\\(?:toprule|midrule|bottomrule|hline)\s*",
                " ",
                s,
            ).strip()
            if "&" not in s:
                continue
            ncol_body = s.count("&") + 1
            break
        if ncol_body < 2:
            return m.group(0)
        letters = re.findall(r"[lcrX]", spec)
        if len(letters) == ncol_body:
            return m.group(0)
        # rebuild: first col l, rest X (safe for A4)
        new_spec = "l" + ("X" * (ncol_body - 1))
        return (
            rf"\begin{{tabularx}}{{\textwidth}}{{{new_spec}}}"
            + body
            + r"\end{tabularx}"
        )

    return _TABULARX_BLOCK.sub(_repl, tex)


def ensure_font_aliases(tex: str) -> str:
    """Model often emits font names missing in the Docker image."""
    repls = (
        (r"\setmonofont{DejaVu Mono}", r"\setmonofont{DejaVu Sans Mono}"),
        (r"\setmainfont{Times New Roman}", r"\setmainfont{DejaVu Serif}"),
        (r"\setsansfont{Arial}", r"\setsansfont{DejaVu Sans}"),
    )
    out = tex
    for a, b in repls:
        out = out.replace(a, b)
    return out


def scrub_project_branding(tex: str) -> str:
    """Remove project codename from title/author (must not appear in PDF)."""

    def _author(m: re.Match[str]) -> str:
        return r"\author{}" if _BRAND.search(m.group(1) or "") else m.group(0)

    def _title(m: re.Match[str]) -> str:
        body = m.group(1) or ""
        if not _BRAND.search(body):
            return m.group(0)
        cleaned = _BRAND.sub("", body)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -:|")
        return r"\title{" + (cleaned or "Отчёт") + "}"

    out = re.sub(r"\\author\{([^{}]*)\}", _author, tex)
    out = re.sub(r"\\title\{([^{}]*)\}", _title, out)
    return out


_CYRILLIC_FONTS = r"""
\setdefaultlanguage{russian}
\setotherlanguage{english}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
""".strip()


def ensure_cyrillic_fonts(tex: str) -> str:
    """XeLaTeX without \\setmainfont falls back to Latin Modern → blank Cyrillic."""
    if r"\setmainfont{" in (tex or ""):
        return tex
    m = _BEGIN_DOC.search(tex or "")
    if not m:
        return tex
    # Prefer right after polyglossia / fontspec if present.
    insert_at = m.start()
    for anchor in (
        r"\usepackage{polyglossia}",
        r"\usepackage{fontspec}",
        r"\documentclass",
    ):
        idx = tex.find(anchor)
        if idx >= 0:
            # after end of that line
            nl = tex.find("\n", idx)
            insert_at = (nl + 1) if nl >= 0 else idx + len(anchor)
            break
    block = _CYRILLIC_FONTS + "\n"
    return tex[:insert_at] + block + tex[insert_at:]


def ensure_report_style(tex: str) -> str:
    """Add typography + fancyhdr block once before \\begin{document}."""
    if r"\pagestyle{fancy}" in tex and r"\setstretch{" in tex:
        return tex
    m = _BEGIN_DOC.search(tex)
    if not m:
        return tex
    block = REPORT_STYLE_BLOCK.strip() + "\n\n"
    return tex[: m.start()] + block + tex[m.start() :]


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
    """Pin page to A4 portrait with comfortable margins."""
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


def preamble_looks_broken(tex: str) -> bool:
    """True if preamble is truncated / unbalanced (unsafe for latexmk)."""
    t = tex or ""
    m = _BEGIN_DOC.search(t)
    head = t[: m.start()] if m else t
    if not head.strip():
        return True
    if head.count("{") != head.count("}"):
        return True
    last = head.rstrip().rsplit("\n", 1)[-1].strip()
    if re.search(r"\\[a-zA-Z]+$", last):
        return True
    # Truncated \usepackage{geom  or \setotherlanguage{engl
    if re.search(r"\\(?:usepackage|set(?:main|sans|mono)font|set(?:default|other)language|geometry)\{[^}]*$", head):
        return True
    if re.search(r"\\usepackage\{[a-zA-Z]*$", head, re.M):
        return True
    return False


def _replace_preamble(tex: str, new_preamble: str) -> str:
    m = _BEGIN_DOC.search(tex or "")
    if not m:
        return new_preamble.rstrip() + "\n"
    body = tex[m.start() :]
    return new_preamble.rstrip() + "\n" + body.lstrip()


def ensure_document_preamble(tex: str) -> str:
    """Packages + Cyrillic fonts + A4 + report style + branding scrub + tables."""
    from case3.tex_utils import _MIN_PREAMBLE

    out = scrub_project_branding(tex)
    if preamble_looks_broken(out):
        out = _replace_preamble(out, _MIN_PREAMBLE)
    m = _DOCCLASS.search(out)
    if m:
        missing = [p for p in REQUIRED_PACKAGES if rf"\usepackage{{{p}}}" not in out]
        if missing:
            block = "".join(rf"\usepackage{{{p}}}" + "\n" for p in missing)
            insert_at = m.end()
            out = out[:insert_at] + "\n" + block + out[insert_at:].lstrip("\n")
    out = ensure_cyrillic_fonts(out)
    out = ensure_font_aliases(out)
    out = ensure_a4_layout(out)
    out = ensure_report_style(out)
    out = harden_wide_tables(out)
    return harden_tabularx_colcount(out)


def strip_orphan_slots(tex: str) -> str:
    """Remove any leftover CASE3 media slots (safety before latexmk)."""
    return re.sub(
        r"(?m)^[ \t]*%CASE3_(?:FIG|CHART):[a-z][a-z0-9_]{0,31}%[ \t]*\r?\n?",
        "",
        tex,
    )
