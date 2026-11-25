"""HTTP contract for Liber ↔ FastAPI (Windows desk: Qwen + Image API)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from case3 import api as api_mod


@pytest.fixture()
def client(api_client: TestClient) -> TestClient:
    return api_client


def test_health_ok(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "vision_configured" in data
    assert "image_api_configured" in data or "kandinsky_configured" in data
    assert "chart_types" in data
    assert "chart_palettes" in data


def test_status_rejects_bad_run_id(client: TestClient) -> None:
    # Slash / traversal never reach handler (404) or fail _RUN_ID_OK (400).
    r = client.get("/api/runs/bad/id/with/slash/status")
    assert r.status_code in {400, 404}
    r2 = client.get("/api/runs/not_a_real_run_zzz/status")
    assert r2.status_code == 404
    r3 = client.get("/api/runs/has spaces/status")
    assert r3.status_code in {400, 404}


def test_run_returns_202_and_status_poll(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_pipeline(*_a, run_id: str, **_kw):
        out = tmp_path / "runs" / "out" / run_id
        out.mkdir(parents=True, exist_ok=True)
        (out / "meta.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": "ok",
                    "stage": "ok",
                    "figures_planned": [],
                    "charts_planned": [],
                    "media_status": {},
                    "max_charts": 0,
                    "max_images": 0,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (out / "demo.tex").write_text(
            r"\documentclass{article}\begin{document}Hi\end{document}",
            encoding="utf-8",
        )
        return out

    monkeypatch.setattr(api_mod, "run_pipeline", _fake_pipeline)

    r = client.post(
        "/api/run",
        data={
            "source_text": "Выручка 10 20 30",
            "intent": "краткий отчёт",
            "max_charts": "0",
            "max_images": "0",
            "forbid_charts": "true",
            "forbid_images": "true",
            "dry_run": "true",
            "formats": "both",
            "chart_auto": "true",
            "chart_palette": "atelier",
        },
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body.get("status") == "started"
    run_id = body["run_id"]
    assert run_id

    # Daemon thread — poll (TestClient no longer awaits BackgroundTasks).
    import time

    payload: dict = {}
    for _ in range(80):
        st = client.get(f"/api/runs/{run_id}/status")
        assert st.status_code == 200
        payload = st.json()
        if payload.get("status") in {"ok", "error"}:
            break
        time.sleep(0.05)
    assert payload.get("status") == "ok", payload.get("error") or payload
    assert payload["run_id"] == run_id


def test_run_plaque_chart_starts_chat_chart_run(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[str] = []

    def _fake_spawn(job, slot_gen=None):
        started.append(job.output_mode)
        api_mod._release_pipeline_slot(job.run_id, generation=slot_gen)

    monkeypatch.setattr(api_mod, "_spawn_pipeline_thread", _fake_spawn)
    r = client.post(
        "/api/run",
        data={
            "intent": "Построй график по регионам",
            "output_mode": "report",
            "artifact_bias": "report",
            "source_text": "| Регион | Факт |\n| --- | --- |\n| Минск | 120 |\n",
        },
    )

    assert r.status_code == 202, r.text
    body = r.json()
    assert body["route_plan"]["kind"] == "chat"
    assert body["route_plan"]["want_chat_chart"] is True
    assert started == ["chat"]


def test_run_explicit_mode_chart_defaults_to_chat_over_conflicting_plaque(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[str] = []

    def _fake_spawn(job, slot_gen=None):
        started.append(job.output_mode)
        api_mod._release_pipeline_slot(job.run_id, generation=slot_gen)

    monkeypatch.setattr(api_mod, "_spawn_pipeline_thread", _fake_spawn)
    r = client.post(
        "/api/run",
        data={
            "intent": "Построй график по регионам",
            "output_mode": "presentation",
            "artifact_bias": "report",
            "source_text": "| Регион | Факт |\n| --- | --- |\n| Минск | 120 |\n",
        },
    )

    assert r.status_code == 202, r.text
    body = r.json()
    assert body["route_plan"]["kind"] == "chat"
    assert body["route_plan"]["want_chat_chart"] is True
    assert started == ["chat"]


def test_run_named_analyze_stays_chat_under_report_plaque(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[str] = []

    def _fake_spawn(job, slot_gen=None):
        started.append(job.output_mode)
        api_mod._release_pipeline_slot(job.run_id, generation=slot_gen)

    monkeypatch.setattr(api_mod, "_spawn_pipeline_thread", _fake_spawn)
    r = client.post(
        "/api/run",
        data={
            "source_text": "Минская область — 10",
            "intent": "Проанализируй отчёт",
            "output_mode": "auto",
            "artifact_bias": "report",
            "dry_run": "true",
        },
    )

    assert r.status_code == 202, r.text
    assert r.json()["output_mode"] == "chat"
    assert r.json()["route_plan"]["kind"] == "chat"
    assert started == ["chat"]


@pytest.mark.parametrize("text", ["ещё точнее", "короче", "тот раздел короче"])
def test_run_report_followup_revises_remembered_section(
    text: str,
    client: TestClient,
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "source_20261124T100000Z"
    out = repo_root / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "report.tex").write_text(
        "\\section{Введение}\nИсходный текст.\n", encoding="utf-8"
    )
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "ok",
                "output_mode": "report",
                "artifacts": {"pdf": "report.pdf"},
                "last_edit": {"op": "rewrite", "section": "Введение"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: list[str] = []

    def _fake_rewrite(_out: Path, _text: str, act) -> str:
        seen.append(act.section)
        return "Переписал раздел «Введение»."

    monkeypatch.setattr("case3.chat_revise._rewrite", _fake_rewrite)
    r = client.post(
        "/api/run",
        data={"intent": text, "prior_run_id": run_id, "output_mode": "auto"},
    )

    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "chat_revise"
    assert r.json()["route_plan"]["kind"] == "revise"
    assert seen == ["Введение"]


def test_run_deck_followup_repeats_remembered_restyle(
    client: TestClient,
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "source_20261124T110000Z"
    out = repo_root / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "ok",
                "output_mode": "presentation",
                "slides_status": "ok",
                "slides_theme_pack": "board",
                "last_edit": {"op": "recolor_deck", "pack": "board"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: list[str] = []

    def _fake_recolor(_run_id: str, _out: Path, pack: str) -> str:
        seen.append(pack)
        return "Перекрашиваю презентацию."

    monkeypatch.setattr("case3.chat_revise._recolor_deck", _fake_recolor)
    r = client.post(
        "/api/run",
        data={"intent": "ещё", "prior_run_id": run_id, "output_mode": "auto"},
    )

    assert r.status_code == 200, r.text
    assert r.json()["route_plan"]["kind"] == "revise"
    assert seen == ["signal"]


def test_run_multi_step_kicks_second_build_with_prior_run(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    intents: list[str] = []

    def _fake_pipeline(
        *_a, run_id: str, output_mode: str, intent: str, **_kw
    ):
        calls.append((run_id, output_mode))
        intents.append(intent)
        out = repo_root / "runs" / "out" / run_id
        logs = repo_root / "runs" / "logs" / run_id
        meta_path = out / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({"status": "ok", "stage": "ok"})
        if output_mode == "report":
            meta["selection_manifest"] = {
                "evidence_ids": ["doc:current:0"],
                "dialogue_ids": [],
                "scores": {},
                "quotas": {},
                "hashes": {"doc:current": "hash_parent_01"},
                "omitted": [],
            }
            meta["source_catalog_hashes"] = {"doc:current": "hash_parent_01"}
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        meta_path.write_text(payload, encoding="utf-8")
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
        return out

    monkeypatch.setattr(api_mod, "run_pipeline", _fake_pipeline)
    monkeypatch.setattr(api_mod, "_auto_kick_presentation_slides", lambda _rid: None)

    r = client.post(
        "/api/run",
        data={
            "source_text": "Минская 10, Гомельская 20",
            "intent": "Сделай отчёт и презентацию",
            "output_mode": "auto",
            "max_charts": "0",
            "max_images": "0",
            "max_diagrams": "0",
            "forbid_charts": "true",
            "forbid_images": "true",
            "dry_run": "true",
        },
    )
    assert r.status_code == 202, r.text
    parent_run_id = r.json()["run_id"]

    import time

    for _ in range(100):
        if len(calls) >= 2:
            break
        time.sleep(0.02)

    assert [mode for _, mode in calls] == ["report", "presentation"]
    assert "РЕЖИМ ПРЕЗЕНТАЦИЯ" in intents[1]
    assert "РЕЖИМ ОТЧЁТ" not in intents[1]
    child_run_id = calls[1][0]
    child_meta = json.loads(
        (repo_root / "runs" / "out" / child_run_id / "meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert child_meta["prior_run_id"] == parent_run_id
    assert child_meta["route_plan"]["parent_run_id"] == parent_run_id
    assert child_meta["route_plan"]["step_index"] == 1
    assert child_meta["route_plan"]["pending_steps"] == []
    assert child_meta["source_catalog_hashes"] == {"doc:current": "hash_parent_01"}
    parent_meta = json.loads(
        (repo_root / "runs" / "out" / parent_run_id / "meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert parent_meta["selection_manifest"]["hashes"] == child_meta["source_catalog_hashes"]


def test_run_presentation_waits_for_slides_before_next_report(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading
    import time

    calls: list[tuple[str, str]] = []
    slides_started = threading.Event()

    def _fake_pipeline(*_a, run_id: str, output_mode: str, **_kw):
        calls.append((run_id, output_mode))
        out = repo_root / "runs" / "out" / run_id
        logs = repo_root / "runs" / "logs" / run_id
        meta_path = out / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({"status": "ok", "stage": "ok"})
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        meta_path.write_text(payload, encoding="utf-8")
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
        return out

    def _fake_auto_kick(run_id: str) -> None:
        path = repo_root / "runs" / "out" / run_id / "meta.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta["slides_status"] = "running"
        path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        slides_started.set()

    monkeypatch.setattr(api_mod, "run_pipeline", _fake_pipeline)
    monkeypatch.setattr(api_mod, "_auto_kick_presentation_slides", _fake_auto_kick)
    r = client.post(
        "/api/run",
        data={
            "source_text": "Минская 10, Гомельская 20",
            "intent": "Сделай презентацию и отчёт",
            "output_mode": "auto",
            "max_charts": "0",
            "max_images": "0",
            "max_diagrams": "0",
            "forbid_charts": "true",
            "forbid_images": "true",
            "dry_run": "true",
        },
    )
    assert r.status_code == 202, r.text
    parent_run_id = r.json()["run_id"]
    assert slides_started.wait(timeout=1)
    time.sleep(0.08)
    assert [mode for _, mode in calls] == ["presentation"]

    path = repo_root / "runs" / "out" / parent_run_id / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["slides_status"] = "ok"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    for _ in range(100):
        if len(calls) >= 2:
            break
        time.sleep(0.02)
    assert [mode for _, mode in calls] == ["presentation", "report"]


def test_run_three_primaries_surfaces_truncation_note(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_spawn(job, slot_gen=None):
        api_mod._release_pipeline_slot(job.run_id, generation=slot_gen)

    monkeypatch.setattr(api_mod, "_spawn_pipeline_thread", _fake_spawn)
    r = client.post(
        "/api/run",
        data={
            "source_text": "Минская 10, Гомельская 20",
            "intent": "Сделай отчёт, презентацию и схему",
            "output_mode": "auto",
            "dry_run": "true",
        },
    )

    assert r.status_code == 202, r.text
    body = r.json()
    assert "схем" in body["chat_summary"].lower()
    assert body["route_plan"]["note"] == body["chat_summary"]


def test_run_multi_step_queue_full_is_visible_on_parent(
    client: TestClient, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_pipeline(*_a, run_id: str, **_kw):
        out = repo_root / "runs" / "out" / run_id
        logs = repo_root / "runs" / "logs" / run_id
        meta_path = out / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({"status": "ok", "stage": "ok"})
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        meta_path.write_text(payload, encoding="utf-8")
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
        return out

    reserve = api_mod._reserve_run_turn
    reservations = 0

    def _reserve_then_reject_child() -> tuple[str, str | None]:
        nonlocal reservations
        reservations += 1
        if reservations == 1:
            return reserve()
        return "busy", "other_run"

    monkeypatch.setattr(api_mod, "run_pipeline", _fake_pipeline)
    monkeypatch.setattr(api_mod, "_reserve_run_turn", _reserve_then_reject_child)

    r = client.post(
        "/api/run",
        data={
            "source_text": "Минская 10, Гомельская 20",
            "intent": "Сделай отчёт и презентацию",
            "output_mode": "auto",
            "max_charts": "0",
            "max_images": "0",
            "max_diagrams": "0",
            "forbid_charts": "true",
            "forbid_images": "true",
            "dry_run": "true",
        },
    )
    assert r.status_code == 202, r.text
    parent_run_id = r.json()["run_id"]

    import time

    parent_meta: dict = {}
    for _ in range(100):
        meta_path = repo_root / "runs" / "out" / parent_run_id / "meta.json"
        if meta_path.is_file():
            parent_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if parent_meta.get("route_plan", {}).get("chain_error"):
                break
        time.sleep(0.02)

    route = parent_meta["route_plan"]
    assert route["chain_error"]
    assert "очеред" in route["chain_error"].lower()
    assert route["pending_steps"][0]["kind"] == "presentation"
    assert "next_run_id" not in route
    status = client.get(f"/api/runs/{parent_run_id}/status")
    assert status.status_code == 200
    assert status.json()["route_plan"]["chain_error"] == route["chain_error"]


def test_run_rejects_second_while_busy(client: TestClient, monkeypatch) -> None:
    """Under CASE3_MAX_CONCURRENT_RUNS=1, second queues and third gets 409."""
    monkeypatch.setenv("CASE3_MAX_CONCURRENT_RUNS", "1")
    monkeypatch.setenv("CASE3_MAX_QUEUED_RUNS", "1")
    assert api_mod._claim_pipeline_slot("holder_test") is None
    started: list[str] = []

    def _fake_bg(**kwargs: object) -> None:
        started.append(str(kwargs["run_id"]))

    original = api_mod._bg_run_pipeline
    api_mod._bg_run_pipeline = _fake_bg  # type: ignore[assignment]
    try:
        r = client.post(
            "/api/run",
            data={
                "source_text": "Выручка 10",
                "intent": "Сделай отчёт",
                "output_mode": "report",
                "max_charts": "0",
                "max_images": "0",
                "forbid_charts": "true",
                "forbid_images": "true",
                "dry_run": "true",
                "formats": "both",
            },
        )
        assert r.status_code == 202, r.text
        assert r.json()["status"] == "queued"
        assert r.json()["waiting_for"] == "holder_test"
        assert started == []
        third = client.post(
            "/api/run",
            data={
                "source_text": "Выручка 20",
                "intent": "Сделай второй отчёт",
                "output_mode": "report",
                "dry_run": "true",
            },
        )
        assert third.status_code == 409, third.text
        detail = third.json().get("detail") or ""
        assert "уже ждёт" in detail
        assert "Этот запрос не поставлен" in detail
        assert "перезапуск" not in detail
        assert "holder_test" not in detail
    finally:
        # Release/drain queued waiter while _fake_bg is still stubbed so no real thread escapes.
        api_mod._release_pipeline_slot("holder_test")
        if api_mod._PIPELINE_SLOT.locked():
            api_mod._release_pipeline_slot()
        for _ in range(25):
            if started:
                break
            import time

            time.sleep(0.01)
        api_mod._bg_run_pipeline = original


def test_chart_edit_404_missing_run(client: TestClient) -> None:
    r = client.post(
        "/api/runs/missing_run_20260101T000000Z/charts/cht_01/edit",
        json={"palette": "atelier", "formats": "both"},
    )
    assert r.status_code == 404


def test_table_edit_404_missing_run(client: TestClient) -> None:
    r = client.post(
        "/api/runs/missing_run_20260101T000000Z/tables/1/edit",
        json={
            "caption": "T",
            "headers": ["A"],
            "rows": [["1"]],
            "formats": "both",
        },
    )
    assert r.status_code == 404
