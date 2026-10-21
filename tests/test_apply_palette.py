"""Local palette remap must recolor Chart.js HTML without touching data."""

from __future__ import annotations

from case3.chart_style import _PALETTES, apply_palette_to_html


def test_apply_palette_replaces_hex_with_ocean_inks() -> None:
    html = (
        "<canvas id='c'></canvas><script>"
        "new Chart(c,{type:'bar',data:{labels:['A'],datasets:["
        "{label:'X',data:[1],backgroundColor:'#E85D04',borderColor:'#0F3D3E'}"
        "]},options:{scales:{y:{grid:{color:'rgba(15,61,62,0.08)'}}}}});"
        "</script>"
    )
    out = apply_palette_to_html(html, "ocean")
    # Vivid ocean (2026-10-21) — not soft #1A5F9E ladder
    assert "#0B4F8C" in out.upper() or "#1E8AD4" in out.upper()
    assert "data:[1]" in out
    assert "labels:['A']" in out
    assert "#E85D04" not in out


def test_apply_palette_noop_for_auto() -> None:
    html = "backgroundColor:'#E85D04'"
    assert apply_palette_to_html(html, "auto") == html


def test_atelier_palette_is_vivid_olive() -> None:
    html = (
        "backgroundColor:'#111111';"
        "backgroundColor:'#888888';"
        "backgroundColor:'#CCCCCC'"
    )
    out = apply_palette_to_html(html, "atelier")
    up = out.upper()
    assert "#2E4208" in up
    assert "#7A9A28" in up or "#B8D45A" in up or "#4F6B14" in up
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


def test_vivid_palettes_use_punchy_area_alpha() -> None:
    """Print≈preview: area fills ~0.34, not washed 0.16."""
    for pid in ("editorial", "ocean", "sunset", "atelier"):
        area = str(_PALETTES[pid]["area"])
        assert "0.34" in area, pid
        assert _PALETTES[pid]["primary"].startswith("#")
