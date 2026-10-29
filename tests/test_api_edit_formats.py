"""Edit routes share parse_formats_form (incl. none) + _resolve_run_dir."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from case3 import api as api_mod


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    runs = tmp_path / "runs"
    for sub in ("out", "work", "logs", "uploads"):
        (runs / sub).mkdir(parents=True)
    monkeypatch.setattr(api_mod, "ROOT", tmp_path)
    return TestClient(api_mod.app)


def _seed_run(root: Path, run_id: str = "edit_fmt_20260101T000000Z") -> Path:
    out = root / "runs" / "out" / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "demo.tex").write_text(
        r"\documentclass{article}\begin{document}"
        r"\begin{table}\caption{T}\begin{tabular}{l}A\\\end{tabular}\end{table}"
        r"\end{document}",
        encoding="utf-8",
    )
    (out / "figures.json").write_text("{}", encoding="utf-8")
    return out


def test_table_edit_bad_formats_mentions_none(
    client: TestClient, tmp_path: Path
) -> None:
    run_id = "edit_fmt_20260101T000000Z"
    _seed_run(tmp_path, run_id)
    r = client.post(
        f"/api/runs/{run_id}/tables/1/edit",
        json={
            "caption": "T",
            "headers": ["A"],
            "rows": [["1"]],
            "formats": "pptx",
        },
    )
    assert r.status_code == 400
    detail = str(r.json().get("detail") or "")
    assert "none" in detail
    assert "pdf" in detail


def test_figure_edit_404_uses_resolve_run_dir(client: TestClient) -> None:
    r = client.post(
        "/api/runs/missing_run_20260101T000000Z/figures/fig_01/edit",
        json={"mode": "generate", "prompt": "x", "formats": "both"},
    )
    assert r.status_code == 404


def test_paragraph_edit_accepts_formats_none(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """formats=none must not 400 at parse; rebuild with empty set is ok."""
    run_id = "edit_fmt_none_20260101T000000Z"
    out = _seed_run(tmp_path, run_id)
    (out / "demo.tex").write_text(
        "\\documentclass{article}\\begin{document}\n"
        "\\par First paragraph here.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    def _fake_edit(*_a, **_k):
        return {
            "paragraph_index": 1,
            "text": "Hi",
            "artifacts": {},
            "version": 1,
            "media_status": {},
            "undo": None,
        }

    import case3.api_edits as edits_mod

    monkeypatch.setattr(edits_mod, "edit_paragraph_in_run", _fake_edit)
    r = client.post(
        f"/api/runs/{run_id}/paragraphs/1/edit",
        json={"text": "Hi", "formats": "none"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "ok"
