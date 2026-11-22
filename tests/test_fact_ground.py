"""A new report may repeat Source and the user's own number. Not a memory number."""

from pathlib import Path

from case3.fact_ground import fact_number_tokens, ground_generated
from case3.generate import generate_document

_TEX = r"""
\documentclass[a4paper,12pt]{article}
\begin{document}
\section{Касса}
Выручка 77. В источнике 20. Новых точек 15.
\includegraphics[width=0.85\textwidth]{figures/cht_01.png}
\end{document}
"""


def test_spaced_thousands_are_one_number_in_prose_and_in_chart_data():
    from case3.chat_turn import number_norms

    source = "Минская область | 105 865,2"
    norms = number_norms(source)
    assert "105865.2" in norms
    assert "105" not in norms
    assert "865.2" not in norms
    tex = r"""
\documentclass{article}
\begin{document}
В Минской области собрано 105 865,2.
\end{document}
"""
    out, charts, _figures, _diagrams, dropped = ground_generated(
        tex,
        [
            {
                "id": "cht_01",
                "caption": "Минская область",
                "html": "data: [105865.2, 999], labels: ['Минская','Гомельская']",
            }
        ],
        [],
        [],
        source=source,
        intent="Сделай отчёт.",
    )
    assert "105 865,2" in out
    assert "999" not in charts[0]["html"]
    assert "105865.2" in charts[0]["html"]
    assert "999" in dropped


def test_decimal_comma_stays_when_a_foreign_number_is_dropped():
    tex = r"""
\documentclass{article}
\begin{document}
Маржа 12,5. Память 77.
\end{document}
"""
    out, _charts, _figures, _diagrams, dropped = ground_generated(
        tex,
        [],
        [],
        [],
        source="Маржа 12,5.",
        intent="Сделай отчёт.",
    )
    assert "12,5" in out
    assert "12, 5" not in out
    assert "77" not in out
    assert "77" in dropped


def test_memory_number_leaves_the_report_and_the_source_number_stays():
    intent = (
        "Сделай отчёт. Новых точек 15.\n\n"
        "Разговор этого чата (не Source).\n"
        "Ответ: выручка 77.\n"
        "Запрос: было 99."
    )
    tex, charts, _figures, _diagrams, dropped = ground_generated(
        _TEX,
        [
            {
                "id": "cht_01",
                "caption": "Выручка 77",
                "html": "data: [20, 77], labels: ['смена']",
                "insight": "скачок 77",
            }
        ],
        [],
        [],
        source="выручка 20",
        intent=intent,
    )
    assert "77" not in tex
    assert "Выручка ." not in tex
    assert "Выручка." not in tex
    assert "20" in tex
    assert "15" in tex
    assert "0.85" in tex
    assert "12pt" in tex
    assert "77" not in charts[0]["caption"]
    assert "77" not in charts[0]["insight"]
    assert "data: [20, null]" in charts[0]["html"]
    assert "77" in dropped
    assert "20" not in dropped
    assert "15" not in dropped


