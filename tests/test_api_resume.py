"""POST /api/runs/{id}/resume eligibility + kick."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from case3.api import app


def _failed_run(tmp_path: Path, *, failed_stage: str = "latex") -> str:
    run_id = "brief_20261029T120000Z"
    work = tmp_path / "runs" / "work" / run_id
    out = tmp_path / "runs" / "out" / run_id
    logs = tmp_path / "runs" / "logs" / run_id
    for d in (work, out, logs):
        d.mkdir(parents=True)
    (work / "brief.tex").write_text(
        r"\documentclass{article}\begin{document}x\end{document}",
        encoding="utf-8",
    )
    (work / "figures.json").write_text(
        json.dumps({"figures": [], "charts": [], "diagrams": []}),
        encoding="utf-8",
    )
    meta = {
        "run_id": run_id,
        "status": "error",
        "stage": "error",
        "failed_stage": failed_stage,
        "formats": ["pdf"],
        "error": "latexmk failed",
    }
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return run_id


def test_resume_409_when_not_eligible(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = _failed_run(tmp_path, failed_stage="llm")
    client = TestClient(app)
    r = client.post(f"/api/runs/{run_id}/resume")
    assert r.status_code == 409


def test_resume_200_kicks_background(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = _failed_run(tmp_path, failed_stage="latex")
    kicked = MagicMock()
    monkeypatch.setattr("case3.api._kick_resume_thread", kicked)
    client = TestClient(app)
    r = client.post(f"/api/runs/{run_id}/resume")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id
    assert body["status"] == "started"
    kicked.assert_called_once_with(run_id)


def test_status_error_includes_can_resume(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = _failed_run(tmp_path, failed_stage="charts")
    client = TestClient(app)
    r = client.get(f"/api/runs/{run_id}/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["can_resume"] is True
    assert body["failed_stage"] == "charts"


def test_resume_409_when_pipeline_slot_busy(tmp_path: Path, monkeypatch) -> None:
    from case3.api import _claim_pipeline_slot, _release_pipeline_slot

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = _failed_run(tmp_path, failed_stage="latex")
    kicked = MagicMock()
    monkeypatch.setattr("case3.api._kick_resume_thread", kicked)
    assert _claim_pipeline_slot("other_active_run") is None
    try:
        client = TestClient(app)
        r = client.post(f"/api/runs/{run_id}/resume")
        assert r.status_code == 409
        assert "other_active_run" in str(r.json().get("detail") or "")
        kicked.assert_not_called()
    finally:
        _release_pipeline_slot("other_active_run")


def test_resume_200_real_background_pipeline_transitions_to_ok(
    tmp_path: Path, monkeypatch
) -> None:
    """Real _bg_resume_pipeline must not fail eligibility after resume_run flips state."""
    from case3.api import _bg_resume_pipeline, _claim_pipeline_slot

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = _failed_run(tmp_path, failed_stage="latex")

    def fake_render(tex_path: Path, **kwargs):  # noqa: ANN001
        out_dir = kwargs["out_dir"]
        pdf = out_dir / f"{tex_path.stem}.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        return {"pdf": pdf}

    monkeypatch.setattr("case3.pipeline.render_tex", fake_render)
    monkeypatch.setattr(
        "case3.pipeline.try_generate_chat_summary",
        lambda *a, **k: ("ok", "summary"),
    )

    def sync_kick(rid: str) -> None:
        assert _claim_pipeline_slot(rid) is None
        _bg_resume_pipeline(rid)

    monkeypatch.setattr("case3.api._kick_resume_thread", sync_kick)
    client = TestClient(app)
    r = client.post(f"/api/runs/{run_id}/resume")
    assert r.status_code == 200
    meta = json.loads(
        (tmp_path / "runs" / "out" / run_id / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["status"] == "ok"


def test_datetime_stamp_unique_within_same_second() -> None:
    from case3.api import datetime_stamp

    s1 = datetime_stamp()
    s2 = datetime_stamp()
    assert s1 != s2


def test_create_run_409_when_busy_does_not_write_uploads(
    tmp_path: Path, monkeypatch
) -> None:
    from case3.api import _claim_pipeline_slot, _release_pipeline_slot

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    assert _claim_pipeline_slot("busy_run_123") is None
    try:
        client = TestClient(app)
        r = client.post(
            "/api/run",
            data={"source_text": "Конфиденциальный отчёт за Q4", "intent": "Отчёт"},
        )
        assert r.status_code == 409
        uploads_root = tmp_path / "runs" / "uploads"
        written = list(uploads_root.rglob("source.txt")) if uploads_root.exists() else []
        assert written == []
    finally:
        _release_pipeline_slot("busy_run_123")


