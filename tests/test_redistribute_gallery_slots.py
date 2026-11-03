"""Trailing \\section{Визуализация}/Иллюстрации dumps must be scattered into prose."""

from case3.tex_media_place import redistribute_gallery_slots


def test_081536_signature_slots_leave_gallery() -> None:
    tex = r"""\documentclass{article}
\begin{document}
\section{Введение и контекст}
Текст про экономику и рынок ИИ в Беларуси.

\section{Секторальный анализ внедрения}
\subsection{Промышленность и ЗПК}
Заводы и цифровые двойники.

\subsection{Сельское хозяйство}
Дроны и посевы.

\section{Визуализация данных}
\subsection{Динамика рынка ИИ}
%CASE3_CHART:cht_01%
\subsection{Бюджет по секторам}
%CASE3_CHART:cht_02%
\section{Иллюстрации}
\subsection{Роботизированный цех}
%CASE3_FIG:fig_02%
\subsection{Дроны в поле}
%CASE3_FIG:fig_03%
\end{document}
"""
    charts = [
        {"id": "cht_01", "caption": "Динамика рынка ИИ в РБ (2020–2030)"},
        {"id": "cht_02", "caption": "Распределение бюджета на ИИ по секторам"},
    ]
    figures = [
        {"id": "fig_02", "caption": "Роботизированный цех промышленности"},
        {"id": "fig_03", "caption": "Умное сельское хозяйство с дронами"},
    ]
    out = redistribute_gallery_slots(tex, figures=figures, charts=charts)
    assert r"\section{Визуализация" not in out
    assert r"\section{Иллюстрации}" not in out
    # slots survive
    assert "%CASE3_CHART:cht_01%" in out
    assert "%CASE3_FIG:fig_02%" in out
    # charts/figs appear before former gallery — inside earlier sections
    viz_gone_body = out.split(r"\begin{document}", 1)[-1]
    assert viz_gone_body.index("%CASE3_CHART:cht_01%") < viz_gone_body.index(
        r"\section{Секторальный"
    ) or "%CASE3_CHART:cht_01%" in out.split(r"\section{Введение", 1)[-1].split(
        r"\section{Секторальный", 1
    )[0]
    # factory fig near industry, drone near agriculture
    ind = out.split(r"\subsection{Промышленность", 1)[-1]
    assert "%CASE3_FIG:fig_02%" in ind.split(r"\subsection{", 1)[0]
    ag = out.split(r"\subsection{Сельское", 1)[-1]
    assert "%CASE3_FIG:fig_03%" in ag.split(r"\subsection{", 1)[0]


def test_no_gallery_untouched() -> None:
    tex = r"""\documentclass{article}
\begin{document}
\section{A}
Текст.
%CASE3_CHART:cht_01%
\section{B}
Ещё текст.
\end{document}
"""
    out = redistribute_gallery_slots(
        tex,
        figures=[],
        charts=[{"id": "cht_01", "caption": "X"}],
    )
    assert out == tex
