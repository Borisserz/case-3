from __future__ import annotations

import json
from pathlib import Path

from case3.pipeline import run_pipeline


def test_pipeline_insufficient_data_short_circuits(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "prompt" / "gold").mkdir(parents=True)

    src = tmp_path / "source.txt"
    src.write_text("привет, сделай отчет", encoding="utf-8")

    out_dir = run_pipeline(
        src,
        project_root=root,
        intent="сделай отчет",
        output_mode="report",
        dry_run=True,
    )

    meta_file = out_dir / "meta.json"
    assert meta_file.is_file(), "meta.json must be written"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    assert meta.get("insufficient_data") is True
    assert meta.get("status") == "ok"
    assert meta.get("stage") == "ok"
    assert meta.get("artifacts") == {}
    assert "недостаточно данных" in (meta.get("chat_summary") or "").lower()

    summary_file = out_dir / "chat_summary.txt"
    assert summary_file.is_file()
    assert "недостаточно данных" in summary_file.read_text(encoding="utf-8").lower()
