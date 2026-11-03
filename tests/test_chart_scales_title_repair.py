"""LLM often emits scales:{y:{…},title:{…}} — Chart.js throws; READY never fires."""

from case3.chart_html import sanitize_chart_html


def _compact(s: str) -> str:
    return "".join(s.split())


def test_orphan_y_scale_title_nested() -> None:
    raw = (
        "<canvas id='c1'></canvas><script>"
        "new Chart(document.getElementById('c1'),{type:'bar',data:{labels:['A','B'],"
        "datasets:[{data:[1,2],backgroundColor:['#004D47','#0077BB']}]},"
        "options:{plugins:{legend:{display:false}},"
        "scales:{y:{beginAtZero:true},title:{display:true,text:'Минуты'}},"
        "animation:false}});"
        "</script>"
    )
    compact = _compact(sanitize_chart_html(raw))
    assert "y:{beginAtZero:true,title:{display:true,text:'Минуты'}}" in compact
    assert "scales:{y:{beginAtZero:true},title:" not in compact


def test_orphan_x_scale_title_nested() -> None:
    raw = (
        "<canvas id='c1'></canvas><script>"
        "new Chart(document.getElementById('c1'),{type:'bar',data:{labels:['A'],"
        "datasets:[{data:[1]}]},"
        "options:{indexAxis:'y',scales:{x:{beginAtZero:true},title:{display:true,text:'X'}},"
        "animation:false}});"
        "</script>"
    )
    compact = _compact(sanitize_chart_html(raw))
    assert "x:{beginAtZero:true,title:{display:true,text:'X'}}" in compact


def test_chart_timeout_floor_at_least_45() -> None:
    import os
    from case3.charts import chart_timeout_s

    old = os.environ.get("CASE3_CHART_TIMEOUT_S")
    try:
        os.environ["CASE3_CHART_TIMEOUT_S"] = "15"
        assert chart_timeout_s() >= 45.0
    finally:
        if old is None:
            os.environ.pop("CASE3_CHART_TIMEOUT_S", None)
        else:
            os.environ["CASE3_CHART_TIMEOUT_S"] = old
