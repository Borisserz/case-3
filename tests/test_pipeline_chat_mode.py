from __future__ import annotations

import json
from pathlib import Path

from case3.pipeline import run_pipeline


def test_chat_mode_answers_without_tex(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "prompt" / "gold").mkdir(parents=True)
    src = tmp_path / "source.txt"
    src.write_text(
        "Выручка была 10, стала 12. Почему выросла, если других цифр нет?",
        encoding="utf-8",
    )

    out = run_pipeline(
        src,
        project_root=root,
        intent="Проанализируй, почему выручка выросла с 10 до 12",
        output_mode="chat",
        formats=set(),
        dry_run=True,
    )

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["output_mode"] == "chat"
    assert meta["status"] == "ok"
    assert meta.get("insufficient_data") is not True
    assert "Разбор останется в чате" in (meta.get("chat_summary") or "")
    assert not (out / "report.pdf").is_file()
    assert not list(out.glob("*.tex"))


def test_chat_mode_keeps_uploaded_photos_in_the_run(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "prompt" / "gold").mkdir(parents=True)
    src = tmp_path / "source.txt"
    src.write_text("Выручка была 10, стала 12.", encoding="utf-8")
    photo = tmp_path / "shot.png"
    photo.write_bytes(b"png-bytes")

    out = run_pipeline(
        src,
        project_root=root,
        intent="Что на фото, если выручка была 10 и стала 12?",
        output_mode="chat",
        formats=set(),
        dry_run=True,
        user_figures=[
            {"id": "usr_01", "source": "upload", "path": str(photo), "caption": "Фото 1"}
        ],
    )

    assert (out / "figures" / "usr_01.png").read_bytes() == b"png-bytes"
