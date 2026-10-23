"""output_mode=diagram — Mermaid + short prose, no PDF/DOCX."""

from __future__ import annotations

from case3.api import build_intent_from_ui, parse_formats_form


def test_parse_formats_none_empty_set() -> None:
    assert parse_formats_form("none") == set()
    assert parse_formats_form("both") == {"pdf", "docx"}
    assert parse_formats_form("pdf") == {"pdf"}


def test_diagram_mode_intent_forces_schemas_no_charts() -> None:
    intent = build_intent_from_ui(
        chat="Покажи процесс онбординга",
        chart_types=[],
        max_charts=0,
        max_images=0,
        max_diagrams=2,
        forbid_charts=True,
        forbid_images=True,
        chart_auto=True,
        output_mode="diagram",
    )
    low = intent.lower()
    assert "режим схема" in low or "output_mode=diagram" in low or "только" in low
    assert "mermaid" in low or "схем" in low
    assert "без html-графиков" in low or "charts: []" in low
