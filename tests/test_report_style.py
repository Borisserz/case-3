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
    assert r"\pagestyle{fancy}" in out
    assert r"\setstretch{1.15}" in out
    assert r"margin=2.2cm" in out


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