def test_generate_document_strips_a_memory_number(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("выручка 20\n", encoding="utf-8")
    out = tmp_path / "work" / "doc.tex"
    raw = (
        "```json\n"
        '{"charts":[],"diagrams":[],"figures":[]}\n'
        "```\n"
        "```latex\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
                "Выручка 77 держится второй месяц подряд, хотя в источнике указано только 20.\n"
        "\\end{document}\n"
        "```\n"
    )
    generate_document(
        source,
        out_tex=out,
        intent=(
            "Сделай отчёт.\n\n"
            "Разговор этого чата (не Source).\n"
            "Ответ: выручка 77."
        ),
        replay_raw=raw,
        max_images=0,
        max_charts=0,
        max_diagrams=0,
    )
    text = out.read_text(encoding="utf-8")
    assert "77" not in text
    assert "20" in text


def test_slide_scrub_uses_source_not_memory():
    from case3.slides_ir import DeckIrError, parse_deck_ir, scrub_invented_numbers

    source = "выручка 20"
    intent = (
        "Собери слайды.\n\n"
        "Разговор этого чата (не Source).\n"
        "Ответ: доля 77%."
    )
    raw = {
        "version": 1,
        "palette": "atelier",
        "slides": [
            {"id": "s01", "layout": "title", "title": "Касса"},
            {
                "id": "s02",
                "layout": "scorecard",
                "title": "Цифры",
                "kpis": [
                    {"label": "Выручка", "value": "20"},
                    {"label": "Память", "value": "77"},
                ],
            },
            {
                "id": "s03",
                "layout": "closing",
                "title": "Дальше",
                "bullets": ["Держим 20"],
            },
        ],
    }
    allowed = fact_number_tokens(source, intent)
    try:
        parse_deck_ir(raw, source=source, allowed_number_strings=allowed)
    except DeckIrError:
        healed = scrub_invented_numbers(
            raw, source=source, allowed_number_strings=allowed
        )
    else:
        raise AssertionError("77 must not pass as a slide fact")
    assert healed["slides"][1]["kpis"] == [{"label": "Выручка", "value": "20"}]


def test_escaped_percent_does_not_hide_the_memory_number():
    tex = r"""
\documentclass{article}
\begin{document}
В источнике 20\%, а в памяти 77.
% черновик 77
\end{document}
"""
    out, _charts, _figures, _diagrams, dropped = ground_generated(
        tex,
        [],
        [],
        [],
        source="выручка 20",
        intent="Сделай отчёт.\n\nРазговор этого чата (не Source).\nОтвет: 77.",
    )
    assert r"\%77" not in out
    assert "а в памяти 77" not in out
    assert "20" in out
    assert "% черновик 77" in out
    assert "77" in dropped


def test_chart_tooltip_loses_a_memory_number():
    _tex, charts, _figures, _diagrams, _dropped = ground_generated(
        r"\documentclass{article}\begin{document}В источнике 20.\end{document}",
        [
            {
                "id": "cht_01",
                "caption": "Касса",
                "html": "data: [20], title: { text: 'Выручка 77' }, color: 'rgba(77, 77, 77)'",
            }
        ],
        [],
        [],
        source="выручка 20",
        intent="Сделай отчёт.",
    )
    html = charts[0]["html"]
    assert "Выручка 77" not in html
    assert "data: [20]" in html
    assert "rgba(77, 77, 77)" in html


def test_slide_allow_list_keeps_source_spellings_and_drops_memory():
    intent = (
        "Собери слайды.\n\n"
        "Разговор этого чата (не Source).\n"
        "Ответ: доля 77%."
    )
    allowed = fact_number_tokens("Доля 12,5 и 35%.", intent)
    assert "12.5" in allowed
    assert "12,5" in allowed
    assert "35" in allowed
    assert "77" not in allowed


def test_user_number_stays_only_beside_its_word_and_spoken_twelve_counts():
    from case3.fact_ground import ground_generated

    intent = (
        "собери отчёт\n\n"
        "Числа из реплик пользователя (его слова, не ответ модели):\n"
        "2 слайд\n\n"
        "Разговор этого чата (не Source).\n"
    )
    tex = (
        "\\documentclass{article}\n\\begin{document}\n"
        "Выручка 2. Слайд 2 остаётся.\n"
        "\\end{document}\n"
    )
    out, _charts, _figures, _diagrams, _dropped = ground_generated(
        tex, [], [], [], source="Касса без цифр.", intent=intent
    )
    assert "Выручка 2" not in out
    assert "Слайд 2" in out

    spoken_source = ground_generated(
        "\\documentclass{article}\n\\begin{document}\nИтог 12.\n\\end{document}\n",
        [],
        [],
        [],
        source="В кассе двенадцать.",
        intent="собери отчёт",
    )[0]
    assert "12" in spoken_source
    ninety = ground_generated(
        "\\documentclass{article}\n\\begin{document}\nИтог 90.\n\\end{document}\n",
        [],
        [],
        [],
        source="В кассе девяносто.",
        intent="собери отчёт",
    )[0]
    assert "90" in ninety
    invented = ground_generated(
        "\\documentclass{article}\n\\begin{document}\nБыло двенадцать.\n\\end{document}\n",
        [],
        [],
        [],
        source="Касса тихая.",
        intent="собери отчёт",
    )[0]
    assert "двенадцать" not in invented
    from case3.fact_ground import bind_deck_numbers

    deck = bind_deck_numbers(
        {
            "slides": [
                {
                    "kpis": [
                        {"label": "Выручка", "value": "2"},
                        {"label": "Слайд", "value": "2"},
                    ]
                }
            ]
        },
        source="Касса без цифр.",
        intent=intent,
    )
    labels = [item["label"] for item in deck["slides"][0]["kpis"]]
    assert labels == ["Слайд"]
    _bound_tex, charts, _figures, _diagrams, _dropped_chart = ground_generated(
        "\\documentclass{article}\n\\begin{document}\nСлайд 2.\n\\end{document}\n",
        [
            {
                "html": "data: [2], labels: ['касса']",
                "caption": "Слайд 2",
                "highlights": [
                    {"label": "Выручка", "value": "2"},
                    {"label": "Слайд", "value": "2"},
                ],
            }
        ],
        [],
        [],
        source="Касса без цифр.",
        intent=intent,
    )
    assert "data: [2]" not in charts[0]["html"]
    assert "null" in charts[0]["html"]
    assert "Слайд 2" in charts[0]["caption"]
    shown = [row["label"] for row in charts[0]["highlights"] if row.get("value") == "2"]
    assert shown == ["Слайд"]


def test_user_stated_number_stays_in_a_new_report_and_the_answer_number_goes():
    from case3.fact_ground import ground_generated

    intent = (
        "собери отчёт\n\n"
        "Числа из реплик пользователя (его слова, не ответ модели):\n"
        "77 выручк\n\n"
        "Разговор этого чата (не Source).\n"
        "Ответ: было 88."
    )
    tex = (
        "\\documentclass{article}\n\\begin{document}\n"
        "Выручка 77. Модель дописала 88.\n"
        "\\end{document}\n"
    )
    out, charts, figures, diagrams, dropped = ground_generated(
        tex, [], [], [], source="Касса 20.", intent=intent
    )
    assert "77" in out
    assert "88" not in out
    assert "88" in dropped
