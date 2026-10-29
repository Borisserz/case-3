"""Scatter points must be large enough to read in print + Liber draft."""

from __future__ import annotations

from case3.chart_types_coerce import apply_type_to_chart, harden_chart_html


def test_harden_scatter_injects_large_point_radius() -> None:
    html = (
        "<canvas id='c'></canvas><script>"
        "new Chart(c,{type:'scatter',data:{datasets:["
        "{label:'A',data:[{x:1,y:2},{x:2,y:4}],backgroundColor:'#0077BB'}"
        "]},options:{animation:false}});"
        "</script>"
    )
    out = harden_chart_html(html, "scatter")
    assert "pointRadius:10" in out or "pointRadius: 10" in out
    assert "pointHoverRadius:14" in out or "pointHoverRadius: 14" in out


def test_harden_scatter_bumps_tiny_radius() -> None:
    html = (
        "datasets:[{pointRadius:3,pointHoverRadius:4,data:[{x:0,y:1}],"
        "backgroundColor:'#0077BB'}]"
    )
    out = harden_chart_html(html, "scatter")
    assert "pointRadius:10" in out
    assert "pointHoverRadius:14" in out


def test_apply_type_scatter_gets_large_points() -> None:
    chart = {
        "id": "cht_01",
        "type": "bar",
        "html": (
            "<canvas id='c'></canvas><script>"
            "new Chart(c,{type:'bar',data:{labels:['A','B'],datasets:["
            "{label:'N',data:[12,28],backgroundColor:'#0077BB'}]},"
            "options:{animation:false}});"
            "</script>"
        ),
    }
    out = apply_type_to_chart(chart, "scatter")
    html = out["html"]
    assert "scatter" in html.lower()
    assert "pointRadius:10" in html
