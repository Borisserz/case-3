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


def test_layout_computes_valid_bounds():
    from case3.slides_pptx_diagrams import compute_diagram_layout, parse_mermaid_flowchart

    mermaid = """flowchart TD
    A([Начало]) --> B[Этап 1]
    B --> C[Этап 2]
    """
    g = parse_mermaid_flowchart(mermaid)
    assert g is not None
    layout = compute_diagram_layout(g, left=1.0, top=1.0, width=6.0, height=4.0)
    assert len(layout.boxes) == 3
    for nid, box in layout.boxes.items():
        assert box.x >= 1.0 - 1e-4
        assert box.y >= 1.0 - 1e-4
        assert box.x + box.w <= 7.0 + 1e-4
        assert box.y + box.h <= 5.0 + 1e-4
    # Vertical ordering in TD: y(A) < y(B) < y(C)
    assert layout.boxes["A"].y < layout.boxes["B"].y < layout.boxes["C"].y


def test_layout_handles_cycles_and_branching():
    from case3.slides_pptx_diagrams import compute_diagram_layout, parse_mermaid_flowchart

    mermaid = """flowchart TD
    A([Старт]) --> B{Проверка}
    B -->|Ок| C([Финиш])
    B -->|Ошибка| D[Доработка]
    D --> B
    """
    g = parse_mermaid_flowchart(mermaid)
    assert g is not None
    layout = compute_diagram_layout(g, left=0.5, top=0.5, width=7.0, height=5.0)
    assert len(layout.boxes) == 4
    # All boxes within bounds
    for nid, box in layout.boxes.items():
        assert box.x >= 0.5 - 1e-4
        assert box.y >= 0.5 - 1e-4
        assert box.x + box.w <= 7.5 + 1e-4
        assert box.y + box.h <= 5.5 + 1e-4
    # B and D should have valid positions without crashing from cycle D -> B
    assert layout.boxes["A"].y < layout.boxes["B"].y


def test_add_native_diagram_success():
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches
    from case3.slides_pptx_diagrams import add_native_diagram

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    spec = {
        "id": "dia_01",
        "type": "flowchart",
        "title": "Процесс аудита",
        "mermaid": """flowchart TD
        A([Старт]) --> B[Анализ данных]
        B --> C{Соответствие?}
        C -->|Да| D([Успех])
        """,
    }
    placed = add_native_diagram(
        slide,
        spec,
        left=Inches(1),
        top=Inches(1),
        width=Inches(6),
        height=Inches(4),
        colors={"ink": "1a2e22", "paper": "ffffff"},
        palette="editorial",
    )
    assert placed is True
    # Verify shapes were created
    shape_types = []
    for s in slide.shapes:
        try:
            shape_types.append(s.auto_shape_type)
        except (ValueError, AttributeError):
            pass
    assert MSO_SHAPE.ROUNDED_RECTANGLE in shape_types
    assert MSO_SHAPE.DIAMOND in shape_types
    # Nodes + connectors + labels
    assert len(slide.shapes) >= 4


def test_add_native_diagram_fallback_on_unsupported():
    from pptx import Presentation
    from pptx.util import Inches
    from case3.slides_pptx_diagrams import add_native_diagram

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    spec = {"id": "dia_02", "type": "sequence", "mermaid": "sequenceDiagram\nA->>B: ping"}
    placed = add_native_diagram(
        slide,
        spec,
        left=Inches(1),
        top=Inches(1),
        width=Inches(5),
        height=Inches(4),
        colors={},
    )
    assert placed is False
    assert len(slide.shapes) == 0


def test_add_native_diagram_fallback_on_over_capacity():
    from pptx import Presentation
    from pptx.util import Inches
    from case3.slides_pptx_diagrams import add_native_diagram

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # 12 nodes > 10 limit
    nodes = " --> ".join([f"N{i}" for i in range(12)])
    spec = {"id": "dia_03", "type": "flowchart", "mermaid": f"flowchart TD\n{nodes}"}
    placed = add_native_diagram(
        slide,
        spec,
        left=Inches(1),
        top=Inches(1),
        width=Inches(5),
        height=Inches(4),
        colors={},
    )
    assert placed is False
    assert len(slide.shapes) == 0



