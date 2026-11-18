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
