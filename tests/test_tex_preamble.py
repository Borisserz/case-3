import pytest

from case3.tex_preamble import (
    TexStructureError,
    assert_tex_structure,
    ensure_document_preamble,
    strip_orphan_slots,
)


MINIMAL = r"""\documentclass[a4paper,12pt]{article}
\begin{document}
Hi
\end{document}
"""


def test_ensure_adds_float_and_graphicx():
    out = ensure_document_preamble(MINIMAL)
    assert r"\usepackage{float}" in out
    assert r"\usepackage{graphicx}" in out
    assert r"\usepackage{booktabs}" in out
    # packages after documentclass, stable order
    assert out.index(r"\documentclass") < out.index(r"\usepackage{float}")
    assert out.index(r"\usepackage{float}") < out.index(r"\usepackage{graphicx}")


def test_ensure_same_line_documentclass():
    raw = r"\documentclass{article}\begin{document}x\end{document}"
    out = ensure_document_preamble(raw)
    assert r"\usepackage{float}" in out
    assert r"\begin{document}" in out


def test_ensure_idempotent():
    once = ensure_document_preamble(MINIMAL)
    twice = ensure_document_preamble(once)
    assert once.count(r"\usepackage{float}") == 1
    assert twice == once


def test_strip_orphan_slots():
    tex = "A\n%CASE3_CHART:cht_01%\n%CASE3_FIG:fig_01%\nB\n"
    assert "%CASE3_" not in strip_orphan_slots(tex)
    assert "A" in strip_orphan_slots(tex) and "B" in strip_orphan_slots(tex)


def test_assert_structure():
    assert_tex_structure(MINIMAL)
    with pytest.raises(TexStructureError):
        assert_tex_structure(r"\documentclass{article}\begin{document}")
