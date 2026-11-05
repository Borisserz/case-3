"""Content fit: one fact per slide, real sides, written numbers, one question."""

from __future__ import annotations

from case3.slides_ir import parse_deck_ir

BOARD = (
    "сделай презентацию для совета директоров слайдов 13. "
    "выручка 18,4 млн при плане 19. к прошлому году +53%. "
    "новых продаж 1,9 млн, это 86% плана. кэш 20,4 млн, хватает на 24 месяца. "
    "nrr 117%. вопрос нанимать двух продажников или нет"
)


def _wrap(slides: list[dict]) -> dict:
    return {"version": 1, "palette": "board", "slides": slides}


def test_thousands_word_allows_the_absolute_form() -> None:
    deck = parse_deck_ir(
        _wrap(
            [
                {"id": "s01", "layout": "title", "title": "Неделя"},
                {
                    "id": "s02",
                    "layout": "bullets",
                    "title": "Расход",
                    "bullets": ["Потратили 86000."],
                },
                {"id": "s03", "layout": "closing", "title": "Дальше", "bullets": ["Поиск"]},
            ]
        ),
        source="за неделю потратили 86 тысяч, отдача 4,1",
    )
    assert "86000" in deck["slides"][1]["bullets"][0]


def test_bare_fragment_does_not_match_a_larger_integer() -> None:
    import pytest
    from case3.slides_ir import DeckIrError

    with pytest.raises(DeckIrError):
        parse_deck_ir(
            _wrap(
                [
                    {"id": "s01", "layout": "title", "title": "Неделя"},
                    {
                        "id": "s02",
                        "layout": "bullets",
                        "title": "Расход",
                        "bullets": ["Потратили 86."],
                    },
                    {"id": "s03", "layout": "closing", "title": "Дальше", "bullets": ["Поиск"]},
                ]
            ),
            source="потратили 86000 без слова тысяч",
        )


def test_empty_section_and_echo_slide_drop() -> None:
    deck = parse_deck_ir(
        _wrap(
            [
                {"id": "s01", "layout": "title", "title": "Совет", "subtitle": "Выручка 18,4 млн"},
                {
                    "id": "s02",
                    "layout": "section",
                    "title": "Где мы сейчас",
                    "subtitle": "Факты без добавлений",
                },
                {
                    "id": "s03",
                    "layout": "bullets",
                    "title": "Выручка",
                    "bullets": ["Выручка 18,4 млн при плане 19."],
                },
                {
                    "id": "s04",
                    "layout": "bullets",
                    "title": "То же",
                    "bullets": ["Выручка 18,4 млн при плане 19."],
                },
                {"id": "s05", "layout": "closing", "title": "Дальше", "bullets": ["Решение"]},
            ]
        ),
        source=BOARD,
    )
    ids = [s["id"] for s in deck["slides"]]
    assert "s02" not in ids
    assert "s04" not in ids
    assert ids[0] == "s01" and ids[-1] == "s05"


def test_negated_compare_becomes_one_question() -> None:
    deck = parse_deck_ir(
        _wrap(
            [
                {"id": "s01", "layout": "title", "title": "Совет"},
                {
                    "id": "s02",
                    "layout": "compare",
                    "title": "Нанять двух продажников или нет",
                    "cards": [
                        {"title": "Нанять двух продажников", "body": "Вопрос совета."},
                        {"title": "Не нанимать двух продажников", "body": "Вопрос совета."},
                    ],
                },
                {"id": "s03", "layout": "closing", "title": "Дальше", "bullets": ["Решение"]},
            ]
        ),
        source=BOARD,
    )
    mid = deck["slides"][1]
    assert mid["layout"] == "callout"
    assert "cards" not in mid
    assert "нанимать" in mid["definition"].casefold()


def test_scorecard_title_stops_listing_every_kpi() -> None:
    deck = parse_deck_ir(
        _wrap(
            [
                {"id": "s01", "layout": "title", "title": "Совет"},
                {
                    "id": "s02",
                    "layout": "scorecard",
                    "kicker": "Показатели",
                    "title": "Выручка 18,4 млн при плане 19; продажи 1,9 млн",
                    "subtitle": "Выручка 18,4 млн и продажи 1,9 млн.",
                    "kpis": [
                        {"label": "Выручка", "value": "18,4 млн", "hint": "План 19."},
                        {"label": "Продажи", "value": "1,9 млн", "hint": "86% плана."},
                    ],
                },
                {"id": "s03", "layout": "closing", "title": "Дальше", "bullets": ["Решение"]},
            ]
        ),
        source=BOARD,
    )
    card = deck["slides"][1]
    assert card["title"] == "Показатели"
    assert "subtitle" not in card


def test_source_question_is_its_own_slide_before_closing() -> None:
    deck = parse_deck_ir(
        _wrap(
            [
                {"id": "s01", "layout": "title", "title": "Совет", "subtitle": "Выручка 18,4 млн"},
                {
                    "id": "s02",
                    "layout": "bullets",
                    "title": "Кэш",
                    "bullets": ["Кэш 20,4 млн хватает на 24 месяца."],
                },
                {"id": "s03", "layout": "closing", "title": "Дальше", "bullets": ["Смотреть план"]},
            ]
        ),
        source=BOARD,
    )
    assert deck["slides"][-2]["layout"] == "callout"
    assert "или нет" not in deck["slides"][-2]["definition"]
    assert deck["slides"][-2]["definition"].endswith("?")
    assert deck["slides"][-1]["layout"] == "closing"
