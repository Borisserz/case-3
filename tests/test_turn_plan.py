# tests/test_turn_plan.py
import pytest

from case3.turn_plan import format_route_projection, plan_turn


def test_format_route_projection_report_goal():
    p = plan_turn("Сделай отчёт по цифрам", mode_hint="auto")
    text = format_route_projection(p)
    assert "цель: отчёт" in text
    assert text.startswith("Маршрут:")


def test_format_route_projection_clarify_empty():
    p = plan_turn("построй график по регионам", mode_hint="auto", bias="report")
    assert p.kind == "clarify"
    assert format_route_projection(p) == ""


def test_format_route_projection_chat_chart_flags():
    p = plan_turn("Построй график по областям", mode_hint="auto")
    text = format_route_projection(p)
    assert "цель: чат" in text
    assert "в чате: график" in text


def test_auto_report_and_presentation_from_language():
    p = plan_turn("Сделай отчёт по цифрам", mode_hint="auto")
    assert p.kind == "report"
    assert [s.kind for s in p.steps] == ["report"]

    p = plan_turn("Собери презентацию", mode_hint="auto")
    assert p.kind == "presentation"


def test_bare_primary_artifact_noun_builds_that_artifact():
    assert plan_turn("Отчёт", mode_hint="auto").kind == "report"
    assert plan_turn("Презентация", mode_hint="auto").kind == "presentation"


def test_question_stays_chat_under_report_hint():
    p = plan_turn("Какая доля Минской?", mode_hint="report", bias="report")
    assert p.kind == "chat"


def test_analyze_plus_plaque_builds(adr_0017):
    p = plan_turn("проанализируй регионы", mode_hint="auto", bias="report")
    assert p.kind == "report"


def test_analyze_named_report_stays_chat_under_report_plaque(adr_0017):
    p = plan_turn("Проанализируй отчёт", mode_hint="auto", bias="report")
    assert p.kind == "chat"


@pytest.mark.parametrize("text", ["ещё точнее", "короче", "тот раздел короче"])
def test_report_followup_uses_remembered_section(text: str):
    p = plan_turn(
        text,
        mode_hint="auto",
        has_report=True,
        last_section="Введение",
        last_op="rewrite",
    )
    assert p.kind == "revise"
    assert p.edit_act is not None
    assert p.edit_act.op == "rewrite"
    assert p.edit_act.section == "Введение"


def test_deck_followup_uses_remembered_restyle():
    p = plan_turn(
        "ещё",
        mode_hint="auto",
        has_deck=True,
        last_op="recolor_deck",
    )
    assert p.kind == "revise"
    assert p.edit_act is not None
    assert p.edit_act.op == "recolor_deck"


def test_bare_chart_auto_is_chat_chart():
    p = plan_turn("Построй график по областям", mode_hint="auto")
    assert p.kind == "chat"
    assert p.want_chat_chart is True


def test_make_chart_linear_is_revise_when_prior_chart():
    p = plan_turn(
        "сделай график линейным",
        mode_hint="auto",
        has_chart=True,
    )
    assert p.kind == "revise"
    assert p.edit_act is not None
    assert p.edit_act.op in {"retype_chart", "retype_charts"}
    assert p.edit_act.chart == "line"


def test_new_linear_chart_is_chat_not_revise():
    p = plan_turn(
        "сделай новый линейный график",
        mode_hint="auto",
        has_chart=True,
    )
    assert p.kind == "chat"
    assert p.want_chat_chart is True
    assert p.edit_act is None


def test_report_plaque_plus_chart_clarifies():
    p = plan_turn("построй график по регионам", mode_hint="auto", bias="report")
    assert p.kind == "clarify"
    assert p.clarify_prompt == (
        "Построить график в чате или добавить в отчёт? "
        "Напишите «график в чате» или «график в отчёте»."
    )


def test_presentation_plaque_plus_chart_clarifies():
    p = plan_turn("построй график по регионам", mode_hint="auto", bias="presentation")
    assert p.kind == "clarify"
    assert p.clarify_prompt == (
        "Построить график в чате или добавить в презентацию? "
        "Напишите «график в чате» или «график в презентации»."
    )


def test_report_mode_hint_plus_chart_clarifies_without_bias():
    p = plan_turn("построй график по регионам", mode_hint="report")
    assert p.kind == "clarify"
    assert "добавить в отчёт" in (p.clarify_prompt or "")


def test_explicit_mode_hint_wins_conflicting_bias_for_clarify():
    p = plan_turn(
        "построй график по регионам",
        mode_hint="presentation",
        bias="report",
    )
    assert p.kind == "clarify"
    assert "добавить в презентацию" in (p.clarify_prompt or "")


def test_explicit_in_chat_under_plaque_is_chat():
    p = plan_turn("построй график в чате", mode_hint="auto", bias="report")
    assert p.kind == "chat"
    assert p.want_chat_chart is True


def test_explicit_in_report_under_plaque_is_report():
    p = plan_turn("построй график в отчёте", mode_hint="auto", bias="report")
    assert p.kind == "report"
    assert p.build_media.get("chart") is True


def test_named_report_with_chart_under_plaque_is_report():
    p = plan_turn("Сделай отчёт с графиком продаж", mode_hint="auto", bias="report")
    assert p.kind == "report"
    assert p.build_media.get("chart") is True


def test_bare_diagramma_is_chat_chart():
    p = plan_turn("Нарисуй диаграмму", mode_hint="auto")
    assert p.kind == "chat"
    assert p.want_chat_chart is True


def test_process_diagramma_is_diagram_mode():
    p = plan_turn("Нарисуй диаграмму процесса оплаты", mode_hint="auto")
    assert p.kind == "diagram"


def test_schema_is_diagram_mode():
    p = plan_turn("Нарисуй схему онбординга", mode_hint="auto")
    assert p.kind == "diagram"


def test_schema_in_chat_is_chat_diagram():
    p = plan_turn("Покажи схему онбординга в чате", mode_hint="auto")
    assert p.kind == "chat"
    assert p.want_chat_diagram is True


def test_report_and_presentation_ordered():
    p = plan_turn("Сделай отчёт и презентацию", mode_hint="auto")
    assert [s.kind for s in p.steps] == ["report", "presentation"]
    assert p.kind == "report"
    assert p.reason == "multi_primary"


def test_presentation_and_report_reversed():
    p = plan_turn("Сделай презентацию и отчёт", mode_hint="auto")
    assert [s.kind for s in p.steps] == ["presentation", "report"]
    assert p.kind == "presentation"
    assert p.reason == "multi_primary"


def test_report_with_schema_stays_single_report():
    p = plan_turn("Сделай отчёт с таблицей и схемой", mode_hint="auto")
    assert p.kind == "report"
    assert len(p.steps) == 1
    assert p.build_media.get("diagram") is True


def test_three_container_primaries_caps_at_two_in_order():
    p = plan_turn("Сделай отчёт, презентацию и схему", mode_hint="auto")
    assert p.reason == "multi_primary"
    assert p.kind == "report"
    assert len(p.steps) == 2
    assert [s.kind for s in p.steps] == ["report", "presentation"]
    assert p.note
    assert "схем" in p.note.lower()