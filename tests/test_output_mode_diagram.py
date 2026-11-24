"""output_mode=diagram — Mermaid + short prose, no PDF/DOCX."""

from __future__ import annotations

from case3.api import (
    apply_mode_caps,
    apply_turn_caps,
    build_intent_from_ui,
    parse_formats_form,
)
from case3.pipeline import (
    _presentation_chat_blurb,
    resolve_pipeline_formats,
)
from case3.turn_plan import plan_turn


def test_presentation_keeps_diagrams_for_the_deck_and_skips_pdf() -> None:
    charts, images, diagrams, formats, no_charts, no_images = apply_mode_caps(
        "presentation",
        max_charts=3,
        max_images=2,
        max_diagrams=2,
        formats="both",
        no_charts=False,
        no_images=False,
    )
    assert formats == "none"
    assert diagrams == 2
    assert charts == 3
    assert images == 2
    assert no_charts is False
    assert no_images is False

    _, _, diagrams0, formats0, _, _ = apply_mode_caps(
        "presentation",
        max_charts=3,
        max_images=0,
        max_diagrams=0,
        formats="pdf",
        no_charts=False,
        no_images=True,
    )
    assert formats0 == "none"
    assert diagrams0 == 0


def test_turn_caps_do_not_force_unrequested_presentation_diagram() -> None:
    plan = plan_turn("Собери презентацию", mode_hint="presentation")
    charts, images, diagrams, formats, no_charts, no_images = apply_turn_caps(
        plan,
        max_charts=3,
        max_images=2,
        max_diagrams=0,
        formats="both",
        no_charts=False,
        no_images=False,
    )
    assert (charts, images, diagrams) == (3, 2, 0)
    assert formats == "none"
    assert no_charts is False
    assert no_images is False


def test_turn_caps_force_requested_presentation_diagram() -> None:
    plan = plan_turn("Собери презентацию", mode_hint="presentation")
    plan.build_media["diagram"] = True
    caps = apply_turn_caps(
        plan,
        max_charts=0,
        max_images=0,
        max_diagrams=0,
        formats="both",
        no_charts=True,
        no_images=True,
    )
    assert caps[2] == 1


def test_turn_caps_allow_chat_charts_only_when_plan_requests_one() -> None:
    plain = plan_turn("Расскажи о данных", mode_hint="chat")
    visual = plan_turn("Построй график в чате", mode_hint="chat")

    plain_caps = apply_turn_caps(
        plain,
        max_charts=3,
        max_images=2,
        max_diagrams=2,
        formats="both",
        no_charts=False,
        no_images=False,
    )
    visual_caps = apply_turn_caps(
        visual,
        max_charts=3,
        max_images=2,
        max_diagrams=2,
        formats="both",
        no_charts=False,
        no_images=False,
    )

    assert plain_caps[:4] == (1, 0, 0, "none")
    assert visual_caps[:4] == (2, 0, 0, "none")


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


def test_pipeline_diagram_mode_uses_fast_diagram_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    from pathlib import Path
    from case3.pipeline import run_pipeline

    src = tmp_path / "source.txt"
    src.write_text("Процесс возврата товара клиентом", encoding="utf-8")

    calls = []
    class DummyLLM:
        def __init__(self, cfg):
            self.cfg = cfg
        def complete(self, *, system, user_text, cancel_check=None, reasoning=None, images=None):
            calls.append((system, user_text, self.cfg.max_tokens))
            return '```json\n{"diagrams": [{"id": "dia_01", "title": "Возврат", "type": "flowchart", "mermaid": "flowchart TD\\nA-->B"}]}\n```'

    monkeypatch.setattr("case3.llm_client.LLMClient", DummyLLM)
    monkeypatch.setattr("case3.generate.LLMClient", DummyLLM)
    monkeypatch.setattr("case3.chat_summary.LLMClient", DummyLLM)
    out = run_pipeline(
        src,
        project_root=tmp_path,
        dry_run=False,
        output_mode="diagram",
        max_diagrams=2,
        formats=set(),
    )
    assert len(calls) >= 1
    diagram_calls = [item for item in calls if item[2] >= 2048]
    assert diagram_calls, calls
    system_prompt, _, max_tokens = diagram_calls[0]
    assert len(system_prompt) < 5000
    assert max_tokens >= 2048
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert len(fj["diagrams"]) == 1
    assert fj["diagrams"][0]["id"] == "dia_01"

