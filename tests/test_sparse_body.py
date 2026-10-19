"""Sparse (charts-only) TeX must be filled with Source prose."""

from __future__ import annotations

from case3.generate import fill_sparse_tex_with_source, tex_body_is_sparse


def test_sparse_detection() -> None:
    sparse = r"""\documentclass{article}
\begin{document}
\maketitle
%CASE3_CHART:cht_01%
\end{document}
"""
    assert tex_body_is_sparse(sparse)
    rich = sparse.replace(
        "%CASE3_CHART:cht_01%",
        r"\section{Введение} Население республики составило девять миллионов человек.",
    )
    assert not tex_body_is_sparse(rich)


def test_fill_inserts_source_and_keeps_slots() -> None:
    sparse = r"""\documentclass{article}
\begin{document}
\maketitle
%CASE3_CHART:cht_01%
%CASE3_CHART:cht_02%
\end{document}
"""
    source = "Население 2019: 9470 тыс.\nРождаемость 9.0."
    out = fill_sparse_tex_with_source(
        sparse,
        source,
        chart_ids=["cht_01", "cht_02"],
        figure_ids=[],
    )
    assert r"\section{Исходные данные}" in out or "Население" in out
    assert "%CASE3_CHART:cht_01%" in out
    assert "%CASE3_CHART:cht_02%" in out
    assert r"\end{document}" in out
    assert not tex_body_is_sparse(out)
