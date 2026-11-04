"""Edit routes share parse_formats_form (incl. none) + _resolve_run_dir."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(api_client: TestClient) -> TestClient:
    return api_client


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
    client: TestClient, repo_root: Path
) -> None:
    run_id = "edit_fmt_20260101T000000Z"
    _seed_run(repo_root, run_id)
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
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """formats=none must not 400 at parse; rebuild with empty set is ok."""
    run_id = "edit_fmt_none_20260101T000000Z"
    out = _seed_run(repo_root, run_id)
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


def test_docs_rebuild_calls_rebuild_run_docs(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "edit_docs_rebuild_20260101T000000Z"
    out = _seed_run(repo_root, run_id)
    (out / "demo.pdf").write_bytes(b"%PDF-1.4")
    called: dict[str, object] = {}

    def _fake_rebuild(out_dir, *, formats=None):
        called["out"] = out_dir
        called["formats"] = formats
        return {"pdf": out_dir / "demo.pdf"}

    import case3.run_rebuild as rebuild_mod

    monkeypatch.setattr(rebuild_mod, "rebuild_run_docs", _fake_rebuild)
    r = client.post(f"/api/runs/{run_id}/docs/rebuild")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("run_id") == run_id
    assert "preview" in body
    assert "downloads" in body
    assert called.get("formats") == {"pdf", "docx"}
    assert Path(called["out"]).resolve() == out.resolve()


def test_undo_accepts_rebuild_false(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "edit_undo_norebuild_20260101T000000Z"
    _seed_run(repo_root, run_id)
    seen: dict[str, object] = {}

    def _fake_undo(out_dir, *, rebuild=True):
        seen["rebuild"] = rebuild
        return {"kind": "paragraph", "target": "1"}

    import case3.run_undo as undo_mod

    monkeypatch.setattr(undo_mod, "apply_undo", _fake_undo)
    r = client.post(f"/api/runs/{run_id}/undo?rebuild=0")
    assert r.status_code == 200, r.text
    assert seen.get("rebuild") is False


def test_slides_ir_rebuild_false_skips_worker(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "slides_ir_norebuild_20260101T000000Z"
    out = repo_root / "runs" / "out" / run_id
    out.mkdir(parents=True, exist_ok=True)
    slides = out / "slides"
    slides.mkdir(parents=True, exist_ok=True)
    deck = {
        "slides": [
            {"id": "s1", "title": "A", "layout": "title_body", "blocks": []},
        ]
    }
    (slides / "deck.json").write_text(
        json.dumps(deck), encoding="utf-8"
    )
    (out / "meta.json").write_text(
        json.dumps({"status": "ok", "slides_status": "ok"}), encoding="utf-8"
    )
    started: list[bool] = []

    def _fake_thread(*_a, **_k):
        started.append(True)
        class T:
            def start(self):
                return None
        return T()

    import case3.api_slides as slides_mod

    monkeypatch.setattr(slides_mod.threading, "Thread", _fake_thread)
    r = client.patch(
        f"/api/runs/{run_id}/slides/ir?rebuild=0",
        json={"slides": [{"id": "s1", "title": "B"}]},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("rebuilt") is False
    assert started == []
    saved = json.loads((slides / "deck.json").read_text(encoding="utf-8"))
    assert saved["slides"][0]["title"] == "B"
