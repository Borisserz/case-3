"""Report typography preamble + branding scrub."""

from __future__ import annotations

from case3.tex_preamble import ensure_document_preamble, scrub_project_branding


def test_ensure_adds_fancyhdr_and_setspace() -> None:
    raw = r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\begin{document}
Hi
\end{document}
"""
    out = ensure_document_preamble(raw)
    assert r"\usepackage{fancyhdr}" in out
    assert r"\usepackage{setspace}" in out
    assert r"\usepackage{caption}" in out
    assert r"\usepackage{xcolor}" in out
    assert r"\pagestyle{fancy}" in out
    assert r"\setstretch{1.15}" in out
    assert r"margin=2.2cm" in out
    assert r"\setmainfont{DejaVu Serif}" in out
    assert r"\setdefaultlanguage{russian}" in out
    assert r"\setlength{\headheight}{15pt}" in out


def test_ensure_adds_xcolor_before_definecolor_ink() -> None:
    """LLM atelier ink without xcolor → latexmk exit 12."""
    raw = r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=ink,urlcolor=ink}
\definecolor{ink}{HTML}{2C3A14}
\begin{document}
\section{Выручка}
Ok
\end{document}
"""
    out = ensure_document_preamble(raw)
    assert r"\usepackage{xcolor}" in out
    xcolor_at = out.index(r"\usepackage{xcolor}")
    define_at = out.index(r"\definecolor{ink}")
    assert xcolor_at < define_at


def test_ensure_strips_color_from_titleformat() -> None:
    r"""\color{black} in titleformat without xcolor breaks \section."""
    raw = r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\usepackage{setspace}
\usepackage{titlesec}
\usepackage{fancyhdr}
\setstretch{1.15}
\titleformat{\section}
  {\large\bfseries\color{black}}
  {}{0pt}{}
\pagestyle{fancy}
\begin{document}
\section{Краткий вывод}
Текст
\end{document}
"""
    out = ensure_document_preamble(raw)
    assert r"\color{black}" not in out
    assert r"\titleformat{\section}{\large\bfseries\raggedright}" in out
    assert r"\setlength{\headheight}{15pt}" in out


def test_scrub_author_case3() -> None:
    raw = r"\title{Демография}\author{case-3}\date{\today}"
    out = scrub_project_branding(raw)
    assert r"\author{}" in out
    assert "case-3" not in out
    assert "case3" not in out.lower()


def test_scrub_title_with_case3() -> None:
    raw = r"\title{Отчёт case-3}\author{Иванов}"
    out = scrub_project_branding(raw)
    assert "case-3" not in out
    assert r"\author{Иванов}" in out
