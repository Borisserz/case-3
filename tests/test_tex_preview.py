"""TeX → chat preview blocks."""

from __future__ import annotations

from pathlib import Path

from case3.tex_preview import build_report_preview, tex_to_preview_blocks

FIXTURE = Path(__file__).parent / "fixtures" / "preview_sample.tex"


def test_tex_to_preview_extracts_structure() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    data = tex_to_preview_blocks(tex)
    assert data["title"] == "Демография 2019–2023"
    types = [b["type"] for b in data["blocks"]]
    assert "heading" in types
    assert "paragraph" in types
    assert "table" in types
    assert "figure" in types
    headings = [b for b in data["blocks"] if b["type"] == "heading"]
    assert headings[0]["level"] == 1
    assert "Общая" in headings[0]["text"]
    table = next(b for b in data["blocks"] if b["type"] == "table")
    assert table["headers"] == ["Показатель", "Значение", "Комментарий"]
    assert len(table["rows"]) == 2
    assert "72 000" in table["rows"][1][1] or "72000" in table["rows"][1][1].replace(
        " ", ""
    )
    figs = [b for b in data["blocks"] if b["type"] == "figure"]
    assert figs[0]["id"] == "cht_01"
    assert figs[0]["caption"] == "Численность населения"


def test_build_report_preview_attaches_urls_and_captions() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    media = {
        "cht_01": {"ok": True, "kind": "chart"},
        "fig_01": {"ok": True, "kind": "figure"},
    }
    figures_json = {
        "charts": [{"id": "cht_01", "caption": "from json"}],
        "figures": [{"id": "fig_01", "caption": "Схема из JSON"}],
    }
    preview = build_report_preview(
        tex,
        run_id="demo_run",
        media_status=media,
        figures_json=figures_json,
    )
    figs = [b for b in preview["blocks"] if b["type"] == "figure"]
    assert figs[0]["url"] == "/api/runs/demo_run/figures/cht_01.png"
    assert figs[0]["kind"] == "chart"
    # empty TeX caption filled from figures.json
    fig01 = next(b for b in figs if b["id"] == "fig_01")
    assert fig01["caption"] == "Схема из JSON"
    assert fig01["kind"] == "image"


def test_failed_media_omits_url() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    preview = build_report_preview(
        tex,
        run_id="x",
        media_status={"cht_01": {"ok": False, "kind": "chart"}},
        figures_json={},
    )
    fig = next(b for b in preview["blocks"] if b.get("id") == "cht_01")
    assert not fig.get("url")
