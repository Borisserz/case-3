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
    assert "#023E8A" in out or "#0077B6" in out
    assert "data:[1]" in out
    assert "labels:['A']" in out
    assert "#E85D04" not in out


def test_apply_palette_noop_for_auto() -> None:
    html = "backgroundColor:'#E85D04'"
    assert apply_palette_to_html(html, "auto") == html
