import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from case3.artifact_context import resolve_artifact_targets
from case3.chat_act import ChatAct
from case3.turn_plan import plan_turn


def _write_run(
    root: Path,
    run_id: str,
    *,
    prior_run_id: str = "",
    meta: dict | None = None,
) -> Path:
    out_dir = root / "runs" / "out" / run_id
    out_dir.mkdir(parents=True)
    payload = {"run_id": run_id, "prior_run_id": prior_run_id}
    payload.update(meta or {})
    (out_dir / "meta.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_dir


def test_resolves_slide_number_to_newest_deck(tmp_path: Path) -> None:
    deck_id = "source_20261124T100000Z"
    deck_dir = _write_run(
        tmp_path,
        deck_id,
        meta={"output_mode": "presentation", "slides_status": "ok"},
    )
    slides_dir = deck_dir / "slides"
    slides_dir.mkdir()
    (slides_dir / "deck.json").write_text(
        json.dumps(
            {
                "slides": [
                    {"id": "s01", "title": "Обзор"},
                    {"id": "s02", "title": "Данные"},
                    {"id": "s03", "title": "Старые итоги"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    plan = plan_turn(
        "поменяй заголовок слайда 3 на Новые итоги",
        has_deck=True,
    )

    targets = resolve_artifact_targets(
        plan=plan,
        root=tmp_path,
        prior_run_id=deck_id,
    )

    assert [target.artifact_id for target in targets] == [
        f"artifact:{deck_id}:slide:3"
    ]
    assert targets[0].label == "Слайд 3 — Старые итоги"
    assert targets[0].number_evidence is False


def test_resolves_previous_chart_across_chain(tmp_path: Path) -> None:
    chart_id = "source_20261124T110000Z"
    head_id = "source_20261124T120000Z"
    chart_dir = _write_run(
        tmp_path,
        chart_id,
        meta={"output_mode": "chat", "charts_planned": ["cht_01"]},
    )
    (chart_dir / "figures.json").write_text(
        json.dumps(
            {
                "charts": [
                    {"id": "cht_01", "type": "bar", "caption": "Поступления"}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_run(tmp_path, head_id, prior_run_id=chart_id, meta={"output_mode": "chat"})
    plan = plan_turn(
        "сделай предыдущий график линейным",
        has_chart=True,
    )

    targets = resolve_artifact_targets(
        plan=plan,
        root=tmp_path,
        prior_run_id=head_id,
    )

    assert [target.artifact_id for target in targets] == [
        f"artifact:{chart_id}:cht_01"
    ]
    assert targets[0].label == "График cht_01 — Поступления"
    assert targets[0].number_evidence is False


def test_resolves_named_section_from_report(tmp_path: Path) -> None:
    report_id = "source_20261124T130000Z"
    report_dir = _write_run(
        tmp_path,
        report_id,
        meta={"output_mode": "report", "artifacts": {"pdf": "report.pdf"}},
    )
    (report_dir / "report.tex").write_text(
        "\\section{Введение}\nТекст.\n"
        "\\section{Выводы}\nПроверяемый итог.\n",
        encoding="utf-8",
    )
    plan = plan_turn("перепиши раздел Выводы", has_report=True)

    targets = resolve_artifact_targets(
        plan=plan,
        root=tmp_path,
        prior_run_id=report_id,
    )

    assert [target.artifact_id for target in targets] == [
        f"artifact:{report_id}:section:Выводы"
    ]
    assert targets[0].label == "Раздел «Выводы»"
    assert targets[0].number_evidence is False


@pytest.mark.parametrize(
    ("media_id", "kind", "label"),
    [
        ("dia_01", "diagrams", "Схема dia_01 — Процесс"),
        ("usr_01", "figures", "Фото usr_01 — Экран"),
    ],
)
def test_resolves_explicit_media_id(
    tmp_path: Path,
    media_id: str,
    kind: str,
    label: str,
) -> None:
    run_id = "source_20261124T140000Z"
    out_dir = _write_run(tmp_path, run_id, meta={"output_mode": "report"})
    (out_dir / "figures.json").write_text(
        json.dumps(
            {
                kind: [
                    {
                        "id": media_id,
                        "title": "Процесс",
                        "caption": "Экран",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if media_id.startswith("usr_"):
        figures = out_dir / "figures"
        figures.mkdir()
        (figures / f"{media_id}.png").write_bytes(b"png")
    plan = SimpleNamespace(
        edit_act=ChatAct(kind="revise", op="caption", section=media_id)
    )

    targets = resolve_artifact_targets(
        plan=plan,
        root=tmp_path,
        prior_run_id=run_id,
    )

    assert [target.artifact_id for target in targets] == [
        f"artifact:{run_id}:{media_id}"
    ]
    assert targets[0].label == label
    assert targets[0].number_evidence is False


def test_ambiguous_unnumbered_chart_returns_no_target(tmp_path: Path) -> None:
    run_id = "source_20261124T150000Z"
    out_dir = _write_run(
        tmp_path,
        run_id,
        meta={"output_mode": "report", "charts_planned": ["cht_01", "cht_02"]},
    )
    (out_dir / "figures.json").write_text(
        json.dumps(
            {
                "charts": [
                    {"id": "cht_01", "caption": "Первый"},
                    {"id": "cht_02", "caption": "Второй"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    plan = plan_turn("сделай предыдущий график линейным", has_chart=True)

    assert (
        resolve_artifact_targets(
            plan=plan,
            root=tmp_path,
            prior_run_id=run_id,
        )
        == []
    )
