import json
from pathlib import Path

from case3.chat_memory import format_sources, format_thread, load_chain


def test_thread_marks_itself_as_not_source_and_shrinks_old_turns():
    turns = [
        {"chat_prompt": f"вопрос {i}", "chat_summary": f"ответ {i}", "output_mode": "chat"}
        for i in range(6)
    ]
    text = format_thread(turns)
    assert "не Source" in text
    assert "Ход 6" in text
    assert "Раньше:" in text
    assert format_thread([]) == ""


def test_chain_walks_prior_run_id_oldest_first(tmp_path: Path):
    root = tmp_path
    first = "source_20261118T100000Z"
    second = "source_20261118T110000Z"
    for run_id, prior, prompt in (
        (first, "", "первый"),
        (second, first, "второй"),
    ):
        out = root / "runs" / "out" / run_id
        out.mkdir(parents=True)
        (out / "meta.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "prior_run_id": prior,
                    "chat_prompt": prompt,
                    "chat_summary": prompt + " готов",
                    "output_mode": "chat",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    chain = load_chain(root, second)
    assert [m["chat_prompt"] for m in chain] == ["первый", "второй"]
    text = format_thread(chain)
    assert text.index("первый") < text.index("второй")


def test_sources_stay_labeled():
    text = format_sources([("Договор.pdf", "пункт 2"), ("", "")])
    assert "===== Договор.pdf =====" in text
    assert "пункт 2" in text
    assert format_sources([]) == ""


def test_thread_names_the_last_edit_as_dialogue_not_fact():
    text = format_thread(
        [
            {
                "chat_prompt": "переделай введение",
                "chat_summary": "Переписал раздел",
                "last_edit": {"section": "Введение"},
            }
        ]
    )
    assert "Введение" in text
    assert "не Source" in text
    assert text.count("Последняя правка") == 1


def test_memory_card_keeps_labels_and_drops_numbers_from_the_open_question():
    from case3.chat_memory import format_card, memory_card

    card = memory_card(
        [
            {
                "chat_prompt": "почему так?",
                "chat_summary": "Уточни, это про 20 процентов?",
                "last_edit": {"section": "Введение", "pack": "board"},
            }
        ],
        "===== a.txt =====\nбыло 10\n===== b.txt =====\nстало 12\n",
    )
    assert card["documents"] == ["a.txt", "b.txt"]
    assert card["section"] == "Введение"
    assert card["style"] == "board"
    assert card["turn_count"] == 1
    assert "20" not in card["open_question"]
    text = format_card(card)
    assert "не Source" in text
    assert "a.txt" in text
    assert "20" not in text


def test_recall_finds_the_same_word_in_another_case():
    from case3.chat_memory import recall_block

    hit = recall_block(
        [{"chat_prompt": "касса выросла", "chat_summary": "КАССАСЕМЬ"}],
        "что ты говорил про кассу",
    )
    assert "КАССАСЕМЬ" in hit
    other = recall_block(
        [{"chat_prompt": "доля в тексте", "chat_summary": "ДОЛЯСТАРТ"}],
        "что ты говорил про долю",
    )
    assert "ДОЛЯСТАРТ" in other


def test_recall_lifts_one_older_turn_and_says_when_it_is_missing():
    from case3.chat_memory import recall_block

    turns = [
        {"chat_prompt": "про долю", "chat_summary": "Доля в тексте есть."},
        {"chat_prompt": "про кассу", "chat_summary": "Касса отдельно."},
    ]
    hit = recall_block(turns, "как ты отвечал про долю")
    assert "Один прошлый ход" in hit
    assert "не Source" in hit
    assert "Доля в тексте есть." in hit
    assert "Касса" not in hit
    miss = recall_block(turns, "что ты говорил про маржу")
    assert "не видно" in miss
    assert recall_block(turns, "что такое доля") == ""


def test_prior_block_shows_the_card_and_not_the_carried_chat(tmp_path: Path):
    from case3.prior_turn import prior_block_for_form

    old = "source_20261118T100000Z"
    new = "source_20261118T110000Z"
    old_dir = tmp_path / "runs" / "out" / old
    new_dir = tmp_path / "runs" / "out" / new
    source = tmp_path / "runs" / "out" / new / "source.txt"
    old_dir.mkdir(parents=True)
    new_dir.mkdir(parents=True)
    source.write_text("===== a.txt =====\nбыло 10\n", encoding="utf-8")
    (old_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": old,
                "chat_prompt": "секретный старый вопрос",
                "chat_summary": "старый ответ про долю",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (new_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": new,
                "chat_prompt": "новый вопрос",
                "chat_summary": "новый ответ",
                "source": str(source),
                "carried_run_id": old,
                "last_edit": {"section": "Введение"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    block = prior_block_for_form(new, root=tmp_path, user_text="как ты отвечал про долю")
    assert "Карточка этого чата" in block
    assert "a.txt" in block
    assert "Введение" in block
    assert "новый вопрос" in block
    assert "секретный" not in block
    assert "Один прошлый ход" in block
    assert "не видно" in block


def test_chain_notice_only_on_the_turns_that_matter():
    from case3.chat_memory import chain_notice

    assert chain_notice(39) == ""
    assert "40" in chain_notice(40)
    assert "Новый чат" in chain_notice(40)
    assert chain_notice(46) == ""
    assert "один ход" in chain_notice(47)
    last = chain_notice(48)
    assert "последний" in last
    assert "Новый чат" in last


def test_carry_keeps_the_chat_notice():
    from case3.pipeline import carry_chat_prompt

    meta: dict = {}
    carry_chat_prompt(meta, {"chat_notice": "Остался один ход после этого."})
    assert meta["chat_notice"] == "Остался один ход после этого."


def _marked(marker: str, at: int, tail: str = "КОНЕЦ") -> str:
    gap = max(0, at - len(marker))
    return marker + ("н" * gap) + tail


def test_latest_answer_keeps_the_analysis_the_screen_shows():
    body = (
        "Абзац один про кассу.\n\nАбзац два про долю.\n\n"
        + ("н" * 360)
        + "СЕРЕДИНАРАЗБОРА"
        + ("н" * 1700)
        + "ЛИШНЕЕ"
    )
    text = format_thread(
        [{"chat_prompt": "разбери", "chat_summary": body, "output_mode": "chat"}]
    )
    assert "Абзац один про кассу.\n\nАбзац два про долю." in text
    assert "СЕРЕДИНАРАЗБОРА" in text
    assert "ЛИШНЕЕ" not in text
    assert "не Source" in text


def test_thread_budget_shrinks_as_turns_get_older():
    """Archive is one line. Four turns back stays short. The previous turn keeps ~1200."""
    turns = [
        {"chat_prompt": "старт", "chat_summary": "начало разговора"},
        {"chat_prompt": "давно", "chat_summary": "давний ответ"},
        {"chat_prompt": "далеко", "chat_summary": _marked("ДАЛЕКО", 400, "СРЕЗДАЛЕКО")},
        {"chat_prompt": "середина", "chat_summary": _marked("СЕРЕДИНА", 400, "СРЕЗСЕРЕДИНА")},
        {
            "chat_prompt": "прошлый",
            "chat_summary": "ПРОШЛЫЙ" + ("н" * 400) + "ДЕРЖУПРОШЛЫЙ" + ("н" * 900) + "СРЕЗПРОШЛЫЙ",
        },
        {"chat_prompt": "сейчас", "chat_summary": "короткий текущий"},
    ]
    text = format_thread(turns)
    assert "начало разговора" in text
    assert "Раньше:" in text
    assert "ДАЛЕКО" in text
    assert "СРЕЗДАЛЕКО" not in text
    assert "СРЕЗСЕРЕДИНА" not in text
    assert "ПРОШЛЫЙ" in text
    assert "ДЕРЖУПРОШЛЫЙ" in text
    assert "СРЕЗПРОШЛЫЙ" not in text
    assert "сейчас" in text


def test_recall_returns_the_old_analysis_not_a_stub():
    from case3.chat_memory import recall_block

    summary = (
        "Касса выросла в тексте.\n\n"
        + ("н" * 400)
        + "ПАМЯТЬ"
        + ("н" * 1700)
        + "ХВОСТПАМЯТИ"
    )
    hit = recall_block(
        [{"chat_prompt": "разбор кассы", "chat_summary": summary}],
        "что ты говорил про кассу",
    )
    assert "Касса выросла в тексте." in hit
    assert "ПАМЯТЬ" in hit
    assert "ХВОСТПАМЯТИ" not in hit


def test_latest_edit_note_is_not_cut_at_the_old_limit():
    note = "а" * 180 + "КОНЕЦЗАМЕТКИ"
    text = format_thread(
        [
            {
                "chat_prompt": "поправь",
                "chat_summary": "Переписал",
                "dialogue": [{"user": note, "assistant": "Сделал правку в разделе"}],
            }
        ]
    )
    assert "КОНЕЦЗАМЕТКИ" in text
    assert "Сделал правку в разделе" in text


def test_long_thread_keeps_the_start_and_one_edit_line():
    turns = []
    for i in range(12):
        turns.append(
            {
                "chat_prompt": f"вопрос {i}",
                "chat_summary": "старт разговора" if i == 0 else ("ответ " + "слово " * 40),
                "last_edit": {"op": "rewrite", "section": "Введение"},
            }
        )
    text = format_thread(turns)
    assert "старт разговора" in text
    assert "вопрос 11" in text
    assert text.count("Последняя правка") == 1


def test_split_sources_roundtrip_and_plain_text():
    from case3.chat_memory import split_sources

    packed = format_sources([("А.pdf", "один"), ("Б.md", "два")])
    assert split_sources(packed) == [("А.pdf", "один"), ("Б.md", "два")]
    assert split_sources("просто текст") == [("Документ", "просто текст")]
    assert split_sources("  ") == []


def test_focus_source_keeps_only_the_named_document():
    from case3.chat_memory import focus_source

    packed = format_sources([("А.pdf", "один"), ("Б.md", "два")])
    focused = focus_source(packed, "разбери по второму файлу")
    assert "Б.md" in focused
    assert "один" not in focused
    assert focus_source(packed, "что здесь?") == packed


def test_newest_edit_walks_past_a_chat_turn(tmp_path: Path):
    from case3.chat_memory import newest_edit

    root = tmp_path
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    for run_id, prior, edit in (
        (report, "", {"op": "rewrite", "section": "Введение"}),
        (chat, report, {}),
    ):
        out = root / "runs" / "out" / run_id
        out.mkdir(parents=True)
        (out / "meta.json").write_text(
            json.dumps(
                {"run_id": run_id, "prior_run_id": prior, "last_edit": edit},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    found = newest_edit(root, chat)
    assert found.get("section") == "Введение"


def test_undo_keeps_the_section_it_followed(tmp_path: Path):
    from case3.chat_memory import newest_edit

    root = tmp_path
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    for run_id, prior, edit in (
        (report, "", {"op": "rewrite", "section": "Введение"}),
        (chat, report, {"op": "undo"}),
    ):
        out = root / "runs" / "out" / run_id
        out.mkdir(parents=True)
        (out / "meta.json").write_text(
            json.dumps(
                {"run_id": run_id, "prior_run_id": prior, "last_edit": edit},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    found = newest_edit(root, chat)
    assert found.get("section") == "Введение"
    assert found.get("op") == "undo"


def test_twelve_turns_still_find_the_report_and_the_edit(tmp_path: Path):
    from case3.chat_memory import memory_view

    root = tmp_path
    prev = ""
    ids = []
    for i in range(12):
        run_id = f"source_20261118T{i:02d}0000Z"
        ids.append(run_id)
        out = root / "runs" / "out" / run_id
        out.mkdir(parents=True)
        edit = {"op": "rewrite", "section": "Введение"} if i == 0 else {}
        (out / "meta.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "prior_run_id": prev,
                    "chat_prompt": "старт" if i == 0 else f"вопрос {i}",
                    "chat_summary": "ответ",
                    "output_mode": "report" if i == 0 else "chat",
                    "last_edit": edit,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        if i == 0:
            (out / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
        prev = run_id
    chain = load_chain(root, ids[-1])
    assert len(chain) == 12
    assert chain[0]["chat_prompt"] == "старт"
    view = memory_view(root, ids[-1])
    assert view is not None
    assert view["turns"][0]["chat_prompt"] == "старт"
    assert view["last_edit"]["section"] == "Введение"
    assert view["artifact_run_id"] == ids[0]


def test_memory_view_returns_only_uploaded_photos(tmp_path: Path):
    from case3.chat_memory import memory_view

    run_id = "source_20261118T120000Z"
    out = tmp_path / "runs" / "out" / run_id
    figs = out / "figures"
    figs.mkdir(parents=True)
    (figs / "usr_01.png").write_bytes(b"png")
    (figs / "cht_01.png").write_bytes(b"chart")
    (out / "meta.json").write_text(
        json.dumps(
            {"run_id": run_id, "chat_prompt": "смотри фото", "output_mode": "chat"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    view = memory_view(tmp_path, run_id)
    assert view is not None
    assert view["turns"][0]["photos"] == [
        {"name": "usr_01", "url": f"/api/runs/{run_id}/figures/usr_01.png"}
    ]


def test_memory_keeps_a_photo_that_was_left_beside_the_source(tmp_path: Path):
    from case3.chat_memory import memory_view

    run_id = "source_20261118T130000Z"
    upload = tmp_path / "runs" / "uploads" / "stamp"
    (upload / "user_photos").mkdir(parents=True)
    (upload / "user_photos" / "usr_01.png").write_bytes(b"png-bytes")
    (upload / "source.txt").write_text("было 10", encoding="utf-8")
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "chat_prompt": "что на фото",
                "output_mode": "chat",
                "source": str(upload / "source.txt"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    view = memory_view(tmp_path, run_id)
    assert view is not None
    assert view["turns"][0]["photos"] == [
        {"name": "usr_01", "url": f"/api/runs/{run_id}/figures/usr_01.png"}
    ]
    assert (out / "figures" / "usr_01.png").read_bytes() == b"png-bytes"
