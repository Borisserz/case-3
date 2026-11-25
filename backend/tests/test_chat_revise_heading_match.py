"""Section edits must find a heading through Russian case, not only the dictionary form."""

from case3.chat_revise import _paragraphs_under

_TEX = r"""
\documentclass{article}
\begin{document}
\section{Введение}
Первый абзац введения про платежи района.
Второй абзац про факт и план.
\section{Итоговые показатели}
Сводные итоги по всем платежам.
\section{Выполнение плана}
План исполнен.
\end{document}
"""


def test_genitive_and_prepositional_find_the_intro():
    exact = _paragraphs_under(_TEX, "Введение")
    assert exact
    assert _paragraphs_under(_TEX, "Введения") == exact
    assert _paragraphs_under(_TEX, "введении") == exact


def test_other_inflected_heading_stays_unique():
    plan = _paragraphs_under(_TEX, "плана")
    assert plan
    assert plan != _paragraphs_under(_TEX, "Введение")
    assert _paragraphs_under(_TEX, "показателей") == _paragraphs_under(
        _TEX, "Итоговые показатели"
    )


def test_missing_and_ambiguous_names_stay_unmatched():
    assert _paragraphs_under(_TEX, "Заключение") is None
    doubled = _TEX.replace(
        r"\section{Итоговые показатели}",
        r"\section{Введение в платежи}",
        1,
    )
    assert _paragraphs_under(doubled, "Введения") is None
    assert _paragraphs_under(_TEX, "Введения") != _paragraphs_under(
        _TEX, "Итоговые показатели"
    )
