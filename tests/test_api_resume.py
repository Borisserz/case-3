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
