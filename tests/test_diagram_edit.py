"""Diagram edit + regenerate (figures.json only, no TeX)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from case3.diagram_edit import DiagramEditError, edit_diagram_in_run, regenerate_diagrams_in_run


def _seed_run(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    source = tmp_path / "src.txt"
    source.write_text(
        "Клиент подаёт заявку. Если КИН ок — договор, иначе отказ.\n",
        encoding="utf-8",
    )
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": "t1",
                "source": str(source),
                "intent": "режим схема",
                "max_diagrams": 2,
                "output_mode": "diagram",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "figures.json").write_text(
        json.dumps(
            {
                "figures": [],
                "charts": [],
                "diagrams": [
                    {
                        "id": "dia_01",
                        "title": "Черновик",
                        "type": "flowchart",
                        "mermaid": "flowchart LR\n  A[Начало] --> B[Конец]",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out


def test_edit_diagram_saves_sanitized_mermaid(tmp_path: Path) -> None:
    out = _seed_run(tmp_path)
    new_src = (
        "flowchart TD\n"
        "  A[Заявка]:::start --> B{ОК?}:::decision\n"
        "  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22\n"
        "  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22\n"
    )
    result = edit_diagram_in_run(out, "dia_01", mermaid=new_src, title="Заявка")
    assert result["id"] == "dia_01"
    assert ":::start" in result["mermaid"]
    assert result["title"] == "Заявка"
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert fj["diagrams"][0]["mermaid"].startswith("flowchart")


def test_edit_diagram_rejects_unknown_id(tmp_path: Path) -> None:
    out = _seed_run(tmp_path)
    with pytest.raises(DiagramEditError, match="not found"):
        edit_diagram_in_run(out, "dia_99", mermaid="flowchart TD\nA-->B")


def test_regenerate_replaces_diagrams_with_llm(tmp_path: Path) -> None:
    out = _seed_run(tmp_path)
    payload = {
        "diagrams": [
            {
                "id": "dia_01",
                "title": "Согласование",
                "type": "flowchart",
                "mermaid": (
                    "flowchart TD\n"
                    "  A[Заявка]:::start --> B{КИН}:::decision\n"
                    "  B -->|ок| C[Договор]:::ok\n"
                    "  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22\n"
                    "  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22\n"
                    "  classDef ok fill:#cfe6d4,stroke:#3d7a4a,color:#1a2e22\n"
                ),
            }
        ]
    }

    class Fake:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, *, system: str, user_text: str, reasoning: str | None = None) -> str:
            self.calls += 1
            # First call = generate; may also call repair
            return "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"

    fake = Fake()
    result = regenerate_diagrams_in_run(
        out, palette="atelier", client=fake, skip_repair=True
    )
    assert result["diagrams"][0]["title"] == "Согласование"
    assert "КИН" in result["diagrams"][0]["mermaid"]
    assert fake.calls >= 1
    assert result.get("undo") and result["undo"].get("kind") == "diagram_regen"
    fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert fj["diagrams"][0]["title"] == "Согласование"
    # Pre-regen snapshot kept «Черновик»
    draft = fj.get("diagrams_draft") or []
    assert draft and draft[0]["title"] == "Черновик"
