"""Deck IR parse + Source-bound number gate + arc rules."""

from __future__ import annotations

import pytest

from case3.slides_ir import SLIDE_LAYOUTS, DeckIrError, parse_deck_ir

SOURCE = "Выручка 120 млн в 2024 году. Доля 35%. NPS 42."


def _base_slides(**extra: object) -> list[dict]:
    slides = [
        {"id": "s01", "layout": "title", "title": "Итоги", "subtitle": "2024"},
        {
            "id": "s02",
            "layout": "bullets",
            "title": "Факты",
            "bullets": ["Выручка 120 млн", "Доля 35%"],
        },
        {"id": "s03", "layout": "closing", "title": "Далее", "bullets": ["План"]},
    ]
    if extra:
        # replace middle for custom tests via caller
        pass
    return slides


def test_layouts_whitelist() -> None:
    assert "kpi_row" in SLIDE_LAYOUTS
    assert "chart_split" in SLIDE_LAYOUTS
    assert "section" in SLIDE_LAYOUTS
    assert "scorecard" in SLIDE_LAYOUTS
    assert "callout" in SLIDE_LAYOUTS
    assert "table_hero" in SLIDE_LAYOUTS


def test_section_scorecard_callout_table() -> None:
    ir = parse_deck_ir(
        {
            "version": 1,
            "palette": "atelier",
            "slides": [
                {
                    "id": "s01",
                    "layout": "title",
                    "title": "Выручка 120 млн — главный итог",
                    "takeaway": "Рост за счёт доли 35%",
                    "subtitle": "2024",
                },
                {
                    "id": "s02",
                    "layout": "section",
                    "chapter": 1,
                    "title": "Цифры",
                    "subtitle": "Что уже в Source",
                },
                {
                    "id": "s03",
                    "layout": "scorecard",
                    "chapter": 1,
                    "title": "Три рычага",
                    "kpis": [
                        {
                            "label": "Выручка",
                            "value": "120 млн",
                            "delta": "+12%",
                            "status": "up",
                        },
                        {"label": "Доля", "value": "35%", "status": "flat"},
                        {"label": "NPS", "value": "42", "delta": "+3", "status": "up"},
                    ],
                },
                {
                    "id": "s04",
                    "layout": "callout",
                    "chapter": 2,
                    "title": "Определение",
                    "term": "Доля",
                    "definition": "Доля 35% — сегмент в Source.",
                },
                {
                    "id": "s05",
                    "layout": "table_hero",
                    "title": "Сводка",
                    "rows": [
                        ["Метрика", "2024"],
                        ["Выручка", "120 млн"],
                        ["Доля", "35%"],
                    ],
                },
                {"id": "s06", "layout": "closing", "title": "Далее", "bullets": ["План"]},
            ],
        },
        source=SOURCE + " Рост +12%. NPS +3.",
    )
    assert ir["slides"][1]["layout"] == "section"
    assert ir["slides"][1]["chapter"] == 1
    assert ir["slides"][2]["kpis"][0]["delta"] == "+12%"
    assert ir["slides"][3]["term"] == "Доля"
    assert len(ir["slides"][4]["rows"]) == 3
    assert ir["slides"][0].get("takeaway")


def test_accepts_arc_title_bullets_closing() -> None:
    ir = parse_deck_ir(
        {
            "version": 1,
            "aspect": "16:9",
            "palette": "atelier",
            "language": "ru",
            "slides": _base_slides(),
        },
        source=SOURCE,
    )
    assert len(ir["slides"]) == 3
    assert ir["slides"][0]["layout"] == "title"
    assert ir["slides"][-1]["layout"] == "closing"


def test_rejects_unknown_layout() -> None:
    with pytest.raises(DeckIrError, match="layout"):
        parse_deck_ir(
            {
                "version": 1,
                "palette": "atelier",
                "slides": [
                    {"id": "s01", "layout": "title", "title": "T"},
                    {"id": "s02", "layout": "agenda", "title": "X"},
                    {"id": "s03", "layout": "closing", "title": "C", "bullets": ["a"]},
                ],
            },
            source=SOURCE,
        )


