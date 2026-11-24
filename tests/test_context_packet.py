import json
from pathlib import Path

from case3.context_packet import (
    ArtifactTarget,
    ContextPacket,
    DialogueExcerpt,
    EvidenceChunk,
    HistoricalUserBinding,
    PacketBudgets,
    PacketCoverage,
    PacketRequest,
    PacketRoute,
    build_context_packet,
    render_chat_user_block,
)
from case3 import context_select
from case3.turn_plan import plan_turn

_CHAT_SECTION_ORDER = [
    "## Текущий запрос",
    "## Маршрут хода",
    "## Выбранные источники",
    "## Покрытие источников",
    "## Контекст диалога — не источник чисел",
    "## Открытый артефакт — не Source",
    "## Числа из прошлых реплик пользователя",
    "## Ограничение ответа",
]


def test_packet_has_version_and_route():
    plan = plan_turn("Какая доля Минской?", mode_hint="auto")
    p = build_context_packet(
        plan=plan,
        user_text="Какая доля Минской?",
        source_text="| Область | Факт |\n| --- | --- |\n| Минская | 10 |\n",
    )
    assert p.version == "gcp-v1"
    assert p.route.kind == "chat"
    assert p.request.text.startswith("Какая")


def test_compare_two_docs_equal_quotas():
    text = (
        "===== Документ 1: A.md =====\nВыручка 10\n\n"
        "===== Документ 2: B.md =====\nВыручка 20\n"
    )
    query = "Сравни первый и второй документы по выручке"
    packet = build_context_packet(
        plan=plan_turn(query, mode_hint="auto"),
        user_text=query,
        source_text=text,
    )

    assert len(packet.source_catalog) >= 2
    assert packet.request.compare is True
    assert packet.budgets.per_source_quota
    assert len(set(packet.selection_manifest.quotas.values())) == 1
    assert {chunk.source_id for chunk in packet.evidence} == {
        source.id for source in packet.source_catalog
    }


def test_explicit_second_doc_only():
    text = (
        "===== Документ 1: A.md =====\nРиск пожар\n\n"
        "===== Документ 2: B.md =====\nРиск кибер\n"
    )
    query = "Ответь только по второму файлу: какие там риски?"
    packet = build_context_packet(
        plan=plan_turn(query),
        user_text=query,
        source_text=text,
    )

    assert packet.request.named_source_ids == [packet.source_catalog[1].id]
    assert {chunk.source_id for chunk in packet.evidence} == {
        packet.source_catalog[1].id
    }
    assert packet.coverage.omitted == [packet.source_catalog[0].id]
    assert "explicit_focus" in packet.coverage.notices
    assert packet.selection_manifest.omitted == [
        {"source_id": packet.source_catalog[0].id, "reason": "explicit_focus"}
    ]


def test_plain_source_catalog_uses_current_document_id():
    from case3.context_select import catalog_sources

    catalog = catalog_sources("Один документ", None)

    assert [(item.source_id, item.title) for item in catalog] == [
        ("doc:current", "Документ")
    ]


def test_markdown_table_rows_stay_whole_when_chunked():
    from case3.context_select import catalog_sources, chunk_source

    source = "\n".join(
        [
            "# Раздел",
            "| Регион | Факт |",
            "| --- | --- |",
            *[f"| Регион {index} | {index} |" for index in range(400)],
        ]
    )

    chunks = chunk_source(catalog_sources(source, None)[0])

    assert len(chunks) > 1
    assert all(chunk.text.startswith("# Раздел\n") for chunk in chunks)
    assert all(
        line.count("|") >= 3
        for chunk in chunks
        for line in chunk.text.splitlines()
        if line.startswith("|")
    )


def test_compare_generic_document_word_does_not_focus_current_only():
    query = "Сравни оба документа"
    packet = build_context_packet(
        plan=plan_turn(query),
        user_text=query,
        source_text="Первый текст",
        attachments=[("B.md", "Второй текст")],
    )

    assert len(packet.source_catalog) == 2
    assert {chunk.source_id for chunk in packet.evidence} == {
        source.id for source in packet.source_catalog
    }


