"""Mermaid diagram sanitize + parse (UI-only, no TeX slots)."""

from __future__ import annotations

import pytest

from case3.diagrams import DIAGRAM_TYPES, parse_diagrams, sanitize_mermaid
from case3.parse_output import parse_model_output


def test_sanitize_strips_mermaid_fence() -> None:
    raw = "```mermaid\nflowchart TD\n  A-->B\n```"
    out = sanitize_mermaid(raw)
    assert out.startswith("flowchart")
    assert "```" not in out


def test_sanitize_keeps_classdef_colors() -> None:
    raw = (
        "flowchart TD\n"
        "  A[Старт]:::start --> B{Ок?}:::decision\n"
        "  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22\n"
        "  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22\n"
    )
    out = sanitize_mermaid(raw)
    assert ":::start" in out
    assert "classDef start" in out
    assert "#dce8df" in out
    assert "#f3e6c8" in out


def test_sanitize_repairs_multi_classname_class_line() -> None:
    """LLM emits `class A,B,C start decision process` — invalid; zip 1:1."""
    raw = (
        "flowchart TD\n"
        "  A[Старт]:::start --> B{Ок?}:::decision\n"
        "  B --> C[Шаг]\n"
        "  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22\n"
        "  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22\n"
        "  classDef process fill:#eef3ef,stroke:#5a7a64,color:#1a2e22\n"
        "  class A,B,C start decision process\n"
    )
    out = sanitize_mermaid(raw)
    assert "class A,B,C start decision process" not in out
    assert "class A start" in out
    assert "class B decision" in out
    assert "class C process" in out
    assert "classDef start" in out


def test_sanitize_drops_unmappable_multi_class_line() -> None:
    raw = (
        "flowchart TD\n"
        "  A-->B\n"
        "  class A,B start decision process process process\n"
    )
    out = sanitize_mermaid(raw)
    assert "class A,B" not in out
    assert "A-->B" in out


def test_sanitize_rewrites_purple_and_strips_click() -> None:
    raw = (
        "flowchart TD\n"
        "  A[X]:::x\n"
        "  click A \"https://evil.example\"\n"
        "  classDef x fill:#7c3aed,stroke:#a855f7,color:#fff\n"
    )
    out = sanitize_mermaid(raw)
    assert "click" not in out.lower()
    assert "#7c3aed" not in out.lower()
    assert "#a855f7" not in out.lower()
    assert "#dce8df" in out or "#6b8f76" in out


def test_sanitize_rejects_empty() -> None:
    with pytest.raises(ValueError):
        sanitize_mermaid("   ")


def test_parse_diagrams_accepts_flowchart() -> None:
    items = parse_diagrams(
        [
            {
                "id": "dia_01",
                "title": "Процесс",
                "type": "flowchart",
                "mermaid": "flowchart TD\n  A[Start] --> B[End]",
            }
        ],
        max_diagrams=2,
    )
    assert len(items) == 1
    assert items[0]["id"] == "dia_01"
    assert items[0]["type"] == "flowchart"
    assert "flowchart TD" in items[0]["mermaid"]


def test_parse_diagrams_drops_unknown_type() -> None:
    items = parse_diagrams(
        [{"id": "dia_01", "title": "X", "type": "pie", "mermaid": "pie\n  \"A\": 1"}],
        max_diagrams=2,
    )
    assert items == []


def test_parse_diagrams_respects_cap() -> None:
    raw = [
        {
            "id": f"dia_0{i}",
            "title": f"T{i}",
            "type": "flowchart",
            "mermaid": f"flowchart TD\n  A{i}-->B{i}",
        }
        for i in range(1, 5)
    ]
    items = parse_diagrams(raw, max_diagrams=2)
    assert len(items) == 2
    assert {d["id"] for d in items} == {"dia_01", "dia_02"}


def test_parse_diagrams_zero_cap() -> None:
    assert (
        parse_diagrams(
            [
                {
                    "id": "dia_01",
                    "title": "X",
                    "type": "flowchart",
                    "mermaid": "flowchart TD\nA-->B",
                }
            ],
            max_diagrams=0,
        )
        == []
    )


def test_parse_diagrams_drops_bad_id() -> None:
    items = parse_diagrams(
        [
            {
                "id": "DIA-01",
                "title": "X",
                "type": "flowchart",
                "mermaid": "flowchart TD\nA-->B",
            }
        ],
        max_diagrams=2,
    )
    assert items == []


