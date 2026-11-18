from case3.turn_route import resolve_turn


def test_question_stays_chat_even_if_plaque_is_report():
    assert resolve_turn("Проанализируй отчёт и разложи цифры", "report") == "chat"


def test_explicit_deck_wins_over_plaque_and_over_analyze():
    assert resolve_turn("Проанализируй и собери презентацию", "report") == "presentation"


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
