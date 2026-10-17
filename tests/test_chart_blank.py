"""P1: reject empty mount / broken fragment."""

from pathlib import Path

import pytest

from case3.charts import render_chart_png


def test_reject_empty_fragment_png(tmp_path: Path):
    pytest.importorskip("playwright")
    chart = {
        "id": "cht_empty",
        "type": "kpi",
        "caption": "Empty",
        "html": "<div></div><script>window.__CASE3_CHART_READY=true;</script>",
        "width": r"0.85\textwidth",
    }
    dest = tmp_path / "empty.png"
    try:
        render_chart_png(chart, dest, work_dir=tmp_path / "work")
        pytest.fail("expected blank chart to raise")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "executable" in msg or "chromium" in msg or "browser" in msg:
            pytest.skip(f"chromium not installed: {exc}")
        assert "blank" in msg or "empty" in msg


def test_mount_survives_stray_close_div(tmp_path: Path):
    pytest.importorskip("playwright")
    html = (
        "</div><canvas id='c1' width='900' height='480'></canvas>"
        "<script>"
        "new Chart(document.getElementById('c1'),{type:'bar',"
        "data:{labels:['A','B'],datasets:[{data:[3,7],backgroundColor:'#0b5fff'}]},"
        "options:{}});"
        "window.__CASE3_CHART_READY=true;"
        "</script>"
    )
    chart = {
        "id": "cht_break",
        "type": "bar",
        "caption": "Break",
        "html": html,
        "width": r"0.85\textwidth",
    }
    dest = tmp_path / "break.png"
    try:
        render_chart_png(chart, dest, work_dir=tmp_path / "work")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "executable" in msg or "chromium" in msg or "browser" in msg:
            pytest.skip(f"chromium not installed: {exc}")
        raise
    assert dest.read_bytes().startswith(b"\x89PNG")
    assert dest.stat().st_size > 800
