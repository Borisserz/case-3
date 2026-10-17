import json

import pytest

from case3.parse_output import ParseError, parse_model_output

BAR_HTML = (
    '<canvas id="c1" width="800" height="400"></canvas>'
    "<script>"
    "new Chart(document.getElementById('c1'),{type:'bar',"
    "data:{labels:['2024','2025'],datasets:[{label:'clients',data:[12,28]}]}});"
    "window.__CASE3_CHART_READY=true;"
    "</script>"
)


def _raw(chart: dict) -> str:
    payload = {"figures": [], "charts": [chart]}
    return (
        "```latex\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Text\n"
        "%CASE3_CHART:cht_01%\n"
        "\\end{document}\n"
        "```\n\n"
        "```json\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n```\n"
    )


def test_parse_chart_ok():
    raw = _raw(
        {
            "id": "cht_01",
            "type": "bar",
            "caption": "Клиенты",
            "width": "0.85\\textwidth",
            "html": BAR_HTML,
        }
    )
    tex, figs, charts = parse_model_output(raw, max_images=0, max_charts=2)
    assert figs == []
    assert charts[0]["id"] == "cht_01"
    assert charts[0]["type"] == "bar"
    assert "__CASE3_CHART_READY" in charts[0]["html"]
    assert "%CASE3_CHART:cht_01%" in tex


def test_max_charts_zero_ignores_slots():
    raw = _raw(
        {
            "id": "cht_01",
            "type": "bar",
            "caption": "Клиенты",
            "width": "0.85\\textwidth",
            "html": BAR_HTML,
        }
    )
    _, figs, charts = parse_model_output(raw, max_images=0, max_charts=0)
    assert figs == []
    assert charts == []


def test_unknown_type_soft_strips_slot():
    raw = _raw(
        {
            "id": "cht_01",
            "type": "spider",
            "caption": "X",
            "width": "0.85\\textwidth",
            "html": BAR_HTML,
        }
    )
    tex, figs, charts = parse_model_output(raw, max_images=0, max_charts=2)
    assert figs == []
    assert charts == []
    assert "%CASE3_CHART:" not in tex


def test_id_collision_figure_chart():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
%CASE3_FIG:same%
%CASE3_CHART:same%
\\end{document}
```

```json
{
  "figures":[{"id":"same","caption":"F","prompt":"a blue network diagram photo","width":"0.8\\\\textwidth"}],
  "charts":[{"id":"same","type":"bar","caption":"C","width":"0.8\\\\textwidth","html":"<div class='kpi'>1</div><script>window.__CASE3_CHART_READY=true;</script>"}]
}
```
"""
    with pytest.raises(ParseError, match="collision"):
        parse_model_output(raw, max_images=2, max_charts=2)
