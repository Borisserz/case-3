"""C4: wide tables → landscape wrap; normal tabularx stays portrait."""

from __future__ import annotations

from case3.tex_preamble import ensure_preamble, maybe_landscape_wide_tables, table_needs_landscape


def test_narrow_table_no_landscape() -> None:
    block = r"""
\begin{table}[ht]
\caption{KPI}
\begin{tabularx}{\textwidth}{lXr}
Метрика & Q2 & Q3 \\
Выручка & 1 & 2 \\
\end{tabularx}
\end{table}
"""
    assert table_needs_landscape(block) is False
    out = maybe_landscape_wide_tables(block)
    assert r"\begin{landscape}" not in out


def test_wide_many_cols_needs_landscape() -> None:
    cols = " & ".join(f"C{i}" for i in range(8))
    spec = "l" + "X" * 7
    block = rf"""
\begin{{table}}[ht]
\caption{{Wide}}
\begin{{tabularx}}{{\textwidth}}{{{spec}}}
{cols} \\
\end{{tabularx}}
\end{{table}}
"""
    assert table_needs_landscape(block) is True
    out = maybe_landscape_wide_tables(block)
    assert r"\begin{landscape}" in out
    assert r"\end{landscape}" in out
    # idempotent
    out2 = maybe_landscape_wide_tables(out)
    assert out2.count(r"\begin{landscape}") == 1


def test_ensure_preamble_adds_pdflscape() -> None:
    tex = r"""\documentclass{article}
\begin{document}
Hi
\end{document}
"""
    out = ensure_preamble(tex)
    assert r"\usepackage{pdflscape}" in out
