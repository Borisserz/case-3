"""Local palette remap must recolor Chart.js HTML without touching data."""

from __future__ import annotations

from case3.chart_style import apply_palette_to_html


def test_apply_palette_replaces_hex_with_ocean_inks() -> None:
    html = (
        "<canvas id='c'></canvas><script>"
        "new Chart(c,{type:'bar',data:{labels:['A'],datasets:["
        "{label:'X',data:[1],backgroundColor:'#E85D04',borderColor:'#0F3D3E'}"
        "]},options:{scales:{y:{grid:{color:'rgba(15,61,62,0.08)'}}}}});"
        "</script>"
    )
    out = apply_palette_to_html(html, "ocean")
    assert "#1A5F9E" in out.upper() or "#2B8FC4" in out.upper()
    assert "data:[1]" in out
    assert "labels:['A']" in out
    assert "#E85D04" not in out


def test_apply_palette_noop_for_auto() -> None:
    html = "backgroundColor:'#E85D04'"
    assert apply_palette_to_html(html, "auto") == html


def test_atelier_palette_is_soft_olive_mono() -> None:
    html = (
        "backgroundColor:'#111111';"
        "backgroundColor:'#888888';"
        "backgroundColor:'#CCCCCC'"
    )
    out = apply_palette_to_html(html, "atelier")
    up = out.upper()
    assert "#3F5210" in up
    assert "#7A8F45" in up or "#A8B87A" in up or "#5A6E28" in up
    assert "#111111" not in up


def test_atelier_keeps_white_borders_and_readable_labels() -> None:
    html = (
        "backgroundColor:['#111111','#444444','#888888','#CCCCCC'],"
        "borderColor:'#FFFFFF',"
        "labels:{color:'#333333'},"
        "ticks:{color:'#555555'}"
    )
    out = apply_palette_to_html(html, "atelier")
    up = out.upper()
    assert "#FFFFFF" in up
    assert "#6A7160" in up
    assert "#333333" not in up
