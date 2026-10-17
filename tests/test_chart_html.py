import pytest

from case3.chart_html import ChartHtmlError, sanitize_chart_html, wrap_chart_page


def test_sanitize_keeps_inline_script():
    html = '<canvas id="c"></canvas><script>window.__CASE3_CHART_READY=true;</script>'
    out = sanitize_chart_html(html)
    assert "<script>" in out
    assert "canvas" in out


def test_sanitize_strips_iframe_and_cdn():
    dirty = (
        '<iframe src="https://evil"></iframe>'
        '<img src="https://cdn.example/x.png">'
        '<div class="kpi"><div class="value">12</div></div>'
        "<script>window.__CASE3_CHART_READY=true;</script>"
    )
    out = sanitize_chart_html(dirty)
    assert "iframe" not in out.lower()
    assert "https://" not in out
    assert "kpi" in out


def test_sanitize_rejects_empty():
    with pytest.raises(ChartHtmlError):
        sanitize_chart_html("   ")


def test_wrap_includes_chart_js_and_fragment():
    page = wrap_chart_page(fragment="<div>hi</div>")
    assert "chart.umd.min.js" in page
    assert "<div>hi</div>" in page
    assert "Content-Security-Policy" in page
