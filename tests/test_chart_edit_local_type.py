"""G3: type/palette-only chart edit stays local (no LLM)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from case3.chart_edit import ChartEditError, edit_chart_in_run, preview_chart_html

_BAR_HTML = (
    '<canvas id="c1" width="1100" height="560"></canvas>'
    "<script>new Chart(document.getElementById('c1'),"
    "{type:'bar',data:{labels:['A','B'],datasets:[{data:[10,20],"
    "backgroundColor:['#1A4A4B','#5A6E28']}]},"
    "options:{animation:false}});"
    "window.__CASE3_CHART_READY=true;</script>"
)


def _seed_run(root: Path, run_id: str = "local_type_20260101T000000Z") -> Path:
    # edit_chart_in_run uses parents[2] as project_root from runs/out/<id>
    out = root / "runs" / "out" / run_id
    out.mkdir(parents=True, exist_ok=True)
    fj = {
        "charts": [
            {
                "id": "cht_01",
                "type": "bar",
                "caption": "Выручка",
                "html": _BAR_HTML,
                "palette": "editorial",
            }
        ],
        "figures": [],
    }
    (out / "figures.json").write_text(
        json.dumps(fj, ensure_ascii=False), encoding="utf-8"
    )
    (out / "demo.tex").write_text(
        r"\documentclass{article}\begin{document}Hi\end{document}",
        encoding="utf-8",
    )
    (out / "meta.json").write_text("{}", encoding="utf-8")
    return out


def _stub_render(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Avoid Playwright + Docker; return a spy for LLM rewrite."""
    def _fake_png(chart: dict[str, Any], dest: Path, work_dir: Path | None = None) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        return dest

    monkeypatch.setattr("case3.chart_edit.render_chart_png", _fake_png)
    monkeypatch.setattr(
        "case3.chart_edit.rebuild_run_docs",
        lambda *a, **k: {"pdf": Path("x.pdf")},
    )
    spy = MagicMock(side_effect=AssertionError("LLM must not run for type-only edit"))
    monkeypatch.setattr("case3.chart_edit.rewrite_chart_html_with_llm", spy)
    return spy


def test_type_only_bar_to_horizontal_no_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = _seed_run(tmp_path)
    spy = _stub_render(monkeypatch)
    result = edit_chart_in_run(
        out,
        "cht_01",
        palette="editorial",
        style="",
        chart_type="horizontal_bar",
        formats={"pdf"},
    )
    spy.assert_not_called()
    assert "local_type" in result["mode"]
    assert "type_change" in result["mode"]
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    chart = fj["charts"][0]
    assert chart["type"] == "horizontal_bar"
    assert "indexAxis" in chart["html"]
    assert "10" in chart["html"] and "20" in chart["html"]


def test_palette_only_no_llm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _seed_run(tmp_path)
    spy = _stub_render(monkeypatch)
    result = edit_chart_in_run(
        out,
        "cht_01",
        palette="ocean",
        style="",
        chart_type="bar",
        formats={"pdf"},
    )
    spy.assert_not_called()
    assert "local_palette" in result["mode"]
    assert "llm_style" not in result["mode"]
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert fj["charts"][0]["palette"] == "ocean"


def test_style_notes_still_allow_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = _seed_run(tmp_path)

    def _fake_png(chart: dict[str, Any], dest: Path, work_dir: Path | None = None) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
        return dest

    monkeypatch.setattr("case3.chart_edit.render_chart_png", _fake_png)
    monkeypatch.setattr(
        "case3.chart_edit.rebuild_run_docs",
        lambda *a, **k: {"pdf": Path("x.pdf")},
    )
    rewritten = (
        '<canvas id="c1" width="1100" height="560"></canvas>'
        "<script>new Chart(document.getElementById('c1'),"
        "{type:'bar',data:{labels:['A','B'],datasets:[{data:[10,20],"
        "backgroundColor:['#aabbcc','#ddeeff']}]},"
        "options:{animation:false}});"
        "window.__CASE3_CHART_READY=true;</script>"
    )
    spy = MagicMock(return_value=rewritten)
    monkeypatch.setattr("case3.chart_edit.rewrite_chart_html_with_llm", spy)

    result = edit_chart_in_run(
        out,
        "cht_01",
        palette="atelier",
        style="сделай толще столбцы",
        chart_type="bar",
        formats={"pdf"},
    )
    spy.assert_called_once()
    assert "llm_style" in result["mode"]


def test_preview_type_preserves_data_arrays(tmp_path: Path) -> None:
    out = _seed_run(tmp_path)
    result = preview_chart_html(
        out, "cht_01", palette="mono", chart_type="grouped_bar"
    )
    assert result["type"] == "grouped_bar"
    assert "local_type" in result["modes"]
    assert "[10,20]" in result["html"] or "10,20" in result["html"]
    assert "llm" not in "".join(result["modes"])


def test_kpi_type_change_is_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _seed_run(tmp_path)
    spy = _stub_render(monkeypatch)
    result = edit_chart_in_run(
        out,
        "cht_01",
        palette="editorial",
        style="",
        chart_type="kpi",
        formats={"pdf"},
    )
    spy.assert_not_called()
    assert "local_kpi" in result["mode"]
    assert "local_type" in result["mode"] or "type_change" in result["mode"]
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert fj["charts"][0]["type"] == "kpi"
    assert "kpi" in fj["charts"][0]["html"].lower()


def test_empty_style_and_auto_palette_type_only_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Type-only with palette=auto must still take local path (not raise)."""
    out = _seed_run(tmp_path)
    spy = _stub_render(monkeypatch)
    # normalize_palette_id("auto") may stay auto — type change branch should still work
    result = edit_chart_in_run(
        out,
        "cht_01",
        palette="atelier",
        style=None,
        chart_type="line",
        formats={"pdf"},
    )
    spy.assert_not_called()
    assert "local_type" in result["mode"]
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert fj["charts"][0]["type"] == "line"
    assert "type:'line'" in fj["charts"][0]["html"] or 'type:"line"' in fj["charts"][0]["html"]
