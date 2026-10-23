"""Native OOXML charts land in PPTX when series IR is present."""

from __future__ import annotations

import zipfile
from pathlib import Path

from pptx.dml.color import RGBColor

from case3.slides_pptx_charts import add_native_chart
from case3.slides_pptx_native import build_native_pptx


def test_add_native_chart_embeds_chart_part(tmp_path: Path) -> None:
    deck = {
        "version": 1,
        "aspect": "16:9",
        "palette": "atelier",
        "style": {
            "pack_id": "atelier",
            "colors": {
                "primary": "#2E4208",
                "accent": "#4F6B14",
                "ink": "#14161a",
                "ink2": "#2c3028",
                "muted": "#6A7160",
                "paper": "#f0ede4",
                "sheet": "#fffcf7",
                "rule": "#e6e2d8",
            },
            "fonts": {"title": "Georgia", "body": "Calibri", "fallback_pptx": "Calibri"},
            "chart_series": ["#2E4208", "#4F6B14"],
        },
        "slides": [
            {
                "id": "s1",
                "layout": "chart_hero",
                "title": "Revenue",
                "chart_id": "cht_1",
                "takeaway": "Up",
            }
        ],
    }
    series = {
        "type": "bar",
        "categories": ["Q1", "Q2", "Q3"],
        "series": [{"name": "Rev", "values": [10.0, 14.0, 18.0]}],
    }
    dest = tmp_path / "charts.pptx"
    build_native_pptx(deck, dest, chart_series_by_id={"cht_1": series})
    assert dest.is_file()
    with zipfile.ZipFile(dest) as zf:
        charts = [n for n in zf.namelist() if n.startswith("ppt/charts/")]
    assert charts, "expected native ppt/charts/* when series provided"


def test_add_native_chart_rejects_empty() -> None:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    ok = add_native_chart(
        slide,
        {"type": "bar", "categories": [], "series": []},
        left=Inches(1),
        top=Inches(1),
        width=Inches(6),
        height=Inches(4),
        series_colors=[RGBColor(0x2E, 0x42, 0x08)],
    )
    assert ok is False
