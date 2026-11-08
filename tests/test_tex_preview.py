"""TeX → chat preview blocks."""

from __future__ import annotations

from pathlib import Path

from case3.tex_preview import build_report_preview, tex_to_preview_blocks

FIXTURE = Path(__file__).parent / "fixtures" / "preview_sample.tex"


def test_tex_to_preview_extracts_structure() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    data = tex_to_preview_blocks(tex)
    assert data["title"] == "Демография 2019–2023"
    types = [b["type"] for b in data["blocks"]]
    assert "heading" in types
    assert "paragraph" in types
    assert "table" in types
    assert "figure" in types
    headings = [b for b in data["blocks"] if b["type"] == "heading"]
    assert headings[0]["level"] == 1
    assert "Общая" in headings[0]["text"]
    table = next(b for b in data["blocks"] if b["type"] == "table")
    assert table["headers"] == ["Показатель", "Значение", "Комментарий"]
    assert len(table["rows"]) == 2
    assert "72 000" in table["rows"][1][1] or "72000" in table["rows"][1][1].replace(
        " ", ""
    )
    figs = [b for b in data["blocks"] if b["type"] == "figure"]
    assert figs[0]["id"] == "cht_01"
    assert figs[0]["caption"] == "Численность населения"


def test_build_report_preview_attaches_urls_and_captions() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    media = {
        "cht_01": {"ok": True, "kind": "chart"},
        "fig_01": {"ok": True, "kind": "figure"},
    }
    figures_json = {
        "charts": [{"id": "cht_01", "caption": "from json"}],
        "figures": [{"id": "fig_01", "caption": "Схема из JSON"}],
    }
    preview = build_report_preview(
        tex,
        run_id="demo_run",
        media_status=media,
        figures_json=figures_json,
    )
    figs = [b for b in preview["blocks"] if b["type"] == "figure"]
    assert figs[0]["url"] == "/api/runs/demo_run/figures/cht_01.png"
    assert figs[0]["kind"] == "chart"
    assert figs[0].get("pdfPage") == 1
    # empty TeX caption filled from figures.json
    fig01 = next(b for b in figs if b["id"] == "fig_01")
    assert fig01["caption"] == "Схема из JSON"
    assert fig01["kind"] == "image"
    assert fig01.get("pdfPage") == 1


def test_failed_media_omits_url() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    preview = build_report_preview(
        tex,
        run_id="x",
        media_status={"cht_01": {"ok": False, "kind": "chart"}},
        figures_json={},
    )
    fig = next(b for b in preview["blocks"] if b.get("id") == "cht_01")
    assert not fig.get("url")


def test_preview_preserves_bold_and_italic() -> None:
    """C2: \\textbf / \\textit survive as HTML strong/em in paragraph blocks."""
    tex = r"""
\documentclass{article}
\begin{document}
\title{T}
\section{S}
Текст с \textbf{важной} и \textit{курсивной} деталью.
\end{document}
"""
    data = tex_to_preview_blocks(tex)
    paras = [b for b in data["blocks"] if b["type"] == "paragraph"]
    assert paras, "expected a paragraph"
    html = paras[0].get("html") or ""
    assert "<strong>" in html and "важной" in html
    assert "<em>" in html and "курсивной" in html
    # plain text still available without tags
    assert "важной" in paras[0]["text"]
    assert "<strong>" not in paras[0]["text"]


def test_preview_extracts_itemize_and_enumerate() -> None:
    """C1: itemize/enumerate → list blocks with items."""
    tex = r"""
\documentclass{article}
\begin{document}
\section{Итоги}
\begin{itemize}
\item Первый пункт с \textbf{акцентом}
\item Второй
\end{itemize}
\begin{enumerate}
\item Шаг один
\item Шаг два
\end{enumerate}
\end{document}
"""
    data = tex_to_preview_blocks(tex)
    lists = [b for b in data["blocks"] if b["type"] == "list"]
    assert len(lists) >= 2
    ul = next(b for b in lists if not b.get("ordered"))
    ol = next(b for b in lists if b.get("ordered"))
    assert len(ul["items"]) == 2
    assert "Первый" in ul["items"][0]["text"]
    assert "<strong>" in (ul["items"][0].get("html") or "")
    assert len(ol["items"]) == 2
    assert "Шаг один" in ol["items"][0]["text"]


def test_preview_preserves_math_formula() -> None:
    """P3: math formulas $...$ wrapped in <span class="tex-math" data-math="...">."""
    tex = r"""
\documentclass{article}
\begin{document}
Формула $E = mc^2$ и предел $\lim_{x \to 0} \frac{\sin x}{x} = 1$. Цена: \$100.
\end{document}
"""
    data = tex_to_preview_blocks(tex)
    paras = [b for b in data["blocks"] if b["type"] == "paragraph"]
    assert paras, "expected a paragraph"
    html = paras[0].get("html") or ""
    assert 'class="tex-math"' in html
    assert 'data-math="E = mc^2"' in html
    assert 'data-math="\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1"' in html
    # Escaped \$ is not converted to math
    assert "$100" in html
    # Plain text cleans up math delimiters
    assert "E = mc^2" in paras[0]["text"]
