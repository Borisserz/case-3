"""Cancel endpoint + cooperative flag."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from case3.api import app


def test_cancel_marks_meta(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    run_id = "run_cancel_test"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "status": "running", "stage": "latex"}),
        encoding="utf-8",
    )
    client = TestClient(app)
    r = client.post(f"/api/runs/{run_id}/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["cancel_requested"] is True
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["cancel_requested"] is True
