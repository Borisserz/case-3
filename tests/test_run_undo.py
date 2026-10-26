"""B21: one-slot undo snapshot for Liber edits."""

from __future__ import annotations

import json
from pathlib import Path

from case3.run_undo import (
    apply_undo,
    capture_before_edit,
    clear_undo,
    undo_meta,
)


def _seed_run(out: Path) -> None:
    out.mkdir(parents=True)
    (out / "report.tex").write_text("% before\n", encoding="utf-8")
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
    assert undo_meta(out) is not None

    (out / "report.tex").write_text("% after\n", encoding="utf-8")
    (out / "figures" / "cht_01.png").write_bytes(b"PNG_AFTER" + b"\x00" * 40)

    info = apply_undo(out, rebuild=False)
    assert info["kind"] == "chart"
    assert (out / "report.tex").read_text(encoding="utf-8") == "% before\n"
    assert (out / "figures" / "cht_01.png").read_bytes().startswith(b"PNG_BEFORE")
    assert undo_meta(out) is None
    assert clear_undo(out) is False


def test_second_capture_overwrites_slot(tmp_path: Path) -> None:
    out = tmp_path / "out" / "run_u2"
    _seed_run(out)
    capture_before_edit(out, kind="chart", target="cht_01")
    (out / "report.tex").write_text("% mid\n", encoding="utf-8")
    capture_before_edit(out, kind="table", target="0")
    apply_undo(out, rebuild=False)
    assert (out / "report.tex").read_text(encoding="utf-8") == "% mid\n"
