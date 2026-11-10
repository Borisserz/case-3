"""Disk waiter: one queued run survives an API restart (ADR-0010)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from case3.api import app, _claim_pipeline_slot, _release_pipeline_slot
from case3.pipeline_queue import clear_waiter, load_waiter, save_waiter


def _source(root: Path, name: str = "source.txt") -> Path:
    upload = root / "runs" / "uploads" / "stamp"
    upload.mkdir(parents=True, exist_ok=True)
    path = upload / name
    path.write_text("Выручка 12 и 40%.", encoding="utf-8")
    return path


def _queued_meta(root: Path, run_id: str) -> None:
    out = root / "runs" / "out" / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "queued",
                "stage": "queued",
                "steps": [
                    {
                        "event": "stage",
                        "stage": "queued",
                        "scope": "pipeline",
                        "t": 1.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    src = _source(tmp_path)
    save_waiter(
        tmp_path,
        {
            "src_path": str(src),
            "run_id": "source_20261110T120000Z",
            "formats": ["pdf"],
            "dry_run": False,
            "intent": "Отчёт",
            "max_images": 1,
            "max_charts": 2,
            "max_diagrams": 0,
            "user_figures": [{"id": "usr_01", "caption": "экран"}],
            "output_mode": "report",
        },
    )
    loaded = load_waiter(tmp_path)
    assert loaded is not None
    assert loaded["run_id"] == "source_20261110T120000Z"
    assert loaded["user_figures"] == [{"id": "usr_01", "caption": "экран"}]
    assert loaded["formats"] == ["pdf"]
    assert Path(loaded["src_path"]) == src.resolve()


def test_load_rejects_path_outside_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / "not-a-run-source.txt"
    outside.write_text("x", encoding="utf-8")
    save_waiter(
        tmp_path,
        {
            "src_path": str(outside),
            "run_id": "source_20261110T120001Z",
            "formats": ["pdf"],
            "dry_run": False,
            "intent": "Отчёт",
            "max_images": 0,
            "max_charts": 0,
            "max_diagrams": 0,
            "user_figures": [],
            "output_mode": "report",
        },
    )
    assert load_waiter(tmp_path) is None


def test_clear_waiter_only_matching_run(tmp_path: Path) -> None:
    src = _source(tmp_path)
    payload = {
        "src_path": str(src),
        "run_id": "source_keep",
        "formats": ["docx"],
        "dry_run": False,
        "intent": "x",
        "max_images": 0,
        "max_charts": 0,
        "max_diagrams": 0,
        "user_figures": [],
        "output_mode": "report",
    }
    save_waiter(tmp_path, payload)
    assert clear_waiter(tmp_path, run_id="source_other") is False
    assert load_waiter(tmp_path) is not None
    assert clear_waiter(tmp_path, run_id="source_keep") is True
    assert load_waiter(tmp_path) is None


def test_post_run_persists_waiter(tmp_path: Path, monkeypatch) -> None:
    import threading

    ran = threading.Event()

    def _fake_bg(**kwargs: object) -> None:
        ran.set()

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    monkeypatch.setattr("case3.api._bg_run_pipeline", _fake_bg)
    assert _claim_pipeline_slot("holder_run") is None
    run_id = ""
    try:
        client = TestClient(app)
        queued = client.post(
            "/api/run",
            data={"source_text": "Текст отчёта с числами 12 и 40%", "intent": "Отчёт"},
        )
        assert queued.status_code == 202
        run_id = queued.json()["run_id"]
        stored = load_waiter(tmp_path)
        assert stored is not None
        assert stored["run_id"] == run_id
        meta = json.loads(
            (tmp_path / "runs" / "out" / run_id / "meta.json").read_text(encoding="utf-8")
        )
        assert meta["status"] == "queued"
        assert any(
            isinstance(s, dict) and s.get("stage") == "queued" for s in meta.get("steps") or []
        )
    finally:
        _release_pipeline_slot("holder_run")
        if run_id:
            assert ran.wait(2)
            _release_pipeline_slot(run_id)


def test_recover_starts_queued_job_after_restart(tmp_path: Path, monkeypatch) -> None:
    from case3.api import recover_persisted_pipeline

    started: list[str] = []

    def _fake_bg(**kwargs: object) -> None:
        started.append(str(kwargs["run_id"]))

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    monkeypatch.setattr("case3.api._bg_run_pipeline", _fake_bg)
    run_id = "source_20261110T130000Z"
    src = _source(tmp_path)
    _queued_meta(tmp_path, run_id)
    save_waiter(
        tmp_path,
        {
            "src_path": str(src),
            "run_id": run_id,
            "formats": ["pdf", "docx"],
            "dry_run": True,
            "intent": "Отчёт",
            "max_images": 0,
            "max_charts": 0,
            "max_diagrams": 0,
            "user_figures": [],
            "output_mode": "report",
        },
    )
    try:
        assert recover_persisted_pipeline() == run_id
        for _ in range(50):
            if started and load_waiter(tmp_path) is None:
                break
            time.sleep(0.02)
        assert started == [run_id]
        assert load_waiter(tmp_path) is None
    finally:
        _release_pipeline_slot(run_id)


def test_recover_drops_terminal_and_cancelled(tmp_path: Path, monkeypatch) -> None:
    from case3.api import recover_persisted_pipeline

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    monkeypatch.setattr(
        "case3.api._bg_run_pipeline",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not start")),
    )
    run_id = "source_20261110T130001Z"
    src = _source(tmp_path)
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "status": "queued", "cancel_requested": True}),
        encoding="utf-8",
    )
    save_waiter(
        tmp_path,
        {
            "src_path": str(src),
            "run_id": run_id,
            "formats": ["pdf"],
            "dry_run": False,
            "intent": "Отчёт",
            "max_images": 0,
            "max_charts": 0,
            "max_diagrams": 0,
            "user_figures": [],
            "output_mode": "report",
        },
    )
    assert recover_persisted_pipeline() is None
    assert load_waiter(tmp_path) is None