def test_rejects_invented_number() -> None:
    with pytest.raises(DeckIrError, match="number|Source|source"):
        parse_deck_ir(
            {
                "version": 1,
                "palette": "atelier",
                "slides": [
                    {"id": "s01", "layout": "title", "title": "T"},
                    {
                        "id": "s02",
                        "layout": "bullets",
                        "title": "X",
                        "bullets": ["Выручка 999 млрд"],
                    },
                    {"id": "s03", "layout": "closing", "title": "C", "bullets": ["a"]},
                ],
            },
            source=SOURCE,
        )


def test_rejects_three_consecutive_bullets() -> None:
    with pytest.raises(DeckIrError, match="consecutive"):
        parse_deck_ir(
            {
                "version": 1,
                "palette": "atelier",
                "slides": [
                    {"id": "s01", "layout": "title", "title": "T"},
                    {
                        "id": "s02",
                        "layout": "bullets",
                        "title": "A",
                        "bullets": ["Выручка 120 млн"],
                    },
                    {
                        "id": "s03",
                        "layout": "bullets",
                        "title": "B",
                        "bullets": ["Доля 35%"],
                    },
                    {
                        "id": "s04",
                        "layout": "bullets",
                        "title": "C",
                        "bullets": ["NPS 42"],
                    },
                    {"id": "s05", "layout": "closing", "title": "Z", "bullets": ["ok"]},
                ],
            },
            source=SOURCE,
        )


def test_rejects_missing_closing() -> None:
    with pytest.raises(DeckIrError, match="closing"):
        parse_deck_ir(
            {
                "version": 1,
                "palette": "atelier",
                "slides": [
                    {"id": "s01", "layout": "title", "title": "T"},
                    {
                        "id": "s02",
                        "layout": "bullets",
                        "title": "A",
                        "bullets": ["Выручка 120 млн"],
                    },
                    {
                        "id": "s03",
                        "layout": "bullets",
                        "title": "B",
                        "bullets": ["Доля 35%"],
                    },
                ],
            },
            source=SOURCE,
        )


def test_kpi_row_ok() -> None:
    ir = parse_deck_ir(
        {
            "version": 1,
            "palette": "atelier",
            "slides": [
                {"id": "s01", "layout": "title", "title": "T"},
                {
                    "id": "s02",
                    "layout": "kpi_row",
                    "title": "KPI",
                    "kpis": [
                        {"label": "Выручка", "value": "120 млн", "hint": "2024"},
                        {"label": "Доля", "value": "35%"},
                        {"label": "NPS", "value": "42"},
                    ],
                },
                {"id": "s03", "layout": "closing", "title": "C", "bullets": ["Далее"]},
            ],
        },
        source=SOURCE,
    )
    assert ir["slides"][1]["layout"] == "kpi_row"
    assert len(ir["slides"][1]["kpis"]) == 3


def test_chart_split_ok() -> None:
    ir = parse_deck_ir(
        {
            "version": 1,
            "palette": "ocean",
            "slides": [
                {"id": "s01", "layout": "title", "title": "T"},
                {
                    "id": "s02",
                    "layout": "chart_split",
                    "title": "Доля 35%",
                    "chart_id": "cht_01",
                    "body": "Ключевой показатель 2024",
                    "bullets": ["Доля 35%"],
                },
                {"id": "s03", "layout": "closing", "title": "C", "bullets": ["ok"]},
            ],
        },
        source=SOURCE,
    )
    assert ir["slides"][1]["chart_id"] == "cht_01"


def test_normalize_auto_palette_to_atelier() -> None:
    ir = parse_deck_ir(
        {
            "version": 1,
            "palette": "auto",
            "slides": [
                {"id": "s01", "layout": "title", "title": "Hello"},
                {
                    "id": "s02",
                    "layout": "bullets",
                    "title": "A",
                    "bullets": ["no digits here"],
                },
                {"id": "s03", "layout": "closing", "title": "Bye", "bullets": ["x"]},
            ],
        },
        source=SOURCE,
    )
    assert ir["palette"] == "atelier"
