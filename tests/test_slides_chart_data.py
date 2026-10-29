"""Extract Chart.js series for native PPTX charts."""

from __future__ import annotations

from case3.slides_chart_data import (
    attach_series_ir,
    ensure_deck_charts,
    extract_chart_series,
    series_from_figures_json,
)


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


def test_attach_series_ir_persists_on_chart() -> None:
    chart = {"id": "cht_01", "type": "bar", "html": BAR_HTML}
    ir = attach_series_ir(chart)
    assert ir is not None
    assert chart["series"]["categories"] == ["Офлайн", "Сайт", "Маркетплейсы"]
    assert chart["series"]["series"][0]["values"] == [48.0, 35.0, 17.0]


def test_series_from_figures_prefers_stored() -> None:
    stored = {
        "type": "line",
        "categories": ["A", "B"],
        "series": [{"name": "X", "values": [1.0, 2.0]}],
    }
    fj = {
        "charts": [
            {
                "id": "cht_01",
                "type": "bar",
                "html": "<script>broken</script>",
                "series": stored,
            }
        ]
    }
    ir = series_from_figures_json(fj, "cht_01")
    assert ir == stored


def test_ensure_deck_injects_chart_hero_when_missing() -> None:
    deck = {
        "slides": [
            {"id": "s0", "layout": "title", "title": "Hi"},
            {"id": "s1", "layout": "bullets", "title": "Notes", "bullets": ["a"]},
        ]
    }
    series_by_id = {
        "cht_01": {
            "type": "bar",
            "categories": ["Q1", "Q2"],
            "series": [{"name": "Rev", "values": [1.0, 2.0]}],
        }
    }
    assert bool(ensure_deck_charts(deck, series_by_id)) is True
    ids = [
        str(s.get("chart_id") or s.get("media_id") or "")
        for s in deck["slides"]
        if isinstance(s, dict)
    ]
    assert "cht_01" in ids
    layouts = [str(s.get("layout")) for s in deck["slides"] if isinstance(s, dict)]
    assert "chart_hero" in layouts


def test_ensure_deck_noop_when_chart_present() -> None:
    deck = {
        "slides": [
            {
                "id": "s1",
                "layout": "chart_hero",
                "title": "Rev",
                "chart_id": "cht_01",
            }
        ]
    }
    series_by_id = {
        "cht_01": {
            "type": "bar",
            "categories": ["Q1"],
            "series": [{"name": "Rev", "values": [1.0]}],
        }
    }
    assert bool(ensure_deck_charts(deck, series_by_id)) is False


def test_ensure_deck_charts_injects_missing_ids() -> None:
    """If IR kept one chart but run has two eligible — inject the missing one."""
    deck = {
        "slides": [
            {"id": "s0", "layout": "title", "title": "Hi"},
            {
                "id": "s1",
                "layout": "chart_hero",
                "title": "Only one",
                "chart_id": "cht_01",
            },
            {"id": "s2", "layout": "closing", "title": "Bye"},
        ]
    }
    series_by_id = {
        "cht_01": {
            "type": "bar",
            "categories": ["Q1"],
            "series": [{"name": "A", "values": [1.0]}],
        },
        "cht_02": {
            "type": "donut",
            "categories": ["X", "Y"],
            "series": [{"name": "Series", "values": [60.0, 40.0]}],
        },
    }
    injected = ensure_deck_charts(deck, series_by_id)
    assert injected == ["cht_02"]
    ids = {
        str(s.get("chart_id") or s.get("media_id") or "")
        for s in deck["slides"]
        if isinstance(s, dict)
    }
    assert "cht_01" in ids and "cht_02" in ids


def test_attach_donut_renames_anonymous_series() -> None:
    html = """
    <script>new Chart(c,{type:'doughnut',data:{labels:['A','B'],
    datasets:[{data:[60,40]}]},options:{}});</script>
    """
    chart = {"id": "cht_02", "type": "donut", "html": html, "caption": "Бюджет"}
    ir = attach_series_ir(chart)
    assert ir is not None
    assert ir["series"][0]["name"] == "Бюджет"
