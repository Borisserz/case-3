"""Retype the chart on a named deck slide — not every chart in the run."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from case3.chat_revise import _chart_id_on_slide, _retype_on_slide


def _seed_deck(out: Path) -> None:
    slides = out / "slides"
    slides.mkdir(parents=True)
    (slides / "deck.json").write_text(
        json.dumps(
            {
                "version": 1,
                "slides": [
                    {"id": "s1", "layout": "title", "title": "Старт"},
                    {"id": "s2", "layout": "chart_hero", "chart_id": "cht_01"},
                    {"id": "s3", "layout": "chart_hero", "media_id": "cht_02"},
                    {"id": "s4", "layout": "chart_hero", "chart_id": "cht_03"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "figures.json").write_text(
        json.dumps(
            {
                "charts": [
                    {"id": "cht_01", "type": "bar", "html": "<canvas></canvas>"},
                    {"id": "cht_02", "type": "line", "html": "<canvas></canvas>"},
                    {"id": "cht_03", "type": "donut", "html": "<canvas></canvas>"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "meta.json").write_text(
        json.dumps({"charts_planned": ["cht_01", "cht_02", "cht_03"]}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_chart_id_on_slide_reads_chart_id_and_media_id(tmp_path: Path) -> None:
    _seed_deck(tmp_path)
    assert _chart_id_on_slide(tmp_path, 1) is None
    assert _chart_id_on_slide(tmp_path, 2) == "cht_01"
    assert _chart_id_on_slide(tmp_path, 3) == "cht_02"
    assert _chart_id_on_slide(tmp_path, 4) == "cht_03"
    assert _chart_id_on_slide(tmp_path, 9) is None


def test_retype_on_slide_edits_only_that_chart(tmp_path: Path) -> None:
    _seed_deck(tmp_path)
    edited: list[str] = []

    def _fake_edit(out_dir, chart_id, **kwargs):  # noqa: ANN001
        edited.append(chart_id)
        # Pretend type landed
        fj = json.loads((out_dir / "figures.json").read_text(encoding="utf-8"))
        for chart in fj["charts"]:
            if chart["id"] == chart_id:
                chart["type"] = kwargs.get("chart_type") or chart["type"]
                chart["html"] = "type:'area'"
        (out_dir / "figures.json").write_text(
            json.dumps(fj, ensure_ascii=False), encoding="utf-8"
        )
        return {"chart_id": chart_id}

    with (
        patch("case3.chart_edit.edit_chart_in_run", _fake_edit),
        patch("case3.chat_revise._type_landed", return_value=True),
    ):
        say = _retype_on_slide(tmp_path, "area", 3)

    assert edited == ["cht_02"]
    assert "слайде 3" in say.casefold() or "слайд 3" in say.casefold()
    assert "площад" in say.casefold()


def test_retype_on_slide_without_chart_explains(tmp_path: Path) -> None:
    _seed_deck(tmp_path)
    say = _retype_on_slide(tmp_path, "area", 1)
    assert "нет графика" in say.casefold()
