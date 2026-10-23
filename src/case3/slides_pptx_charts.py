"""Add native OOXML charts to Liber PPTX slides."""

from __future__ import annotations

from typing import Any

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Emu, Inches, Pt


def _chart_type(ir_type: str):
    t = (ir_type or "bar").lower()
    if t == "line":
        return XL_CHART_TYPE.LINE_MARKERS
    if t == "area":
        return XL_CHART_TYPE.AREA
    if t in ("stacked_bar",):
        return XL_CHART_TYPE.COLUMN_STACKED
    if t == "horizontal_bar":
        return XL_CHART_TYPE.BAR_CLUSTERED
    if t == "donut":
        return XL_CHART_TYPE.DOUGHNUT
    if t in ("grouped_bar", "bar"):
        return XL_CHART_TYPE.COLUMN_CLUSTERED
    return XL_CHART_TYPE.COLUMN_CLUSTERED


def add_native_chart(
    slide,
    series_ir: dict[str, Any],
    *,
    left,
    top,
    width,
    height,
    series_colors: list[RGBColor] | None = None,
) -> bool:
    """Embed a native chart; return False if data unusable."""
    cats = list(series_ir.get("categories") or [])
    series = list(series_ir.get("series") or [])
    if not cats or not series:
        return False
    data = CategoryChartData()
    data.categories = cats
    for s in series:
        name = str(s.get("name") or "Series")
        vals = list(s.get("values") or [])
        if len(vals) < len(cats):
            vals = vals + [0.0] * (len(cats) - len(vals))
        data.add_series(name, vals[: len(cats)])

    chart_type = _chart_type(str(series_ir.get("type") or "bar"))
    try:
        graphic = slide.shapes.add_chart(
            chart_type, left, top, width, height, data
        )
    except Exception:
        return False
    chart = graphic.chart
    try:
        chart.has_legend = len(series) > 1
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
    except Exception:
        pass

    # Soft color series from theme when possible
    if series_colors:
        try:
            for i, ser in enumerate(chart.series):
                color = series_colors[i % len(series_colors)]
                if chart_type in (
                    XL_CHART_TYPE.LINE_MARKERS,
                    XL_CHART_TYPE.LINE,
                ):
                    ser.format.line.color.rgb = color
                else:
                    ser.format.fill.solid()
                    ser.format.fill.fore_color.rgb = color
        except Exception:
            pass

    try:
        plot = chart.plots[0]
        plot.has_data_labels = False
    except Exception:
        pass

    # Quiet axis text size
    try:
        chart.font.size = Pt(10)
    except Exception:
        pass

    return True


def default_chart_box(*, split: bool) -> tuple:
    if split:
        return Inches(6.4), Inches(1.7), Inches(6.2), Inches(4.6)
    return Inches(0.7), Inches(1.65), Inches(11.9), Inches(4.8)
