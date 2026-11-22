from case3.turn_route import resolve_turn


def test_word_and_spravka_leave_chat():
    assert resolve_turn("Сделай word", None) == "report"
    assert resolve_turn("сделай справку по областям", None) == "report"
    assert resolve_turn("Собери ворд", None) == "report"
    assert resolve_turn("что в справке?", "report") == "chat"


def test_a_question_does_not_rebuild_because_the_plaque_is_on():
    assert resolve_turn("Какая доля Минской?", "report") == "chat"
    assert resolve_turn("что в отчёте по Гомельской", "report") == "chat"
    assert resolve_turn("что на слайде", "presentation") == "chat"


def test_question_stays_chat_even_if_plaque_is_report():
    assert resolve_turn("Проанализируй отчёт и разложи цифры", "report") == "chat"


def test_explicit_deck_wins_over_plaque_and_over_analyze():
    assert resolve_turn("Проанализируй и собери презентацию", "report") == "presentation"


def test_a_chart_request_builds_a_report_and_a_scheme_stays_a_scheme():
    assert resolve_turn("Построй график по областям", None) == "report"
    assert resolve_turn("Нарисуй диаграмму продаж", None) == "report"
    assert resolve_turn("Нарисуй схему онбординга", None) == "diagram"


def test_explicit_diagram_and_report():
    assert resolve_turn("Нарисуй схему онбординга", None) == "diagram"
    assert resolve_turn("Напиши отчёт по этим цифрам", None) == "report"


def test_plaque_is_the_default_when_the_text_names_no_action():
    assert resolve_turn("Выручка 10 и 12, доля 30%", "presentation") == "presentation"
    assert resolve_turn("Выручка 10 и 12, доля 30%", None) == "chat"


def test_bare_artifact_noun_without_analyze_is_a_request():
    assert resolve_turn("Нужна схема процесса оплаты", None) == "diagram"


def test_empty_message_uses_plaque_or_chat():
    assert resolve_turn("", "diagram") == "diagram"
    assert resolve_turn("   ", None) == "chat"


def test_negated_artifact_is_not_a_request():
    assert resolve_turn("не делай отчёт, просто разбери цифры", None) == "chat"
    assert resolve_turn("без схемы, расскажи про оплату", "diagram") == "chat"
    assert resolve_turn("не презентацию, сделай отчёт", None) == "report"


def test_describe_stays_chat_even_if_the_noun_is_present():
    assert resolve_turn("Опиши отчёт по этим цифрам", "report") == "chat"
    assert resolve_turn("Кратко сделай презу", None) == "presentation"
