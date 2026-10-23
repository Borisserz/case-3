"""Slides job API: 409 when report not ok; 202 + offline when ok."""

from __future__ import annotations

import json
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


def _seed_ok_run(
    tmp_path: Path, run_id: str, *, source: str = "Выручка 120 млн. Доля 35%."
) -> Path:
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    src = tmp_path / "runs" / "uploads" / run_id / "source.txt"
    src.parent.mkdir(parents=True)
    src.write_text(source, encoding="utf-8")
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "ok",
                "stage": "ok",
                "source": str(src),
                "intent": "- палитра графиков: Atelier (atelier)",
                "charts_planned": [],
                "figures_planned": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "report.pdf").write_bytes(b"%PDF-1.4 fake")
    return out


def test_slides_crash_writes_error(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_slides_crash"
    _seed_ok_run(tmp_path, run_id)

    def _boom(rid: str, **_kw: object) -> None:
        raise RuntimeError("simulated slides crash")

    monkeypatch.setattr("case3.slides_job.run_slides_job", _boom)

    r = client.post(f"/api/runs/{run_id}/slides")
    assert r.status_code == 202, r.text

    import time

    body: dict = {}
    for _ in range(80):
        st = client.get(f"/api/runs/{run_id}/status")
        body = st.json()
        if body.get("slides_status") == "error":
            break
        time.sleep(0.05)
    assert body.get("slides_status") == "error"
    assert "simulated slides crash" in (body.get("slides_error") or "")


def test_slides_409_when_not_ok(client: TestClient, tmp_path: Path) -> None:
    run_id = "run_bad"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "status": "running", "stage": "llm"}),
        encoding="utf-8",
    )
    r = client.post(f"/api/runs/{run_id}/slides")
    assert r.status_code == 409


def test_slides_202_and_offline_job(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_slides_ok"
    _seed_ok_run(tmp_path, run_id)

    def _fake_pngs(deck, *, work_root, out_dir, chart_png_by_id=None, media_png_by_id=None, **_kw):
        from PIL import Image

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, _slide in enumerate(deck.get("slides") or [], start=1):
            p = out_dir / f"slide_{i:02d}.png"
            Image.new("RGB", (64, 36), (40, 80, 40)).save(p)
            paths.append(p)
        return paths

    monkeypatch.setattr("case3.slides_job.render_deck_pngs", _fake_pngs)

    def _fake_job(rid: str) -> None:
        from case3.slides_job import run_slides_job

        run_slides_job(
            rid,
            root=tmp_path,
            skip_llm_ir={
                "version": 1,
                "aspect": "16:9",
                "palette": "atelier",
                "language": "ru",
                "slides": [
                    {
                        "id": "s01",
                        "layout": "title",
                        "title": "Итоги",
                        "subtitle": "Кратко",
                    },
                    {
                        "id": "s02",
                        "layout": "kpi_row",
                        "title": "Цифры",
                        "kpis": [
                            {"label": "Выручка", "value": "120 млн"},
                            {"label": "Доля", "value": "35%"},
                        ],
                    },
                    {
                        "id": "s03",
                        "layout": "bullets",
                        "title": "Факты",
                        "bullets": ["Выручка 120 млн"],
                    },
                    {
                        "id": "s04",
                        "layout": "closing",
                        "title": "Далее",
                        "bullets": ["Шаг"],
                    },
                ],
            },
        )

    monkeypatch.setattr(api_mod, "_bg_run_slides", _fake_job)

    r = client.post(f"/api/runs/{run_id}/slides")
    assert r.status_code == 202, r.text
    assert r.json()["slides_status"] == "running"
    assert r.json()["slides_stage"] == "starting"

    # Daemon thread — poll until job finishes (TestClient no longer awaits BackgroundTasks).
    import time

    body: dict = {}
    for _ in range(80):
        st = client.get(f"/api/runs/{run_id}/status")
        assert st.status_code == 200
        body = st.json()
        if body.get("slides_status") in {"ok", "error"}:
            break
        time.sleep(0.05)
    assert body.get("slides_status") == "ok", body.get("slides_error") or body
    assert "pptx" in (body.get("downloads") or {})
    assert "deck_pdf" in (body.get("downloads") or {})
    assert "pdf" in (body.get("downloads") or {})
    assert body["downloads"]["pdf"].endswith("report.pdf")

    g = client.get(f"/api/runs/{run_id}/slides")
    assert g.status_code == 200
    assert g.json()["deck"]["slides"][0]["layout"] == "title"
    assert len(g.json()["slide_pngs"]) == 4


def test_downloads_do_not_collide_deck_pdf(client: TestClient, tmp_path: Path) -> None:
    run_id = "run_collide"
    out = _seed_ok_run(tmp_path, run_id)
    (out / "report_deck.pdf").write_bytes(b"%PDF deck")
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    meta["slides_status"] = "ok"
    meta["slides_artifacts"] = {
        "pptx": "report_slides.pptx",
        "deck_pdf": "report_deck.pdf",
    }
    (out / "report_slides.pptx").write_bytes(b"PK fake")
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    st = client.get(f"/api/runs/{run_id}/status")
    d = st.json()["downloads"]
    assert d["pdf"].endswith("report.pdf")
    assert d["deck_pdf"].endswith("report_deck.pdf")
    assert d["pptx"].endswith("report_slides.pptx")