def _write_chain(tmp_path, turns):
    prior = ""
    ids = []
    for index, turn in enumerate(turns):
        run_id = f"source_20261124T{index:06d}Z"
        out = tmp_path / "runs" / "out" / run_id
        out.mkdir(parents=True)
        (out / "meta.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "prior_run_id": prior,
                    "chat_prompt": turn[0],
                    "chat_summary": turn[1],
                    "output_mode": "chat",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        prior = run_id
        ids.append(run_id)
    return ids


def test_dialogue_never_number_evidence(tmp_path):
    ids = _write_chain(
        tmp_path,
        [
            ("первый вопрос", "первый ответ"),
            ("сколько в кассе", "Модель сказала 999."),
        ],
    )

    packet = build_context_packet(
        plan=plan_turn("что с кассой"),
        user_text="что с кассой",
        source_text="",
        root=tmp_path,
        prior_run_id=ids[-1],
    )

    assert packet.dialogue
    assert all(not item.number_evidence for item in packet.dialogue)
    assert any("999" in item.text for item in packet.dialogue)
    assert packet.selection_manifest.dialogue_ids


def test_dialogue_keeps_eight_recent_and_at_most_two_older_recalls(tmp_path):
    ids = _write_chain(
        tmp_path,
        [
            ("касса архив один", "первый архивный ответ"),
            ("без темы", "архивный шум"),
            ("касса архив два", "второй архивный ответ"),
            ("касса архив три", "третий архивный ответ"),
            *[(f"свежий вопрос {index}", f"свежий ответ {index}") for index in range(8)],
        ],
    )

    dialogue = context_select.select_dialogue(
        tmp_path,
        ids[-1],
        "что с кассой",
        budget=24_000,
    )

    assert len([item for item in dialogue if item.role == "recent"]) == 8
    recalls = [item for item in dialogue if item.role == "recall"]
    assert len(recalls) == 2
    assert all(item.turn_id in ids[:4] for item in recalls)
    assert all(not item.number_evidence for item in dialogue)


def test_dialogue_respects_budget(tmp_path):
    ids = _write_chain(
        tmp_path,
        [(f"вопрос {index}", "длинный ответ " * 80) for index in range(10)],
    )

    dialogue = context_select.select_dialogue(
        tmp_path,
        ids[-1],
        "продолжай",
        budget=500,
    )

    assert sum(len(item.text) for item in dialogue) <= 500


def test_render_order_and_not_source_label():
    packet = build_context_packet(
        plan=plan_turn("Какая доля Минской?", mode_hint="auto"),
        user_text="Какая доля Минской?",
        source_text="| Область | Факт |\n| --- | --- |\n| Минская | 10 |\n",
    )
    block = render_chat_user_block(packet)

    assert "## Текущий запрос" in block
    assert "## Выбранные источники" in block
    assert "не источник чисел" in block.lower() or "не Source" in block


def test_render_section_headers_follow_spec_order():
    packet = build_context_packet(
        plan=plan_turn("Сравни первый и второй", mode_hint="auto"),
        user_text="Сравни первый и второй",
        source_text=(
            "===== Документ 1: A.md =====\nВыручка 10\n\n"
            "===== Документ 2: B.md =====\nВыручка 20\n"
        ),
    )
    block = render_chat_user_block(packet)
    positions = [block.index(title) for title in _CHAT_SECTION_ORDER if title in block]

    assert positions == sorted(positions)
    assert positions[0] == block.index("## Текущий запрос")
    assert block.rindex("## Ограничение ответа") > block.index("## Выбранные источники")


def test_render_includes_dialogue_section_when_present(tmp_path):
    ids = _write_chain(
        tmp_path,
        [
            ("первый вопрос", "первый ответ"),
            ("сколько в кассе", "Модель сказала 999."),
        ],
    )
    packet = build_context_packet(
        plan=plan_turn("что с кассой"),
        user_text="что с кассой",
        source_text="Касса 100",
        root=tmp_path,
        prior_run_id=ids[-1],
    )

    block = render_chat_user_block(packet)

    assert "## Контекст диалога — не источник чисел" in block
    assert "не источник чисел" in block.lower()


def test_render_optional_sections_only_when_populated():
    minimal = ContextPacket(
        version="gcp-v1",
        packet_id="gcp-test",
        route=PacketRoute(kind="chat"),
        request=PacketRequest(text="вопрос"),
        budgets=PacketBudgets(evidence=100, dialogue=50, artifact=20),
        evidence=[
            EvidenceChunk(
                chunk_id="doc:current:0",
                source_id="doc:current",
                title="Документ",
                text="Факт 1",
            )
        ],
        coverage=PacketCoverage(selected=["doc:current"]),
    )
    block = render_chat_user_block(minimal)

    assert "## Открытый артефакт — не Source" not in block
    assert "## Числа из прошлых реплик пользователя" not in block
    assert "## Контекст диалога — не источник чисел" not in block

    rich = ContextPacket(
        version=minimal.version,
        packet_id="gcp-rich",
        route=minimal.route,
        request=minimal.request,
        budgets=minimal.budgets,
        evidence=minimal.evidence,
        coverage=minimal.coverage,
        dialogue=[
            DialogueExcerpt(turn_id="t1", role="recent", text="Ход 1. Запрос: было")
        ],
        historical_user_bindings=[HistoricalUserBinding(stem="слайд", value="2")],
        artifact_targets=[ArtifactTarget(artifact_id="art:report", label="Отчёт")],
    )
    rich_block = render_chat_user_block(rich)

    assert rich_block.index("## Контекст диалога — не источник чисел") < rich_block.index(
        "## Открытый артефакт — не Source"
    )
    assert rich_block.index("## Открытый артефакт — не Source") < rich_block.index(
        "## Числа из прошлых реплик пользователя"
    )
    assert "2 слайд" in rich_block or "слайд" in rich_block


def _write_deck_run(root: Path, run_id: str) -> None:
    out_dir = root / "runs" / "out" / run_id
    out_dir.mkdir(parents=True)
    (out_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "prior_run_id": "",
                "output_mode": "presentation",
                "slides_status": "ok",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    slides_dir = out_dir / "slides"
    slides_dir.mkdir()
    (slides_dir / "deck.json").write_text(
        json.dumps(
            {
                "slides": [
                    {"id": "s01", "title": "Обзор"},
                    {"id": "s02", "title": "Данные"},
                    {"id": "s03", "title": "Старые итоги"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_revise_packet_resolves_artifact_targets(tmp_path):
    deck_id = "source_20261124T200000Z"
    _write_deck_run(tmp_path, deck_id)
    query = "поменяй заголовок слайда 3 на Новые итоги"
    plan = plan_turn(query, has_deck=True)

    packet = build_context_packet(
        plan=plan,
        user_text=query,
        source_text="",
        root=tmp_path,
        prior_run_id=deck_id,
    )

    assert packet.route.kind == "revise"
    assert len(packet.artifact_targets) == 1
    assert packet.artifact_targets[0].artifact_id == f"artifact:{deck_id}:slide:3"
    assert packet.artifact_targets[0].number_evidence is False


def test_chat_packet_skips_artifact_targets(tmp_path):
    deck_id = "source_20261124T200001Z"
    _write_deck_run(tmp_path, deck_id)

    packet = build_context_packet(
        plan=plan_turn("какая доля минской области"),
        user_text="какая доля минской области",
        source_text="| Область | Доля |\n| Минская | 10 |",
        root=tmp_path,
        prior_run_id=deck_id,
    )

    assert packet.route.kind == "chat"
    assert packet.artifact_targets == []


def test_build_packet_accepts_explicit_artifact_targets():
    override = ArtifactTarget(
        artifact_id="artifact:run:section:Выводы",
        label="Раздел «Выводы»",
        number_evidence=False,
    )
    plan = plan_turn("перепиши раздел Выводы", has_report=True)
    packet = build_context_packet(
        plan=plan,
        user_text="перепиши раздел Выводы",
        source_text="Исходник",
        artifact_targets=[override],
    )

    assert packet.artifact_targets == [override]


def test_render_revise_user_block_lists_open_artifact(tmp_path):
    deck_id = "source_20261124T200002Z"
    _write_deck_run(tmp_path, deck_id)
    query = "поменяй заголовок слайда 3 на Новые итоги"
    plan = plan_turn(query, has_deck=True)
    packet = build_context_packet(
        plan=plan,
        user_text=query,
        source_text="",
        root=tmp_path,
        prior_run_id=deck_id,
    )

    from case3.context_packet import render_revise_user_block

    block = render_revise_user_block(packet)

    assert "## Открытый артефакт — не Source" in block
    assert "не источник чисел" in block.lower() or "не Source" in block
    assert "Слайд 3" in block
    assert block.index("## Открытый артефакт — не Source") < block.rindex(
        "## Ограничение ответа"
    )