import json
from pathlib import Path

from case3.chat_revise import try_chat_revise


def test_shorter_edits_the_report_behind_a_chat_turn(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    report_dir = tmp_path / "runs" / "out" / report
    chat_dir = tmp_path / "runs" / "out" / chat
    report_dir.mkdir(parents=True)
    chat_dir.mkdir(parents=True)
    (report_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": report,
                "output_mode": "report",
                "artifacts": {"pdf": "report.pdf"},
                "last_edit": {"op": "rewrite", "section": "Введение"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (report_dir / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": chat,
                "prior_run_id": report,
                "output_mode": "chat",
                "artifacts": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, str] = {}

    def fake_rewrite(out_dir: Path, text: str, act) -> str:
        seen["dir"] = out_dir.name
        seen["section"] = act.section
        return "Переписал раздел «Введение» по документам. Новых чисел нет."

    monkeypatch.setattr("case3.chat_revise._rewrite", fake_rewrite)
    result = try_chat_revise("короче", chat, root=tmp_path)
    assert result is not None
    assert result["run_id"] == chat
    assert seen["dir"] == report
    assert seen["section"] == "Введение"
    head = json.loads((chat_dir / "meta.json").read_text(encoding="utf-8"))
    assert head["last_edit"]["section"] == "Введение"
    assert result["surface"] == "report"


def test_named_deck_title_edits_the_slide_not_the_report(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    deck = "source_20261118T130000Z"
    report_dir = tmp_path / "runs" / "out" / report
    deck_dir = tmp_path / "runs" / "out" / deck
    report_dir.mkdir(parents=True)
    deck_dir.mkdir(parents=True)
    (report_dir / "note.tex").write_text("\\title{Старое}\n", encoding="utf-8")
    (report_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": report, "output_mode": "report", "artifacts": {"pdf": "a.pdf"}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (deck_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": deck,
                "prior_run_id": report,
                "output_mode": "presentation",
                "slides_status": "ok",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_slide(run_id: str, out_dir: Path, title: str, index: int = 1) -> str:
        seen["dir"] = out_dir.name
        seen["title"] = title
        seen["index"] = index
        return f"Заголовок слайда {index} теперь «{title}»."

    monkeypatch.setattr("case3.chat_revise._retitle_slide", fake_slide)
    result = try_chat_revise(
        "поменяй заголовок презентации на Гомель",
        deck,
        root=tmp_path,
    )
    assert result is not None
    assert result["surface"] == "deck"
    assert seen["dir"] == deck
    assert seen["title"] == "Гомель"
    assert seen["index"] == 1


def test_shorter_still_edits_a_report_twelve_answers_later(tmp_path: Path, monkeypatch):
    root = tmp_path
    prev = ""
    report = ""
    head = ""
    for i in range(12):
        run_id = f"source_20261118T{i:02d}0000Z"
        out = root / "runs" / "out" / run_id
        out.mkdir(parents=True)
        if i == 0:
            report = run_id
            (out / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
        head = run_id
        (out / "meta.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "prior_run_id": prev,
                    "output_mode": "report" if i == 0 else "chat",
                    "artifacts": {"pdf": "a.pdf"} if i == 0 else {},
                    "last_edit": {"op": "rewrite", "section": "Введение"} if i == 0 else {},
                    "chat_prompt": "старт" if i == 0 else f"вопрос {i}",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        prev = run_id
    seen: dict[str, str] = {}

    def fake_rewrite(out_dir: Path, text: str, act) -> str:
        seen["dir"] = out_dir.name
        return "Переписал раздел «Введение» по документам. Новых чисел нет."

    monkeypatch.setattr("case3.chat_revise._rewrite", fake_rewrite)
    result = try_chat_revise("короче", head, root=root)
    assert result is not None
    assert result["op"] == "rewrite"
    assert result["run_id"] == head
    assert result["artifact_run_id"] == report
    assert seen["dir"] == report


def test_a_full_chat_asks_for_a_new_one_but_still_edits(tmp_path: Path, monkeypatch):
    from case3.chat_memory import _MAX_HOPS
    from case3.chat_revise import continue_or_limit

    root = tmp_path
    prev = ""
    head = ""
    for i in range(_MAX_HOPS):
        run_id = f"source_20261119T{i:06d}Z"
        out = root / "runs" / "out" / run_id
        out.mkdir(parents=True)
        if i == 0:
            (out / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
        head = run_id
        (out / "meta.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "prior_run_id": prev,
                    "output_mode": "report" if i == 0 else "chat",
                    "artifacts": {"pdf": "a.pdf"} if i == 0 else {},
                    "last_edit": {"op": "rewrite", "section": "Введение"} if i == 0 else {},
                    "chat_prompt": f"ход {i}",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        prev = run_id

    def fake_rewrite(out_dir: Path, text: str, act) -> str:
        return "Переписал раздел «Введение» по документам. Новых чисел нет."

    monkeypatch.setattr("case3.chat_revise._rewrite", fake_rewrite)
    edit = continue_or_limit("короче", head, root=root)
    assert edit is not None
    assert edit["op"] == "rewrite"
    blocked = continue_or_limit("что это значит", head, root=root)
    assert blocked is not None
    assert blocked["op"] == "full"
    assert "Пустой" in blocked["chat"]
    assert "С этими документами" in blocked["chat"]
    assert blocked["run_id"] == head
    assert not (root / "runs" / "out").joinpath("source_20261119T999999Z").exists()


def test_carried_file_can_be_edited_without_joining_its_chat(tmp_path: Path, monkeypatch):
    old = "source_20261118T100000Z"
    old_dir = tmp_path / "runs" / "out" / old
    old_dir.mkdir(parents=True)
    (old_dir / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
    (old_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": old,
                "output_mode": "report",
                "chat_prompt": "секретный старый вопрос",
                "artifacts": {"pdf": "a.pdf"},
                "last_edit": {"op": "rewrite", "section": "Введение"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def fake_rewrite(out_dir: Path, text: str, act) -> str:
        assert out_dir.name == old
        return "Переписал раздел «Введение» по документам. Новых чисел нет."

    monkeypatch.setattr("case3.chat_revise._rewrite", fake_rewrite)
    result = try_chat_revise("короче", "", root=tmp_path, carried_run_id=old)
    assert result is not None
    assert result["isolate"] is True
    assert result["run_id"] == old
    meta = json.loads((old_dir / "meta.json").read_text(encoding="utf-8"))
    assert "dialogue" not in meta
    assert meta["chat_prompt"] == "секретный старый вопрос"


def test_rename_heading_uses_the_report_dir(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    report_dir = tmp_path / "runs" / "out" / report
    report_dir.mkdir(parents=True)
    (report_dir / "note.tex").write_text("\\section{Введение}\nТекст.\n", encoding="utf-8")
    (report_dir / "meta.json").write_text(
        json.dumps({"run_id": report, "output_mode": "report", "artifacts": {"pdf": "a.pdf"}}),
        encoding="utf-8",
    )
    seen: dict[str, str] = {}

    def fake_rename(out_dir: Path, old: str, new: str) -> str:
        seen["dir"] = out_dir.name
        seen["old"] = old
        seen["new"] = new
        return "Переименовал раздел «Введение» в «Контекст»."

    monkeypatch.setattr("case3.chat_revise._rename_heading", fake_rename)
    result = try_chat_revise("переименуй раздел Введение в Контекст", report, root=tmp_path)
    assert result is not None
    assert result["surface"] == "report"
    assert seen == {"dir": report, "old": "Введение", "new": "Контекст"}


def test_unclear_edit_lists_the_real_headings(tmp_path: Path):
    run_id = "source_20261118T120000Z"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "output_mode": "report",
                "artifacts": {"pdf": "report.pdf"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "note.tex").write_text(
        "\\section{Введение}\nБыло 10.\n\\section{Итог}\nСтало 12.\n",
        encoding="utf-8",
    )
    result = try_chat_revise("поправь отчёт", run_id, root=tmp_path)
    assert result is not None
    assert result["op"] == "ask"
    assert "Введение" in result["chat"]
    assert "Итог" in result["chat"]
