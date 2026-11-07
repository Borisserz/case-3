"""Tests for PPTX native diagram shapes, layout, and fail-safe fallback."""

from __future__ import annotations

import pytest


def test_parse_mermaid_flowchart_td():
    from case3.slides_pptx_diagrams import parse_mermaid_flowchart

    mermaid = """flowchart TD
    A([Начало]) --> B[Сбор метрик]
    B --> C{Критерии ок?}
    C -->|Да| D[Формирование отчёта]
    C -->|Нет| E[План корректировок]
    class A start
    class C decision
    class D ok
    class E warn
    """
    g = parse_mermaid_flowchart(mermaid)
    assert g is not None
    assert g.direction == "TD"
    assert len(g.nodes) == 5
    assert g.nodes["A"].shape == "capsule"
    assert g.nodes["A"].role == "start"
    assert g.nodes["A"].label == "Начало"
    assert g.nodes["B"].shape == "rect"
    assert g.nodes["C"].shape == "diamond"
    assert g.nodes["C"].role == "decision"
    assert len(g.edges) == 4
    yes_edge = next(e for e in g.edges if e.src == "C" and e.dst == "D")
    assert yes_edge.label == "Да"


def test_parse_mermaid_rejects_non_flowchart():
    from case3.slides_pptx_diagrams import parse_mermaid_flowchart

    assert parse_mermaid_flowchart("sequenceDiagram\nAlice->>Bob: Hello") is None
    assert parse_mermaid_flowchart("mindmap\n  root((Idea))") is None
    assert parse_mermaid_flowchart("timeline\n  title 2026") is None
    assert parse_mermaid_flowchart("stateDiagram-v2\n  [*] --> State1") is None


def test_parse_mermaid_flowchart_lr_and_classes():
    from case3.slides_pptx_diagrams import parse_mermaid_flowchart

    mermaid = """flowchart LR
    In[(БД Заказов)] --> Process[Обработка]:::process
    Process --> Out([Успешно отправлено]):::ok
    """
    g = parse_mermaid_flowchart(mermaid)
    assert g is not None
    assert g.direction == "LR"
    assert g.nodes["In"].shape == "cylinder"
    assert g.nodes["In"].role == "data"
    assert g.nodes["Process"].role == "process"
    assert g.nodes["Out"].shape == "capsule"
    assert g.nodes["Out"].role == "ok"

