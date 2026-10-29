"""output_mode=diagram — Mermaid + short prose, no PDF/DOCX."""

from __future__ import annotations

from case3.api import build_intent_from_ui, parse_formats_form
from case3.pipeline import (
    _presentation_chat_blurb,
    resolve_pipeline_formats,
)


def test_parse_formats_none_empty_set() -> None:
    assert parse_formats_form("none") == set()
    assert parse_formats_form("both") == {"pdf", "docx"}
    assert parse_formats_form("pdf") == {"pdf"}


def test_resolve_pipeline_formats_keeps_empty_for_presentation() -> None:
    """Empty set from formats=none must not collapse to {pdf} (falsy-or bug)."""
    assert resolve_pipeline_formats(None) == {"pdf"}
    assert resolve_pipeline_formats(set()) == set()
    assert resolve_pipeline_formats({"docx"}) == {"docx"}
    assert resolve_pipeline_formats(parse_formats_form("none")) == set()


def test_presentation_chat_blurb_is_local_and_mentions_media() -> None:
    blurb = _presentation_chat_blurb(
        charts=[{"id": "cht_01"}, {"id": "cht_02"}],
        figures=[{"id": "fig_01"}],
    )
    assert "презентац" in blurb.lower()
    assert "графиков: 2" in blurb
    assert "фото: 1" in blurb
    assert _presentation_chat_blurb() == "Ок, собираем презентацию…"


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
