"""Deck job must catch model refusal and bad JSON without a NameError."""

from __future__ import annotations

import json
from pathlib import Path

from case3.slides_job import run_slides_job


class _Replies:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)

    def complete(self, **_kwargs: object) -> str:
        if not self.texts:
            raise AssertionError("LLM called more times than scripted")
        return self.texts.pop(0)


def _seed(tmp_path: Path, run_id: str) -> None:
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    src = tmp_path / "runs" / "uploads" / run_id / "source.txt"
    src.parent.mkdir(parents=True)
    src.write_text("Выручка: Минск 120, Гродно 80, Брест 40.", encoding="utf-8")
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "ok",
                "stage": "ok",
                "source": str(src),
                "intent": "",
                "output_mode": "presentation",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_slides_insufficient_data_is_a_quiet_ok(tmp_path: Path) -> None:
    run_id = "slides_thin"
    _seed(tmp_path, run_id)
    run_slides_job(
        run_id,
        root=tmp_path,
        llm=_Replies(
            '{"status":"insufficient_data","message":"Мало фактов для деки."}'
        ),
    )
    meta = json.loads(
        (tmp_path / "runs" / "out" / run_id / "meta.json").read_text()
    )
    assert meta["slides_status"] == "ok"
    assert "Мало фактов" in (meta.get("chat_summary") or "")
    assert "not defined" not in json.dumps(meta, ensure_ascii=False)


def test_slides_job_uses_gcp_block_before_brief(tmp_path: Path, monkeypatch) -> None:
    run_id = "slides_gcp"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    src = tmp_path / "source.txt"
    src.write_text(
        "===== Документ 1: A.md =====\nВыручка 10\n"
        "===== Документ 2: B.md =====\nЗапас 99\n",
        encoding="utf-8",
    )
    seen: list[str] = []

    def _system_prompt(*, source: str, **_kw):
        seen.append(source)
        return "SYSTEM"

    monkeypatch.setattr("case3.slides_job.load_slides_system_prompt", _system_prompt)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "ok",
                "stage": "ok",
                "source": str(src),
                "intent": "Только по первому",
                "output_mode": "presentation",
                "gcp_build_block": "## Выбранные источники\n### [doc:a] A\nВыручка 10",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    run_slides_job(
        run_id,
        root=tmp_path,
        llm=_Replies(
            '{"status":"insufficient_data","message":"Мало фактов для деки."}'
        ),
    )
    assert seen
    prompt = seen[0]
    gcp_pos = prompt.index("## Выбранные источники")
    brief_pos = prompt.index("===== Документ 1:")
    assert gcp_pos < brief_pos
    assert "Выручка 10" in prompt[gcp_pos:brief_pos]


def test_slides_bad_json_records_the_parse_error(tmp_path: Path) -> None:
    run_id = "slides_nojson"
    _seed(tmp_path, run_id)
    run_slides_job(
        run_id,
        root=tmp_path,
        llm=_Replies("не json", "тоже не json"),
    )
    meta = json.loads(
        (tmp_path / "runs" / "out" / run_id / "meta.json").read_text()
    )
    err = meta.get("slides_error") or ""
    assert meta["slides_status"] == "error"
    assert "JSON" in err
    assert "not defined" not in err
