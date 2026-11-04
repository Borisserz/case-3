"""Session undo stack + redo for Liber edits."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from case3.run_undo import (
    MAX_UNDO_DEPTH,
    UndoError,
    apply_redo,
    apply_undo,
    capture_before_edit,
    clear_undo,
    undo_meta,
)


def _seed_run(out: Path, tex: str = "% before\n") -> None:
    out.mkdir(parents=True)
    (out / "report.tex").write_text(tex, encoding="utf-8")
    figs = out / "figures"
    figs.mkdir()
    (figs / "cht_01.png").write_bytes(b"PNG_BEFORE" + b"\x00" * 40)
    (out / "figures.json").write_text(
        json.dumps({"charts": [{"id": "cht_01"}]}), encoding="utf-8"
    )
    (out / "meta.json").write_text(
        json.dumps({"run_id": "u1", "status": "ok"}), encoding="utf-8"
    )


def test_capture_and_apply_restores_files(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_u"
    _seed_run(out)
    capture_before_edit(out, kind="chart", target="cht_01")
    meta = undo_meta(out)
    assert meta is not None
    assert meta["can_undo"] is True
    assert meta["can_redo"] is False
    assert meta["depth"] == 1

    (out / "report.tex").write_text("% after\n", encoding="utf-8")
    (out / "figures" / "cht_01.png").write_bytes(b"PNG_AFTER" + b"\x00" * 40)

    info = apply_undo(out, rebuild=False)
    assert info["kind"] == "chart"
    assert (out / "report.tex").read_text(encoding="utf-8") == "% before\n"
    assert (out / "figures" / "cht_01.png").read_bytes().startswith(b"PNG_BEFORE")
    meta2 = undo_meta(out)
    assert meta2 is not None
    assert meta2["can_undo"] is False
    assert meta2["can_redo"] is True
    assert meta2["depth"] == 0


def test_stack_two_edits_undo_twice(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_u2"
    _seed_run(out, "% v0\n")
    capture_before_edit(out, kind="paragraph", target="1")
    (out / "report.tex").write_text("% v1\n", encoding="utf-8")
    capture_before_edit(out, kind="heading", target="1")
    (out / "report.tex").write_text("% v2\n", encoding="utf-8")

    assert undo_meta(out)["depth"] == 2
    apply_undo(out, rebuild=False)
    assert (out / "report.tex").read_text(encoding="utf-8") == "% v1\n"
    assert undo_meta(out)["depth"] == 1
    assert undo_meta(out)["can_redo"] is True
    apply_undo(out, rebuild=False)
    assert (out / "report.tex").read_text(encoding="utf-8") == "% v0\n"
    assert undo_meta(out)["can_undo"] is False
    assert undo_meta(out)["can_redo"] is True


def test_redo_restores_forward(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_redo"
    _seed_run(out, "% v0\n")
    capture_before_edit(out, kind="paragraph", target="1")
    (out / "report.tex").write_text("% v1\n", encoding="utf-8")
    apply_undo(out, rebuild=False)
    assert (out / "report.tex").read_text(encoding="utf-8") == "% v0\n"
    info = apply_redo(out, rebuild=False)
    assert info.get("kind")
    assert (out / "report.tex").read_text(encoding="utf-8") == "% v1\n"
    meta = undo_meta(out)
    assert meta["can_undo"] is True
    assert meta["can_redo"] is False


def test_new_capture_clears_redo(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_cut"
    _seed_run(out, "% v0\n")
    capture_before_edit(out, kind="paragraph", target="1")
    (out / "report.tex").write_text("% v1\n", encoding="utf-8")
    apply_undo(out, rebuild=False)
    assert undo_meta(out)["can_redo"] is True
    capture_before_edit(out, kind="table", target="0")
    (out / "report.tex").write_text("% v2\n", encoding="utf-8")
    meta = undo_meta(out)
    assert meta["can_redo"] is False
    assert meta["depth"] == 1
    with pytest.raises(UndoError):
        apply_redo(out, rebuild=False)


def test_clear_undo_wipes_stack_and_redo(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_clear"
    _seed_run(out)
    capture_before_edit(out, kind="chart", target="cht_01")
    (out / "report.tex").write_text("% after\n", encoding="utf-8")
    apply_undo(out, rebuild=False)
    assert undo_meta(out)["can_redo"] is True
    assert clear_undo(out) is True
    assert undo_meta(out) is None


def test_stack_cap_drops_oldest(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_cap"
    _seed_run(out, "% base\n")
    for i in range(MAX_UNDO_DEPTH + 3):
        capture_before_edit(out, kind="paragraph", target=str(i))
        (out / "report.tex").write_text(f"% v{i}\n", encoding="utf-8")
    meta = undo_meta(out)
    assert meta["depth"] == MAX_UNDO_DEPTH
