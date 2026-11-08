"""Tests for pipeline slot self-healing and reset endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from case3.api import app, _claim_pipeline_slot, _release_pipeline_slot, _pipeline_active_run


def test_stale_slot_auto_reclaimed_when_terminal_meta_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = "source_20261108T194925Z"
    out = tmp_path / "runs" / "out" / run_id
    logs = tmp_path / "runs" / "logs" / run_id
    out.mkdir(parents=True)
    logs.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "status": "cancelled", "error": "Остановлено"}),
        encoding="utf-8",
    )
    # Simulate slot being locked by this cancelled run
    assert _claim_pipeline_slot(run_id) is None
    assert _pipeline_active_run() == run_id

    # A subsequent attempt to claim the slot must auto-reclaim it because status is cancelled
    new_holder = "source_new_test_123"
    claimed = _claim_pipeline_slot(new_holder)
    assert claimed is None
    assert _pipeline_active_run() == new_holder

    _release_pipeline_slot(new_holder)
    assert _pipeline_active_run() is None


def test_pipeline_slot_reset_endpoint() -> None:
    assert _claim_pipeline_slot("mock_stuck_run") is None
    assert _pipeline_active_run() == "mock_stuck_run"

    client = TestClient(app)
    resp = client.post("/api/pipeline/slot/reset")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "reset_from": "mock_stuck_run"}
    assert _pipeline_active_run() is None