def test_diagram_types_whitelist() -> None:
    assert "flowchart" in DIAGRAM_TYPES
    assert "pie" not in DIAGRAM_TYPES


def test_parse_normalizes_graph_header_to_flowchart() -> None:
    items = parse_diagrams(
        [
            {
                "id": "dia_01",
                "title": "Поток",
                "type": "flowchart",
                "mermaid": "graph TD\n  A[Шаг1] --> B[Шаг2]",
            }
        ],
        max_diagrams=2,
    )
    assert len(items) == 1
    assert items[0]["mermaid"].startswith("flowchart")


def test_parse_drops_type_header_mismatch() -> None:
    items = parse_diagrams(
        [
            {
                "id": "dia_01",
                "title": "X",
                "type": "flowchart",
                "mermaid": "sequenceDiagram\n  A->>B: hi",
            }
        ],
        max_diagrams=2,
    )
    assert items == []


def test_parse_accepts_sequence_with_sequenceDiagram_header() -> None:
    items = parse_diagrams(
        [
            {
                "id": "dia_02",
                "title": "Диалог",
                "type": "sequence",
                "mermaid": "sequenceDiagram\n  Alice->>Bob: ping",
            }
        ],
        max_diagrams=2,
    )
    assert len(items) == 1
    assert items[0]["type"] == "sequence"


def test_parse_diagrams_reports_drops() -> None:
    kept, drops = parse_diagrams(
        [
            {
                "id": "dia_01",
                "title": "Ok",
                "type": "flowchart",
                "mermaid": "flowchart TD\nA-->B",
            },
            {
                "id": "dia_02",
                "title": "Bad",
                "type": "flowchart",
                "mermaid": "sequenceDiagram\nA->>B: x",
            },
        ],
        max_diagrams=3,
        with_drops=True,
    )
    assert len(kept) == 1
    assert len(drops) == 1
    assert drops[0]["id"] == "dia_02"
    assert "header" in drops[0]["reason"].lower() or "mismatch" in drops[0]["reason"].lower()


def test_intent_nudges_diagrams_when_budget() -> None:
    from case3.api import build_intent_from_ui

    intent = build_intent_from_ui(
        chat="отчёт",
        chart_types=[],
        max_charts=0,
        max_images=0,
        max_diagrams=2,
        forbid_charts=True,
        forbid_images=True,
    )
    low = intent.lower()
    assert "mermaid" in low or "схем" in low
    # Forbidding charts must NOT forbid Liber Mermaid schemas
    assert "без графиков и диаграмм" not in low
    assert "charts" in low or "html-график" in low or "график" in low


def test_parse_model_output_returns_diagrams() -> None:
    raw = r'''```json
{
  "figures": [],
  "charts": [],
  "diagrams": [
    {
      "id": "dia_01",
      "title": "Согласование",
      "type": "flowchart",
      "mermaid": "flowchart TD\n  A[Заявка] --> B[Готово]"
    }
  ]
}
```
```latex
\documentclass{article}
\begin{document}
Hello.
\end{document}
```
'''
    tex, figs, charts, diagrams, _drops = parse_model_output(
        raw, max_images=0, max_charts=0, max_diagrams=2
    )
    assert figs == []
    assert charts == []
    assert len(diagrams) == 1
    assert diagrams[0]["id"] == "dia_01"
    assert "%CASE3_DIAG" not in tex
    assert r"\documentclass" in tex


def test_parse_model_output_diagram_id_collision_with_chart() -> None:
    raw = r'''```json
{
  "figures": [],
  "charts": [
    {
      "id": "cht_01",
      "type": "bar",
      "caption": "C",
      "html": "<canvas id=\"c1\" width=\"1100\" height=\"560\"></canvas><script>new Chart(document.getElementById('c1'),{type:'bar',data:{labels:['a'],datasets:[{data:[1],backgroundColor:'#D62828'}]},options:{animation:false}});window.__CASE3_CHART_READY=true;</script>"
    }
  ],
  "diagrams": [
    {
      "id": "cht_01",
      "title": "Clash",
      "type": "flowchart",
      "mermaid": "flowchart TD\nA-->B"
    }
  ]
}
```
```latex
\documentclass{article}
\begin{document}
%CASE3_CHART:cht_01%
\end{document}
```
'''
    from case3.parse_output import ParseError

    with pytest.raises(ParseError, match="collision"):
        parse_model_output(raw, max_images=0, max_charts=1, max_diagrams=2)
