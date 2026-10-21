"""Horizontal bar charts must not look sparse / washed-out after regen."""

from __future__ import annotations

import re

from case3.chart_style import apply_palette_to_html, palette_from_intent
from case3.chart_types_coerce import harden_chart_html, polish_charts


_HBAR = (
    '<canvas id="c1" width="1100" height="560"></canvas><script>'
    "new Chart(document.getElementById('c1'),{type:'bar',data:{"
    "labels:['Янв','Фев','Мар','Апр','Май','Июн'],"
    "datasets:[{label:'Выручка',data:[12.4,19.1,15.6,28.3,24.0,32.7],"
    "borderColor:'#023E8A',backgroundColor:'rgba(0,180,216,0.18)',"
    "borderWidth:1,barPercentage:0.7,categoryPercentage:0.8}]},"
    "options:{indexAxis:'y',plugins:{legend:{display:false}},"
    "scales:{x:{beginAtZero:true},y:{grid:{display:false}}}}});"
    "window.__CASE3_CHART_READY=true;</script>"
)


def test_harden_horizontal_bar_shrinks_tall_canvas() -> None:
    out = harden_chart_html(_HBAR, "horizontal_bar")
    m = re.search(r'height="(\d+)"', out)
    assert m is not None
    h = int(m.group(1))
    assert 280 <= h <= 420
    assert h < 560


def test_harden_horizontal_bar_solidifies_ghost_fill() -> None:
    out = harden_chart_html(_HBAR, "horizontal_bar")
    assert "rgba(0,180,216,0.18)" not in out
    assert re.search(r"backgroundColor\s*:\s*'#00B4D8'", out, re.I) or re.search(
        r"backgroundColor\s*:\s*'rgba\(0,180,216,0\.(5|6|7|8|9)", out
    )


def test_harden_horizontal_bar_denser_bars() -> None:
    out = harden_chart_html(_HBAR, "horizontal_bar")
    assert re.search(r"barPercentage\s*:\s*0\.7[89]", out)
    assert re.search(r"categoryPercentage\s*:\s*0\.8[5-9]", out)


def test_palette_from_intent_atelier() -> None:
    intent = (
        "Требования UI:\n"
        "- палитра графиков: Atelier (atelier) — ink #3F5210, accents #5A6E28\n"
    )
    assert palette_from_intent(intent) == "atelier"


def test_palette_from_intent_auto() -> None:
    intent = "- палитра графиков: AUTO — выбери одну из editorial/ocean\n"
    assert palette_from_intent(intent) == "auto"


def test_polish_charts_applies_palette_then_harden() -> None:
    charts = [
        {
            "id": "cht_01",
            "type": "horizontal_bar",
            "caption": "Выручка",
            "html": _HBAR,
        }
    ]
    out = polish_charts(charts, palette_id="atelier")
    html = out[0]["html"]
    up = html.upper()
    assert "#3F5210" in up or "#5A6E28" in up or "#7A8F45" in up
    assert "#023E8A" not in up
    m = re.search(r'height="(\d+)"', html)
    assert m and int(m.group(1)) < 560
    # ghost ocean fill gone
    assert "0.18" not in html or "backgroundColor:'#" in html


def test_apply_palette_alone_keeps_low_alpha_problem() -> None:
    """Document why harden must run after palette remap."""
    remapped = apply_palette_to_html(_HBAR, "atelier")
    # Soft area/grid remap keeps low alpha — still ghostly without harden.
    assert re.search(r"rgba\([^)]*,\s*0\.(1|2)\d*\)", remapped)
