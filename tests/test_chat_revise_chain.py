import json
from dataclasses import replace
from pathlib import Path

from case3.artifact_context import resolve_artifact_targets
from case3.chat_act import resolve_act
from case3.chat_revise import try_chat_revise
from case3.turn_plan import plan_turn


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
    report_meta = json.loads((report_dir / "meta.json").read_text(encoding="utf-8"))
    assert head["last_edit"]["section"] == "Введение"
    assert result["surface"] == "report"
    assert [note.get("user") for note in head.get("dialogue") or []] == ["короче"]
    assert "dialogue" not in report_meta


def _report_deck_chat_chain(tmp_path: Path) -> tuple[str, str, str]:
    report = "source_20261124R00000Z"
    deck = "source_20261124D00000Z"
    chat = "source_20261124C00000Z"
    report_dir = tmp_path / "runs" / "out" / report
    deck_dir = tmp_path / "runs" / "out" / deck
    chat_dir = tmp_path / "runs" / "out" / chat
    report_dir.mkdir(parents=True)
    deck_dir.mkdir(parents=True)
    chat_dir.mkdir(parents=True)
    (report_dir / "note.tex").write_text("\\title{Старый отчёт}\n", encoding="utf-8")
    (report_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": report, "output_mode": "report", "artifacts": {"pdf": "a.pdf"}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    slides_dir = deck_dir / "slides"
    slides_dir.mkdir(parents=True)
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
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": chat, "prior_run_id": deck, "output_mode": "chat"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return report, deck, chat


def test_slide_3_packet_target_prefers_deck_not_report(tmp_path: Path, monkeypatch):
    report, deck, chat = _report_deck_chat_chain(tmp_path)
    query = "поменяй заголовок слайда 3 на Новые итоги"
    plan = plan_turn(query, has_deck=True, has_report=True)
    targets = resolve_artifact_targets(
        plan=plan,
        root=tmp_path,
        prior_run_id=chat,
    )
    assert targets and targets[0].artifact_id.endswith(":slide:3")

    real_resolve = resolve_act

    def wrong_title_surface(text, **kwargs):
        act = real_resolve(text, **kwargs)
        if act.op == "retitle":
            return replace(act, title_on="report")
        return act

    monkeypatch.setattr("case3.chat_revise.resolve_act", wrong_title_surface)
    seen: dict[str, object] = {}

    def fake_report_title(_run_id: str, out_dir: Path, _title: str) -> str:
        seen["surface"] = "report"
        seen["dir"] = out_dir.name
        return "Заголовок отчёта теперь «Новые итоги»."

    def fake_slide_title(
        _run_id: str, out_dir: Path, _title: str, index: int = 1
    ) -> str:
        seen["surface"] = "deck"
        seen["dir"] = out_dir.name
        seen["index"] = index
        return f"Заголовок слайда {index} теперь «Новые итоги»."

    monkeypatch.setattr("case3.chat_revise._retitle", fake_report_title)
    monkeypatch.setattr("case3.chat_revise._retitle_slide", fake_slide_title)

    without_packet = try_chat_revise(query, chat, root=tmp_path)
    assert without_packet is not None
    assert seen.get("surface") == "report"
    assert seen.get("dir") == report

    seen.clear()
    with_packet = try_chat_revise(
        query,
        chat,
        root=tmp_path,
        edit_act=plan.edit_act,
        artifact_targets=targets,
    )
    assert with_packet is not None
    assert with_packet["artifact_run_id"] == deck
    assert with_packet["surface"] == "deck"
    assert seen == {"surface": "deck", "dir": deck, "index": 3}


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


def _report_dir(tmp_path: Path, run_id: str = "source_20261118T100000Z") -> Path:
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
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
    return out


def test_whole_report_shortens_the_file_behind_the_chat(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    report_dir = tmp_path / "runs" / "out" / report
    chat_dir = tmp_path / "runs" / "out" / chat
    report_dir.mkdir(parents=True)
    chat_dir.mkdir(parents=True)
    (report_dir / "note.tex").write_text(
        "\\section{Введение}\nБыло 10.\n", encoding="utf-8"
    )
    (report_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": report, "output_mode": "report", "artifacts": {"pdf": "report.pdf"}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": chat, "prior_run_id": report, "output_mode": "chat"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, str] = {}

    def fake_all(out_dir: Path, text: str, act) -> str:
        seen["dir"] = out_dir.name
        return "Сократил разделы: Введение."

    monkeypatch.setattr("case3.chat_revise._rewrite_all", fake_all)
    result = try_chat_revise("сократи весь отчёт", chat, root=tmp_path)
    assert result is not None
    assert result["op"] == "rewrite_all"
    assert result["artifact_run_id"] == report
    assert seen["dir"] == report


def test_failed_table_row_does_not_replace_the_last_edit(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    report_dir = tmp_path / "runs" / "out" / report
    chat_dir = tmp_path / "runs" / "out" / chat
    report_dir.mkdir(parents=True)
    chat_dir.mkdir(parents=True)
    (report_dir / "note.tex").write_text(_TABLE_TEX, encoding="utf-8")
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
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": chat, "prior_run_id": report, "output_mode": "chat"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    called = {"n": 0}

    def fake_edit(*_args, **_kwargs):
        called["n"] += 1
        return {}

    monkeypatch.setattr("case3.table_edit.edit_table_in_run", fake_edit)
    result = try_chat_revise(
        "в таблице добавь строку: только", chat, root=tmp_path
    )
    assert result is not None
    assert "ячеек" in result["chat"]
    assert called["n"] == 0
    from case3.chat_memory import newest_edit

    found = newest_edit(tmp_path, chat)
    assert found.get("op") == "rewrite"
    assert found.get("section") == "Введение"


def test_chart_recolor_from_chat_rebuilds_pdf_and_docx(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    _report_dir(tmp_path, report)
    seen: dict[str, object] = {}

    def fake_recolor(out_dir: Path, palette: str, formats=None):
        seen["dir"] = out_dir.name
        seen["palette"] = palette
        seen["formats"] = formats
        return {"ok": True}

    monkeypatch.setattr("case3.chart_edit.recolor_all_charts_in_run", fake_recolor)
    result = try_chat_revise("перекрась графики в ocean", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "recolor_charts"
    assert seen["dir"] == report
    assert seen["palette"] == "ocean"
    assert seen["formats"] == {"pdf", "docx"}


def test_green_phrase_repaints_the_chat_chart(tmp_path: Path, monkeypatch):
    chat = "source_20261118T150000Z"
    chat_dir = tmp_path / "runs" / "out" / chat
    figs = chat_dir / "figures"
    figs.mkdir(parents=True)
    html = (
        "<canvas id='c'></canvas><script>"
        "new Chart(c,{type:'bar',data:{labels:['Минск','Брест'],datasets:["
        "{label:'Факт',data:[10,20]}]},options:{responsive:false}});"
        "</script>"
    )
    (chat_dir / "figures.json").write_text(
        json.dumps(
            {"figures": [], "charts": [{"id": "cht_01", "type": "bar", "caption": "Факт", "html": html}], "diagrams": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (chat_dir / "meta.json").write_text(
        json.dumps({"run_id": chat, "output_mode": "chat", "charts_planned": ["cht_01"]}),
        encoding="utf-8",
    )

    def fake_batch(items):
        status = {}
        for cid, _chart, png_path, _cdir in items:
            png_path.parent.mkdir(parents=True, exist_ok=True)
            png_path.write_bytes(b"\x89PNG\r\n")
            status[cid] = {"ok": True}
        return status

    monkeypatch.setattr("case3.charts.render_charts_batch", fake_batch)
    result = try_chat_revise("Доработай график: сделай в зеленых цветах", chat, root=tmp_path)
    assert result is not None
    assert result["op"] == "recolor_hue"
    assert "зелён" in result["chat"]
    assert result["previews"][0]["id"] == "cht_01"
    saved = json.loads((chat_dir / "figures.json").read_text(encoding="utf-8"))
    assert "#1F8A45" in saved["charts"][0]["html"].upper()
    assert "data:[10,20]" in saved["charts"][0]["html"]


def test_pink_donut_phrase_repaints_and_attaches_the_chart(tmp_path: Path, monkeypatch):
    chat = "source_20261126T090000Z"
    chat_dir = tmp_path / "runs" / "out" / chat
    figs = chat_dir / "figures"
    figs.mkdir(parents=True)
    (figs / "cht_01.png").write_bytes(b"\x89PNG\r\n")
    html = (
        "<canvas id='c' width='1100' height='560'></canvas><script>"
        "new Chart(c,{type:'bar',data:{labels:['Минск','Брест'],datasets:["
        "{label:'Факт',data:[10,20]}]},options:{responsive:false}});"
        "</script>"
    )
    (chat_dir / "figures.json").write_text(
        json.dumps(
            {
                "figures": [],
                "charts": [{"id": "cht_01", "type": "bar", "caption": "Факт", "html": html}],
                "diagrams": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (chat_dir / "meta.json").write_text(
        json.dumps({"run_id": chat, "output_mode": "chat", "charts_planned": ["cht_01"]}),
        encoding="utf-8",
    )

    def fake_batch(items):
        status = {}
        for cid, _chart, png_path, _cdir in items:
            png_path.parent.mkdir(parents=True, exist_ok=True)
            png_path.write_bytes(b"\x89PNG\r\n")
            status[cid] = {"ok": True}
        return status

    monkeypatch.setattr("case3.charts.render_charts_batch", fake_batch)
    result = try_chat_revise("сделай круговой график розовым", chat, root=tmp_path)
    assert result is not None
    assert result["op"] == "recolor_hue"
    assert result["surface"] == "chat"
    assert result["previews"][0]["id"] == "cht_01"
    assert "розов" in result["chat"].casefold()
    saved = json.loads((chat_dir / "figures.json").read_text(encoding="utf-8"))
    chart = saved["charts"][0]
    assert chart["type"] == "donut"
    assert "#E2557E" in chart["html"].upper()
    assert "data:[10,20]" in chart["html"] or "data:[10, 20]" in chart["html"]


def test_chart_recolor_without_a_report_does_not_ask_for_print(tmp_path: Path, monkeypatch):
    deck = "source_20261118T140000Z"
    deck_dir = tmp_path / "runs" / "out" / deck
    deck_dir.mkdir(parents=True)
    (deck_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": deck,
                "output_mode": "presentation",
                "slides_status": "ok",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_recolor(out_dir: Path, palette: str, formats=None):
        seen["formats"] = formats
        return {"ok": True}

    monkeypatch.setattr("case3.chart_edit.recolor_all_charts_in_run", fake_recolor)
    result = try_chat_revise("перекрась графики в ocean", deck, root=tmp_path)
    assert result is not None
    assert seen["formats"] == set()


def test_undo_and_structure_after_chat_stay_on_the_deck(tmp_path: Path, monkeypatch):
    report = "source_20261121T200000Z"
    deck = "source_20261121T200100Z"
    chat = "source_20261121T200200Z"
    report_dir = tmp_path / "runs" / "out" / report
    deck_dir = tmp_path / "runs" / "out" / deck
    chat_dir = tmp_path / "runs" / "out" / chat
    for path in (report_dir, deck_dir, chat_dir):
        path.mkdir(parents=True)
    (report_dir / "note.tex").write_text(
        "\\section{Введение}\nБыло 10.\n", encoding="utf-8"
    )
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
                "last_edit": {"op": "recolor_deck", "pack": "board"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": chat,
                "prior_run_id": deck,
                "output_mode": "chat",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    undone: list[str] = []

    def apply_undo(out_dir: Path, *, rebuild: bool = True):
        undone.append(Path(out_dir).name)
        return {}

    monkeypatch.setattr("case3.run_undo.apply_undo", apply_undo)
    first = try_chat_revise("отмени", chat, root=tmp_path)
    second = try_chat_revise("отмени", chat, root=tmp_path)
    assert first is not None and first["surface"] == "deck"
    assert second is not None and second["surface"] == "deck"
    assert undone == [deck, deck]

    styled: list[str] = []

    def restyle(_run_id: str, out_dir: Path, _structure: str) -> str:
        styled.append(Path(out_dir).name)
        return "Собираю презентацию для инвестора."

    monkeypatch.setattr("case3.chat_revise._restyle_structure", restyle)
    changed = try_chat_revise(
        "смени структуру презентации на инвестора", chat, root=tmp_path
    )
    assert changed is not None
    assert changed["op"] == "restyle_structure"
    assert styled == [deck]


def test_undo_and_redo_from_chat_rebuild_print_files(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    _report_dir(tmp_path, report)
    seen: dict[str, bool] = {}

    def fake_undo(out_dir: Path, *, rebuild: bool = True):
        seen["undo"] = rebuild
        return {}

    def fake_redo(out_dir: Path, *, rebuild: bool = True):
        seen["redo"] = rebuild
        return {}

    monkeypatch.setattr("case3.run_undo.apply_undo", fake_undo)
    monkeypatch.setattr("case3.run_undo.apply_redo", fake_redo)
    undone = try_chat_revise("отмени", report, root=tmp_path)
    redone = try_chat_revise("верни правку", report, root=tmp_path)
    assert undone is not None and undone["op"] == "undo"
    assert redone is not None and redone["op"] == "redo"
    assert seen == {"undo": True, "redo": True}


_TABLE_TEX = """\\documentclass{article}
\\begin{document}
\\begin{table}
\\caption{Города}
\\begin{tabular}{ll}
Город & Люди \\\\
Гомель & 10 \\\\
\\end{tabular}
\\end{table}
\\begin{itemize}
\\item касса
\\item доля
\\end{itemize}
\\end{document}
"""


def test_table_cell_from_chat_rewrites_the_grid(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    out = _report_dir(tmp_path, report)
    (out / "note.tex").write_text(_TABLE_TEX, encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_edit(out_dir, index, *, caption, headers, rows, formats):
        seen["index"] = index
        seen["rows"] = rows
        seen["formats"] = formats
        return {}

    monkeypatch.setattr("case3.table_edit.edit_table_in_run", fake_edit)
    result = try_chat_revise("в таблице замени Гомель на Брест", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "replace_cell"
    assert result["surface"] == "report"
    assert seen["index"] == 1
    assert seen["formats"] == {"pdf", "docx"}
    assert seen["rows"] == [["Брест", "10"]]


def test_table_row_from_chat_is_appended_and_removed(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    out = _report_dir(tmp_path, report)
    (out / "note.tex").write_text(_TABLE_TEX, encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_edit(out_dir, index, *, caption, headers, rows, formats):
        seen["rows"] = rows
        seen["formats"] = formats
        return {}

    monkeypatch.setattr("case3.table_edit.edit_table_in_run", fake_edit)
    added = try_chat_revise(
        "в таблице добавь строку: Брест; 12", report, root=tmp_path
    )
    assert added is not None
    assert added["op"] == "add_row"
    assert seen["rows"] == [["Гомель", "10"], ["Брест", "12"]]
    assert seen["formats"] == {"pdf", "docx"}
    removed = try_chat_revise("убери из таблицы строку Гомель", report, root=tmp_path)
    assert removed is not None
    assert removed["op"] == "delete_row"
    assert seen["rows"] == []


def test_list_item_from_chat_is_appended(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    out = _report_dir(tmp_path, report)
    (out / "note.tex").write_text(_TABLE_TEX, encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_edit(out_dir, index, *, items, ordered=None, formats=None):
        seen["index"] = index
        seen["items"] = items
        seen["formats"] = formats
        return {}

    monkeypatch.setattr("case3.list_edit.edit_list_in_run", fake_edit)
    result = try_chat_revise(
        "добавь в список пункт риски поставки", report, root=tmp_path
    )
    assert result is not None
    assert result["op"] == "add_item"
    assert seen["items"] == ["касса", "доля", "риски поставки"]
    assert seen["formats"] == {"pdf", "docx"}


def test_list_item_decline_still_replaces_the_word(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    out = _report_dir(tmp_path, report)
    (out / "note.tex").write_text(_TABLE_TEX, encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_edit(out_dir, index, *, items, ordered=None, formats=None):
        seen["items"] = items
        return {}

    monkeypatch.setattr("case3.list_edit.edit_list_in_run", fake_edit)
    result = try_chat_revise("в списке замени кассу на выручку", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "replace_item"
    assert seen["items"] == ["выручку", "доля"]


def test_undo_does_not_forget_which_section_to_shorten(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    report_dir = _report_dir(tmp_path, report)
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
    chat_dir = tmp_path / "runs" / "out" / chat
    chat_dir.mkdir(parents=True)
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {
                "run_id": chat,
                "prior_run_id": report,
                "output_mode": "chat",
                "last_edit": {"op": "undo"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, str] = {}

    def fake_rewrite(out_dir: Path, text: str, act) -> str:
        seen["section"] = act.section
        return "Переписал раздел «Введение» по документам. Новых чисел нет."

    monkeypatch.setattr("case3.chat_revise._rewrite", fake_rewrite)
    result = try_chat_revise("короче", chat, root=tmp_path)
    assert result is not None
    assert result["op"] == "rewrite"
    assert seen["section"] == "Введение"


def test_undo_then_shorter_keeps_the_section_on_the_report(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    chat = "source_20261118T110000Z"
    report_dir = _report_dir(tmp_path, report)
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
    chat_dir = tmp_path / "runs" / "out" / chat
    chat_dir.mkdir(parents=True)
    (chat_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": chat, "prior_run_id": report, "output_mode": "chat"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("case3.run_undo.apply_undo", lambda *a, **k: {})
    seen: dict[str, str] = {}

    def fake_rewrite(out_dir: Path, text: str, act) -> str:
        seen["section"] = act.section
        return "Переписал раздел «Введение» по документам. Новых чисел нет."

    monkeypatch.setattr("case3.chat_revise._rewrite", fake_rewrite)
    undone = try_chat_revise("отмени", chat, root=tmp_path)
    assert undone is not None and undone["op"] == "undo"
    result = try_chat_revise("короче", chat, root=tmp_path)
    assert result is not None
    assert result["op"] == "rewrite"
    assert seen["section"] == "Введение"


def test_diagram_phrase_refines_the_only_scheme(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    out = _report_dir(tmp_path, report)
    (out / "figures.json").write_text(
        json.dumps(
            {"diagrams": [{"id": "dia_01", "title": "Касса", "mermaid": "graph LR\nA-->B"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_refine(out_dir, diagram_id, *, instruction, client, palette, formats):
        seen["id"] = diagram_id
        seen["instruction"] = instruction
        seen["formats"] = formats
        return {"id": diagram_id}

    monkeypatch.setattr("case3.diagram_edit.refine_diagram_in_run", fake_refine)
    monkeypatch.setattr(
        "case3.llm_client.LLMConfig.from_env",
        lambda: object(),
    )
    monkeypatch.setattr("case3.llm_client.LLMClient", lambda _cfg: object())
    result = try_chat_revise("на схеме убери кассу", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "refine_diagram"
    assert seen["id"] == "dia_01"
    assert "кассу" in str(seen["instruction"])
    assert seen["formats"] == {"pdf", "docx"}


def test_slide_points_from_chat_patch_bullets(tmp_path: Path, monkeypatch):
    deck = "source_20261118T140000Z"
    deck_dir = tmp_path / "runs" / "out" / deck
    deck_dir.mkdir(parents=True)
    (deck_dir / "meta.json").write_text(
        json.dumps(
            {"run_id": deck, "output_mode": "presentation", "slides_status": "ok"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_load(run_id, out_dir):
        return (
            {
                "slides": [
                    {"id": "s1", "title": "Старт"},
                    {"id": "s2", "title": "Середина", "bullets": ["старое"]},
                ]
            },
            deck_dir / "slides" / "deck.json",
        )

    def fake_patch(base, patch):
        seen["patch"] = patch
        return base

    def fake_enqueue(*_args, **_kwargs):
        seen["enqueued"] = True

    monkeypatch.setattr("case3.api_slides._load_deck_for_patch", fake_load)
    monkeypatch.setattr("case3.slides_patch.apply_deck_text_patch", fake_patch)
    monkeypatch.setattr("case3.api_slides._enqueue_deck_rebuild", fake_enqueue)
    result = try_chat_revise(
        "на слайде 2 пункты: риски; сроки", deck, root=tmp_path
    )
    assert result is not None
    assert result["op"] == "slide_bullets"
    assert result["surface"] == "deck"
    assert seen["patch"]["slides"][0]["bullets"] == ["риски", "сроки"]
    assert seen["enqueued"] is True


def test_a_failed_rewrite_asks_for_the_number(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    _report_dir(tmp_path, report)
    meta_path = tmp_path / "runs" / "out" / report / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["last_edit"] = {"op": "rewrite", "section": "Введение"}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    def empty_draft(**_kwargs):
        return ""

    monkeypatch.setattr("case3.chat_turn.draft_section", empty_draft)
    result = try_chat_revise("короче", report, root=tmp_path)
    assert result is not None
    assert "40" in result["chat"]
    assert "черновик вышел пустым" not in result["chat"]


def test_a_rewrite_keeps_a_number_the_user_wrote(tmp_path: Path, monkeypatch):
    report = "source_20261118T100000Z"
    _report_dir(tmp_path, report)
    meta_path = tmp_path / "runs" / "out" / report / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["last_edit"] = {"op": "rewrite", "section": "Введение"}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    seen: dict[str, str] = {}

    def draft(**kwargs):
        seen["user_text"] = kwargs.get("user_text") or ""
        return "В кассе теперь 40."

    def edit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("case3.chat_turn.draft_section", draft)
    monkeypatch.setattr("case3.paragraph_edit.edit_paragraph_in_run", edit)
    result = try_chat_revise("ещё короче, касса 40", report, root=tmp_path)
    assert result is not None
    assert "40" in seen["user_text"]
    assert "40" in result["chat"]
    assert "твоего сообщения" in result["chat"]


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


def test_diagram_phrase_keeps_the_run_palette(tmp_path: Path, monkeypatch):
    report = "source_20261119T120000Z"
    out = _report_dir(tmp_path, report)
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["chart_palette"] = "ocean"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (out / "figures.json").write_text(
        json.dumps(
            {"diagrams": [{"id": "dia_01", "title": "Касса", "mermaid": "graph LR\nA-->B"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_refine(out_dir, diagram_id, *, instruction, client, palette, formats):
        seen["palette"] = palette
        return {"id": diagram_id}

    monkeypatch.setattr("case3.diagram_edit.refine_diagram_in_run", fake_refine)
    monkeypatch.setattr("case3.llm_client.LLMConfig.from_env", lambda: object())
    monkeypatch.setattr("case3.llm_client.LLMClient", lambda _cfg: object())
    result = try_chat_revise("на схеме убери кассу", report, root=tmp_path)
    assert result is not None
    assert seen["palette"] == "ocean"


def test_change_photo_edits_the_chat_png_not_a_new_one(tmp_path: Path, monkeypatch):
    run_id = "chat_20261125T120000Z"
    out = tmp_path / "runs" / "out" / run_id
    figs = out / "figures"
    figs.mkdir(parents=True)
    (figs / "fig_01.png").write_bytes(b"png")
    (out / "meta.json").write_text(
        '{"run_id":"chat_20261125T120000Z","status":"ok","output_mode":"chat"}',
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_edit(out_dir, figure_id, *, mode, prompt, caption=None, formats=None, cfg=None):
        seen["id"] = figure_id
        seen["mode"] = mode
        seen["prompt"] = prompt
        seen["formats"] = formats
        return {"figure_id": figure_id}

    monkeypatch.setattr("case3.figure_edit.edit_figure_in_run", fake_edit)
    result = try_chat_revise("измени фото сделай небо темнее", run_id, root=tmp_path)
    assert result is not None
    assert result["op"] == "edit_photo"
    assert seen["id"] == "fig_01"
    assert seen["mode"] == "edit"
    assert seen["prompt"] == "небо темнее"
    assert seen["formats"] == set()
    assert result["surface"] == "chat"
    assert result["previews"][0]["id"] == "fig_01"
    assert "?v=" in result["previews"][0]["url"]


def test_unnamed_color_asks_when_a_chart_and_a_photo_are_both_open(tmp_path: Path, monkeypatch):
    report = "source_20261119T140000Z"
    out = _report_dir(tmp_path, report)
    figs = out / "figures"
    figs.mkdir()
    (figs / "fig_01.png").write_bytes(b"png")
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["charts_planned"] = ["cht_01"]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise AssertionError("a bare color must ask, not edit")

    monkeypatch.setattr("case3.figure_edit.edit_figure_in_run", boom)
    asked = try_chat_revise("сделай красным", report, root=tmp_path)
    assert asked is not None
    assert asked["op"] == "ask"
    folded = asked["chat"].casefold()
    assert "фото" in folded and "график" in folded
    assert "Введение" not in asked["chat"]

    seen: dict[str, object] = {}

    def fake_edit(out_dir, figure_id, *, mode, prompt, caption=None, formats=None, cfg=None):
        seen["id"] = figure_id
        seen["prompt"] = prompt
        return {"figure_id": figure_id}

    monkeypatch.setattr("case3.figure_edit.edit_figure_in_run", fake_edit)
    edited = try_chat_revise("сделай машину красной", report, root=tmp_path)
    assert edited is not None
    assert edited["op"] == "edit_photo"
    assert seen["id"] == "fig_01"
    assert "красн" in str(seen["prompt"]).casefold()


def test_photo_phrase_edits_the_only_png(tmp_path: Path, monkeypatch):
    report = "source_20261119T130000Z"
    out = _report_dir(tmp_path, report)
    figs = out / "figures"
    figs.mkdir()
    (figs / "usr_01.png").write_bytes(b"png")
    seen: dict[str, object] = {}

    def fake_edit(out_dir, figure_id, *, mode, prompt, caption=None, formats=None, cfg=None):
        seen["id"] = figure_id
        seen["mode"] = mode
        seen["prompt"] = prompt
        seen["formats"] = formats
        return {"figure_id": figure_id}

    monkeypatch.setattr("case3.figure_edit.edit_figure_in_run", fake_edit)
    result = try_chat_revise("на фото сделай небо темнее", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "edit_photo"
    assert seen["id"] == "usr_01"
    assert seen["mode"] == "edit"
    assert seen["prompt"] == "небо темнее"
    assert seen["formats"] == {"pdf", "docx"}


def test_missing_deck_returns_the_canned_line(tmp_path: Path):
    report = "source_20261121T180000Z"
    _report_dir(tmp_path, report)
    result = try_chat_revise("убери слайд 2?", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "talk"
    assert result["chat"].startswith("Презентации в этом чате ещё нет")
    meta = json.loads(
        (tmp_path / "runs" / "out" / report / "meta.json").read_text(encoding="utf-8")
    )
    notes = meta.get("dialogue") or []
    assert notes[-1]["user"] == "убери слайд 2?"
    assert notes[-1]["assistant"].startswith("Презентации в этом чате ещё нет")


def test_two_verbs_run_in_the_order_they_were_written(tmp_path: Path, monkeypatch):
    run_id = "source_20261121T190000Z"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "note.tex").write_text("\\section{Введение}\nБыло 10.\n", encoding="utf-8")
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "output_mode": "report",
                "slides_status": "ok",
                "artifacts": {"pdf": "report.pdf"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: list[str] = []

    def delete_slide(*_args, **_kwargs):
        seen.append("delete")
        return "Убираю слайд 2."

    def recolor(*_args, **_kwargs):
        seen.append("recolor")
        return "Перекрасил графики в ocean."

    monkeypatch.setattr("case3.chat_revise._delete_slide", delete_slide)
    monkeypatch.setattr("case3.chat_revise._recolor_charts", recolor)
    result = try_chat_revise(
        "убери слайд 2 и перекрась графики в ocean",
        run_id,
        root=tmp_path,
    )
    assert result is not None
    assert seen == ["delete", "recolor"]
    assert "Убираю слайд 2." in result["chat"]
    assert "ocean" in result["chat"]
    assert result["op"] == "batch"
    assert result["surfaces"] == [
        {"surface": "deck", "artifact_run_id": run_id, "op": "delete_slide"},
        {"surface": "report", "artifact_run_id": run_id, "op": "recolor_charts"},
    ]


def test_plain_question_still_goes_to_the_model(tmp_path: Path):
    report = "source_20261121T180100Z"
    _report_dir(tmp_path, report)
    assert try_chat_revise("что с кассой", report, root=tmp_path) is None
    assert try_chat_revise("поменяй числа на графике", report, root=tmp_path) is None
    assert try_chat_revise("почему бы не убрать слайд 2?", report, root=tmp_path) is None


def test_retype_chart_hides_raw_english_js_error_from_user(tmp_path: Path, monkeypatch):
    from case3.chart_edit import ChartEditError

    run_id = "source_20261123T173136Z"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "output_mode": "chat",
                "charts_planned": ["cht_01"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def boom(*_args, **_kwargs):
        raise ChartEditError(
            "chart render failed: chart JS error: Cannot read properties of undefined (reading 'axis')"
        )

    monkeypatch.setattr("case3.chart_edit.edit_chart_in_run", boom)
    result = try_chat_revise("сделай этот график линейным", run_id, root=tmp_path)
    assert result is not None
    msg = result["chat"]
    assert "chart render failed" not in msg
    assert "chart JS error" not in msg
    assert "reading 'axis'" not in msg
    assert any("а" <= ch.lower() <= "я" for ch in msg)


def _tex_report(tmp_path: Path, run_id: str, tex: str, *, charts: list[dict] | None = None) -> Path:
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    meta: dict = {"run_id": run_id, "output_mode": "report", "artifacts": {"pdf": "a.pdf"}}
    if charts:
        meta["charts_planned"] = [item["id"] for item in charts]
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (out / "note.tex").write_text(tex, encoding="utf-8")
    if charts:
        (out / "figures.json").write_text(
            json.dumps({"figures": [], "charts": charts, "diagrams": []}, ensure_ascii=False),
            encoding="utf-8",
        )
    return out


def test_delete_named_chart_strips_it_and_keeps_the_other(tmp_path: Path, monkeypatch):
    run_id = "source_20261125T120000Z"
    tex = (
        "\\section{Введение}\nТекст.\n"
        "\\begin{figure}[H]\n\\includegraphics{figures/cht_01.png}\n\\caption{Поступления}\n\\end{figure}\n"
        "\\begin{figure}[H]\n\\includegraphics{figures/cht_02.png}\n\\caption{План}\n\\end{figure}\n"
    )
    out = _tex_report(
        tmp_path,
        run_id,
        tex,
        charts=[
            {"id": "cht_01", "caption": "Поступления", "type": "bar"},
            {"id": "cht_02", "caption": "План", "type": "bar"},
        ],
    )
    monkeypatch.setattr("case3.run_rebuild.rebuild_run_docs", lambda *_a, **_k: {})
    result = try_chat_revise("удали график поступления", run_id, root=tmp_path)
    assert result is not None
    assert result["op"] == "delete_chart"
    assert result["surface"] == "report"
    fresh = (out / "note.tex").read_text(encoding="utf-8")
    assert "cht_01" not in fresh
    assert "cht_02" in fresh
    assert "Поступления" not in fresh


def test_delete_second_paragraph_leaves_the_heading(tmp_path: Path, monkeypatch):
    run_id = "source_20261125T120100Z"
    tex = "\\section{Введение}\nПервый факт.\n\nВторой факт про кассу.\n\n\\section{Итог}\nКонец.\n"
    out = _tex_report(tmp_path, run_id, tex)
    monkeypatch.setattr("case3.run_rebuild.rebuild_run_docs", lambda *_a, **_k: {})
    result = try_chat_revise("удали второй абзац введения", run_id, root=tmp_path)
    assert result is not None
    assert result["op"] == "delete_paragraph"
    assert result["surface"] == "report"
    fresh = (out / "note.tex").read_text(encoding="utf-8")
    assert "Первый факт" in fresh
    assert "Второй факт" not in fresh
    assert "\\section{Введение}" in fresh


def test_delete_block_removes_the_section(tmp_path: Path, monkeypatch):
    run_id = "source_20261125T120200Z"
    tex = "\\section{Введение}\nВода.\n\n\\section{Итог}\nФакт.\n"
    out = _tex_report(tmp_path, run_id, tex)
    monkeypatch.setattr("case3.run_rebuild.rebuild_run_docs", lambda *_a, **_k: {})
    result = try_chat_revise("удали блок введение", run_id, root=tmp_path)
    assert result is not None
    assert result["op"] == "delete_section"
    assert result["surface"] == "report"
    fresh = (out / "note.tex").read_text(encoding="utf-8")
    assert "\\section{Введение}" not in fresh
    assert "\\section{Итог}" in fresh
