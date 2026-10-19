"""Wide tabular → tabularx rewriting."""

from __future__ import annotations

from case3.tex_preamble import (
    ensure_font_aliases,
    harden_tabularx_colcount,
    harden_wide_tables,
)


def test_three_l_columns_become_tabularx() -> None:
    src = r"""
\begin{table}[H]
\begin{tabular}{l l l}
\toprule
A & B & C \\
\bottomrule
\end{tabular}
\end{table}
"""
    out = harden_wide_tables(src)
    assert r"\begin{tabularx}{\textwidth}{lXX}" in out.replace(" ", "")
    assert r"\end{tabularx}" in out
    assert r"\begin{tabular}{l l l}" not in out


def test_two_column_tabular_unchanged() -> None:
    src = r"\begin{tabular}{lr} a & 1 \\ \end{tabular}"
    assert harden_wide_tables(src) == src


def test_already_p_column_unchanged() -> None:
    src = r"\begin{tabular}{lp{0.4\textwidth}r} a & b & c \\ \end{tabular}"
    assert harden_wide_tables(src) == src


def test_tabularx_already_ok() -> None:
    src = r"\begin{tabularx}{\textwidth}{lXX} a & b & c \\ \end{tabularx}"
    assert harden_wide_tables(src) == src


def test_tabularx_colcount_mismatch_fixed() -> None:
    src = (
        r"\begin{tabularx}{\textwidth}{lrrrr}"
        r"\toprule Показатель & 2019 & 2020 & 2021 & 2022 & 2023 \\"
        r"\midrule A & 1 & 2 & 3 & 4 & 5 \\"
        r"\bottomrule\end{tabularx}"
    )
    out = harden_tabularx_colcount(src)
    assert r"{lXXXXX}" in out.replace(" ", "")


def test_dejavu_mono_aliased() -> None:
    assert r"DejaVu Sans Mono" in ensure_font_aliases(
        r"\setmonofont{DejaVu Mono}"
    )
