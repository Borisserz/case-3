from case3.inject import inject_figures, inject_media


def test_inject_sanitizes_width():
    tex = "\\documentclass{article}\nA\n%CASE3_FIG:fig_01%\nB\n"
    figs = [
        {
            "id": "fig_01",
            "caption": "Cap_1 %",
            "prompt": "x",
            "width": r"0.85\textwidth]{hack}\write18{id}",
        }
    ]
    status = {"fig_01": {"ok": True}}
    out = inject_figures(tex, figs, status)
    assert r"width=0.85\textwidth" in out
    assert r"\write18" not in out
    assert r"Cap\_1 \%" in out
    assert r"\usepackage{float}" in out


def test_inject_chart_slot():
    tex = "\\documentclass{article}\nA\n%CASE3_CHART:cht_01%\nB\n"
    charts = [
        {
            "id": "cht_01",
            "type": "bar",
            "caption": "График",
            "html": "<div></div>",
            "width": r"0.9\textwidth",
        }
    ]
    status = {"cht_01": {"ok": True}}
    out = inject_media(tex, [], charts, status)
    assert r"includegraphics[width=0.9\textwidth]{figures/cht_01.png}" in out
    assert r"\label{chart:cht_01}" in out
    assert r"\usepackage{graphicx}" in out
    assert r"\usepackage{float}" in out


def test_inject_failed_chart_stripped():
    tex = "A\n%CASE3_CHART:cht_01%\nB\n"
    charts = [{"id": "cht_01", "type": "bar", "caption": "X", "html": "x", "width": r"0.85\textwidth"}]
    out = inject_media(tex, [], charts, {"cht_01": {"ok": False}})
    assert "CASE3_CHART" not in out
    assert "includegraphics" not in out
    assert out.strip() == "A\nB"
