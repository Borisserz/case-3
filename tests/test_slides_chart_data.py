"""Extract Chart.js series for native PPTX charts."""

from __future__ import annotations

from case3.slides_chart_data import extract_chart_series


LINE_HTML = """
<canvas id="c1"></canvas><script>new Chart(document.getElementById('c1'),{
type:'line',data:{labels:['Q3 2025','Q3 2026'],datasets:[{label:'Выручка',data:[4.1,4.8],
borderColor:'#2E4208'}]},options:{}});</script>
"""

BAR_HTML = """
<script>new Chart(document.getElementById('c2'),{type:'bar',data:{
labels:['Офлайн','Сайт','Маркетплейсы'],
datasets:[{label:'Доля',data:[48,35,17],backgroundColor:['#2E4208','#4F6B14','#7A9A28']}]
},options:{}});</script>
"""


def test_extract_line() -> None:
    ir = extract_chart_series(LINE_HTML, chart_type="line")
    assert ir is not None
    assert ir["type"] == "line"
    assert ir["categories"] == ["Q3 2025", "Q3 2026"]
    assert ir["series"][0]["values"] == [4.1, 4.8]


def test_extract_bar() -> None:
    ir = extract_chart_series(BAR_HTML, chart_type="bar")
    assert ir is not None
    assert ir["type"] == "bar"
    assert len(ir["categories"]) == 3
    assert ir["series"][0]["values"] == [48.0, 35.0, 17.0]


def test_extract_empty() -> None:
    assert extract_chart_series("", chart_type="bar") is None
    assert extract_chart_series("<div/>", chart_type="kpi") is None
