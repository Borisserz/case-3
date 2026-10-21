"""PDF task 4: obvious bullet lines → itemize (outside existing envs)."""

from __future__ import annotations

from case3.tex_preamble import ensure_document_preamble
from case3.tex_prose import harden_prose_lists


def test_dash_bullets_become_itemize() -> None:
    body = (
        "Введение.\n"
        "- первый пункт\n"
        "- второй пункт\n"
        "Заключение.\n"
    )
    out = harden_prose_lists(body)
    assert r"\begin{itemize}" in out
    assert r"\item первый пункт" in out
    assert r"\item второй пункт" in out
    assert r"\end{itemize}" in out
    assert "Введение." in out
    assert "Заключение." in out


def test_bullet_char_and_idempotent() -> None:
    body = "• альфа\n• бета\n"
    once = harden_prose_lists(body)
    twice = harden_prose_lists(once)
    assert once == twice
    assert once.count(r"\begin{itemize}") == 1


def test_skips_inside_itemize_and_tabular() -> None:
    body = (
        r"\begin{itemize}" + "\n"
        r"\item уже список" + "\n"
        r"\end{itemize}" + "\n"
        r"\begin{tabular}{ll}" + "\n"
        "- не трогать & x \\\\\n"
        r"\end{tabular}" + "\n"
        "- снаружи да\n"
        "- и это\n"
    )
    out = harden_prose_lists(body)
    assert "- не трогать" in out
    assert r"\item снаружи да" in out
    assert out.count(r"\begin{itemize}") == 2  # original + new


def test_ensure_preamble_runs_prose_harden() -> None:
    tex = (
        r"\documentclass{article}"
        r"\usepackage{tabularx,booktabs,polyglossia,fontspec,enumitem}"
        r"\begin{document}"
        "Текст.\n- пункт A\n- пункт B\n"
        r"\end{document}"
    )
    out = ensure_document_preamble(tex)
    assert r"\item пункт A" in out
