"""Truncation detection + continuation merge + soft-close cleanup."""

from __future__ import annotations

from case3.generate import merge_continuation, output_looks_truncated
from case3.tex_utils import extract_tex


def test_truncated_when_no_end_document() -> None:
    raw = "```latex\n\\documentclass{article}\\begin{document}\nHi\n"
    assert output_looks_truncated(raw)


def test_truncated_slots_without_json() -> None:
    raw = "```latex\n\\documentclass{article}\\begin{document}\n%CASE3_CHART:cht_01%\n\\end{document}\n```\n"
    assert output_looks_truncated(raw)


def test_complete_dual_fence_not_truncated() -> None:
    raw = (
        "```json\n{\"figures\":[],\"charts\":[]}\n```\n"
        "```latex\n\\documentclass{article}\\begin{document}x\\end{document}\n```\n"
    )
    assert not output_looks_truncated(raw)


def test_merge_appends_json() -> None:
    partial = "```latex\n\\documentclass{article}\\begin{document}\nHi\n"
    cont = '```json\n{"figures":[],"charts":[]}\n```'
    merged = merge_continuation(partial, cont)
    assert "```json" in merged
    assert merged.count("```") >= 4 or "charts" in merged


def test_soft_close_drops_incomplete_table() -> None:
    raw = r"""```latex
\documentclass{article}
\begin{document}
\section{Ok}
Text.
\begin{table}[H]
\centering
\caption{Broken}
\begin{tabular}{lrr}
\toprule
Год & A & B \\
"""
    tex = extract_tex(raw)
    assert r"\end{document}" in tex
    assert r"\begin{table}" not in tex
    assert "Ok" in tex
