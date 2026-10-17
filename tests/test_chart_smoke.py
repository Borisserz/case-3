"""Optional Playwright smoke — skip if Chromium missing."""

from pathlib import Path

import pytest

from case3.charts import render_chart_png


def test_render_bar_png(tmp_path: Path):
    pytest.importorskip("playwright")
    html = (
        '<canvas id="c1" width="800" height="400"></canvas>'
        "<script>"
        "const ctx=document.getElementById('c1');"
        "new Chart(ctx,{type:'bar',data:{labels:['A','B'],"
        "datasets:[{label:'N',data:[12,28],backgroundColor:'#0b5fff'}]},"
        "options:{animation:false,responsive:false}});"
        "window.__CASE3_CHART_READY=true;"
        "</script>"
    )
    chart = {
        "id": "cht_smoke",
        "type": "bar",
        "caption": "Smoke",
        "html": html,
        "width": r"0.85\textwidth",
    }
    dest = tmp_path / "cht_smoke.png"
    try:
        render_chart_png(chart, dest, work_dir=tmp_path / "work")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "executable" in msg or "chromium" in msg or "browser" in msg:
            pytest.skip(f"chromium not installed: {exc}")
        raise
    data = dest.read_bytes()
    assert data.startswith(b"\x89PNG")
    assert len(data) > 1000
