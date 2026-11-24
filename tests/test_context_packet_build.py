from __future__ import annotations

import json
from pathlib import Path

from case3.context_packet import (
    build_context_packet,
    compose_slides_prompt_source,
    render_build_user_block,
)
from case3.generate import build_user_prompt, generate_document
from case3.pipeline import run_pipeline
from case3.turn_plan import plan_turn


def test_build_user_prompt_injects_gcp_parallel_to_full_source():
    source = (
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nЗапас 99\n"
    )
    plan = plan_turn("Только по первому документу", mode_hint="report")
    packet = build_context_packet(
        plan=plan,
        user_text="Только по первому документу",
        source_text=source,
    )
    gcp = render_build_user_block(packet)
    prompt = build_user_prompt(
        intent="Сделай отчёт",
        source=source,
        max_images=0,
        max_charts=0,
        max_diagrams=0,
        gcp_block=gcp,
    )
    assert "## Выбранные источники" in prompt
    assert "Запас 99" in prompt
    assert "Выручка 10" in prompt
    assert prompt.index("## Выбранные источники") < prompt.index("## Source")


def test_generate_document_fact_ground_uses_full_source_not_gcp_selection(tmp_path: Path):
    full = (
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nЗапас 99\n"
    )
    selected = "Выручка 10"
    source = tmp_path / "focus_only.txt"
    source.write_text(selected, encoding="utf-8")
    out = tmp_path / "work" / "doc.tex"
    raw = (
        "```json\n"
        '{"charts":[],"diagrams":[],"figures":[]}\n'
        "```\n"
        "```latex\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\section{Итоги}\n"
        "По первому документу выручка 10, по второму запас 99.\n"
        "\\end{document}\n"
        "```\n"
    )
    generate_document(
        source,
        out_tex=out,
        intent="Только по первому документу",
        replay_raw=raw,
        max_images=0,
        max_charts=0,
        max_diagrams=0,
        grounding_source=full,
    )
    text = out.read_text(encoding="utf-8")
    assert "99" in text
    assert "10" in text


def test_pipeline_report_persists_manifest_and_passes_gcp_block(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "project"
    (root / "prompt" / "gold").mkdir(parents=True)
    source = tmp_path / "source.md"
    source.write_text(
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nВыручка 20\n",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def _fake_generate(source_path, *, out_tex, intent=None, **kwargs):
        captured["gcp_block"] = kwargs.get("gcp_block") or ""
        captured["grounding"] = kwargs.get("grounding_source") or ""
        out_tex.parent.mkdir(parents=True, exist_ok=True)
        out_tex.write_text(
            "\\documentclass{article}\n\\begin{document}\nok\\end{document}\n",
            encoding="utf-8",
        )
        (out_tex.parent / "figures.json").write_text(
            json.dumps({"figures": [], "charts": [], "diagrams": []}),
            encoding="utf-8",
        )
        (out_tex.parent / "source.raw_model.txt").write_text("{}", encoding="utf-8")
        return out_tex, [], [], []

    def _fake_render(tex_path, **kwargs):
        pdf = Path(kwargs.get("out_dir") or tex_path.parent) / "source.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        return {"pdf": pdf}

    monkeypatch.setenv("CASE3_MAX_CHARTS", "0")
    monkeypatch.setenv("IMAGE_MAX_IMAGES", "0")
    monkeypatch.setattr("case3.pipeline.generate_document", _fake_generate)
    monkeypatch.setattr("case3.pipeline.render_tex", _fake_render)

    out = run_pipeline(
        source,
        project_root=root,
        intent="Сравни первый и второй документы",
        output_mode="report",
        formats={"pdf"},
        max_charts=0,
        max_images=0,
        dry_run=False,
        run_id="gcp_report_20261124T120000Z",
    )
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["selection_manifest"]["evidence_ids"]
    gcp_block = str(captured["gcp_block"])
    grounding = str(captured["grounding"])
    assert "## Выбранные источники" in gcp_block
    assert "Выручка 20" in grounding
    assert "Выручка 10" in grounding


def test_compose_slides_prompt_source_puts_gcp_before_brief():
    source = (
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nЗапас 99\n"
    )
    plan = plan_turn("Сравни первый и второй", mode_hint="presentation")
    packet = build_context_packet(
        plan=plan,
        user_text="Сравни первый и второй",
        source_text=source,
    )
    gcp = render_build_user_block(packet)
    composed = compose_slides_prompt_source(gcp_block=gcp, source_text=source)
    assert composed.index("## Выбранные источники") < composed.index("Выручка")
    assert "Запас 99" in composed


def test_build_context_packet_merges_inherited_catalog_hashes():
    source = "===== Документ 1: A.md =====\nВыручка 10\n"
    plan = plan_turn("Только по первому", mode_hint="presentation")
    parent = build_context_packet(
        plan=plan,
        user_text="Только по первому",
        source_text=source,
    )
    inherited = dict(parent.selection_manifest.hashes)
    child = build_context_packet(
        plan=plan_turn("Сделай слайды", mode_hint="presentation"),
        user_text="Сделай слайды",
        source_text=source,
        catalog_hashes=inherited,
    )
    assert child.selection_manifest.hashes == inherited
    assert child.packet_id != parent.packet_id


def test_pipeline_presentation_persists_manifest_and_gcp_block(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "project"
    (root / "prompt" / "gold").mkdir(parents=True)
    source = tmp_path / "source.md"
    source.write_text(
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nВыручка 20\n",
        encoding="utf-8",
    )

    def _fake_complete_diagrams(**_kwargs):
        return []

    def _fake_charts(*_a, **_kw):
        return [], "ok"

    monkeypatch.setenv("CASE3_MAX_CHARTS", "0")
    monkeypatch.setenv("IMAGE_MAX_IMAGES", "0")
    monkeypatch.setattr("case3.diagram_generate.complete_diagrams", _fake_complete_diagrams)
    monkeypatch.setattr("case3.chat_turn.generate_chat_charts", _fake_charts)

    out = run_pipeline(
        source,
        project_root=root,
        intent="Сделай презентацию по первому документу",
        output_mode="presentation",
        formats=set(),
        max_charts=0,
        max_images=0,
        dry_run=True,
        run_id="gcp_pres_20261124T120000Z",
    )
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["selection_manifest"]["evidence_ids"]
    gcp = str(meta.get("gcp_build_block") or "")
    assert "## Выбранные источники" in gcp
    assert meta["source_catalog_hashes"] == meta["selection_manifest"]["hashes"]