"""User-chosen document title must win over model \\title."""

from __future__ import annotations

from case3.api import build_intent_from_ui
from case3.generate import apply_doc_title, doc_title_from_intent


def test_intent_includes_forced_title() -> None:
    intent = build_intent_from_ui(
        chat="Сделай отчёт",
        chart_types=[],
        max_charts=0,
        max_images=0,
        forbid_charts=True,
        forbid_images=True,
        doc_title="Демография 2019–2023",
    )
    assert "Демография 2019–2023" in intent
    assert doc_title_from_intent(intent) == "Демография 2019–2023"


def test_apply_doc_title_rewrites_title() -> None:
    tex = r"""\documentclass{article}
\title{Старое}
\author{}
\begin{document}
\maketitle
Hi
\end{document}
"""
    out = apply_doc_title(tex, "Новый отчёт & co")
    assert r"\title{Новый отчёт \& co}" in out
    assert "Старое" not in out
