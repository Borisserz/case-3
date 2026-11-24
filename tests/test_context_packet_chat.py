from __future__ import annotations

import json
from pathlib import Path

from case3.chat_turn import (
    generate_chat_charts,
    generate_chat_diagram,
    try_chat_answer,
)
from case3.pipeline import run_pipeline


class _AnswerClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.seen: list[str] = []

    def complete(self, **kwargs) -> str:
        self.seen.append(str(kwargs["user_text"]))
        return self.answer


def _chat_route(*, chart: bool = False) -> dict:
    return {
        "route_version": "ttg-v1",
        "kind": "chat",
        "steps": [{"kind": "chat"}],
        "want_chat_chart": chart,
        "want_chat_diagram": False,
        "build_media": {"chart": False, "diagram": False, "images": False},
        "edit_act": None,
        "mode_hint": "chat",
        "reason": "test",
        "clarify_prompt": None,
        "note": None,
    }


def test_pipeline_persists_manifest_before_chat_llm_and_passes_packet_block(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "project"
    (root / "prompt" / "gold").mkdir(parents=True)
    source = tmp_path / "source.md"
    source.write_text(
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nВыручка 20\n",
        encoding="utf-8",
    )
    run_id = "packet_chat_20261124T120000Z"
    out_dir = root / "runs" / "out" / run_id
    out_dir.mkdir(parents=True)
    (out_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "chat_prompt": "Сравни первый и второй документы",
                "route_plan": _chat_route(),
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, str] = {}

    def _answer(source_text: str, intent: str, **kwargs) -> str:
        disk_meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
        assert disk_meta["selection_manifest"]["evidence_ids"]
        captured["source"] = source_text
        captured["context_block"] = kwargs["context_block"]
        return "В первом документе 10, во втором 20."

    monkeypatch.setattr("case3.chat_turn.try_chat_answer", _answer)
    out = run_pipeline(
        source,
        project_root=root,
        run_id=run_id,
        intent="Сравни первый и второй документы",
        output_mode="chat",
        formats=set(),
        max_charts=0,
        dry_run=False,
    )

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert len(meta["selection_manifest"]["evidence_ids"]) == 2
    assert "## Выбранные источники" in captured["context_block"]
    assert "[doc:a-md]" in captured["context_block"]
    assert "[doc:b-md]" in captured["context_block"]


def test_try_chat_answer_uses_context_block_without_pasting_legacy_memory() -> None:
    client = _AnswerClient("Касса 20.")
    context_block = (
        "## Текущий запрос\nЧто с кассой?\n\n"
        "## Выбранные источники\nКасса 20.\n\n"
        "## Ограничение ответа\nБери факты из выбранных источников."
    )

    answer = try_chat_answer(
        "Касса 20.",
        "Что с кассой?\n\nПредыдущий ход этого чата:\nСтарый ответ 999.",
        client=client,
        context_block=context_block,
    )

    assert answer == "Касса 20."
    assert context_block in client.seen[0]
    assert "Старый ответ 999" not in client.seen[0]


def test_inline_visuals_skip_legacy_memory_when_packet_block_is_present(
    tmp_path: Path, monkeypatch
) -> None:
    context_block = "## Выбранные источники\n[selected:1] Касса 20."

    def _legacy_memory(*_args, **_kwargs):
        raise AssertionError("legacy visual memory must not run with a packet")

    monkeypatch.setattr("case3.chat_turn._visual_memory_context", _legacy_memory)
    chart_client = _AnswerClient("")
    charts, _status = generate_chat_charts(
        "Касса 20.",
        "Построй график\n\nПредыдущий ход этого чата:\nСтарый ответ 999.",
        max_charts=1,
        figs_dir=tmp_path / "figures",
        charts_dir=tmp_path / "charts",
        client=chart_client,
        extra_context="Касса равна 20.",
        context_block=context_block,
    )
    assert charts == []
    assert context_block in chart_client.seen[0]
    assert "Старый ответ 999" not in chart_client.seen[0]

    seen: dict[str, str] = {}

    def _complete_diagrams(*, intent: str, source_text: str, **_kwargs):
        seen["intent"] = intent
        seen["source"] = source_text
        return []

    monkeypatch.setattr(
        "case3.diagram_generate.complete_diagrams",
        _complete_diagrams,
    )
    diagrams, _diagram_status = generate_chat_diagram(
        "Касса 20.",
        "Построй схему\n\nПредыдущий ход этого чата:\nСтарый ответ 999.",
        figs_dir=tmp_path / "figures",
        client=object(),
        extra_context="Касса равна 20.",
        context_block=context_block,
    )
    assert diagrams == []
    assert context_block in seen["intent"]
    assert "Старый ответ 999" not in seen["intent"]
    assert seen["source"] == "Касса 20."
