"""A one-point chart is a dash in an empty frame. Drop it, keep a real comparison."""

from case3.chart_coerce import drop_stick_charts
from case3.chart_type_fit import chart_is_stick

_ONE = (
    "<canvas id='c1'></canvas><script>new Chart(c,{type:'bar',"
    "data:{labels:['Итого'],datasets:[{data:[5631052]}]},"
    "options:{animation:false}});</script>"
)
_TWO = (
    "<canvas id='c1'></canvas><script>new Chart(c,{type:'bar',"
    "data:{labels:['Консолидированный','Республиканский'],datasets:[{data:[33,36]}]},"
    "options:{animation:false}});</script>"
)
_STUB = (
    "<canvas id='c1' width='1100' height='560'></canvas><script>"
    "/* full Chart.js */window.__CASE3_CHART_READY=true;</script>"
)
_KPI = "<div class='kpi'><div class='value'>36%</div><div class='label'>доля</div></div>"


def test_one_bar_and_empty_stub_are_sticks() -> None:
    assert chart_is_stick({"type": "bar", "html": _ONE})
    assert chart_is_stick({"type": "bar", "html": _STUB})
    assert not chart_is_stick({"type": "bar", "html": _TWO})
    assert not chart_is_stick({"type": "kpi", "html": _KPI})


def test_drop_stick_removes_the_slot_and_keeps_the_comparison() -> None:
    tex = (
        "\\section{Сводка}\n"
        "Текст.\n"
        "%CASE3_CHART:cht_01%\n"
        "%CASE3_CHART:cht_02%\n"
        "Дальше.\n"
    )
    charts = [
        {"id": "cht_01", "type": "bar", "html": _ONE},
        {"id": "cht_02", "type": "bar", "html": _TWO},
    ]
    out, kept, dropped = drop_stick_charts(tex, charts)
    assert dropped == ["cht_01"]
    assert [c["id"] for c in kept] == ["cht_02"]
    assert "%CASE3_CHART:cht_01%" not in out
    assert "%CASE3_CHART:cht_02%" in out
    assert "Дальше." in out
