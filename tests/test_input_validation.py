from __future__ import annotations

import pytest

from case3.input_validation import validate_input_heuristics


def test_empty_and_whitespace():
    valid, msg = validate_input_heuristics("", "")
    assert not valid
    assert "недостаточно данных" in msg.lower()

    valid, msg = validate_input_heuristics("   \n\t  ", "   ")
    assert not valid
    assert "недостаточно данных" in msg.lower()


def test_short_garbage():
    for garbage in ["а", "1", "...", "йц", "abc"]:
        valid, msg = validate_input_heuristics(garbage, "")
        assert not valid
        assert "недостаточно данных" in msg.lower()


def test_repetitive_keyboard_smash():
    for smash in ["aaaaaaa", "asdfasdfasdf", "йцукенйцукен", "ахахахахахах"]:
        valid, msg = validate_input_heuristics(smash, "")
        assert not valid
        assert "недостаточно данных" in msg.lower()


def test_pure_greetings_and_intent_triggers():
    triggers = [
        "привет",
        "здравствуйте",
        "ку",
        "hello",
        "сделай отчет",
        "отчет",
        "презентация",
        "сделай презу",
        "схема",
        "покажи схему",
        "сделай красиво",
        "как дела",
        "тест",
        "Привет, сделай отчет пожалуйста",
        "Сделай презентацию",
    ]
    for text in triggers:
        valid, msg = validate_input_heuristics(text, "")
        assert not valid, f"Expected invalid for '{text}'"
        assert "недостаточно данных" in msg.lower()


def test_mode_tailored_message():
    _, msg_report = validate_input_heuristics("привет", "", output_mode="report")
    assert "отчёта" in msg_report.lower() or "отчета" in msg_report.lower()

    _, msg_deck = validate_input_heuristics("привет", "", output_mode="presentation")
    assert "презентации" in msg_deck.lower()

    _, msg_diag = validate_input_heuristics("привет", "", output_mode="diagram")
    assert "схемы" in msg_diag.lower()


def test_silly_or_informal_requests_with_numbers_pass():
    queries = [
        "Вася съел 3 яблока, Маша 5 груш. Сделай отчет",
        "наш стартап заработал 100 баксов за январь и 200 за февраль",
        "было 10 пользователей, стало 50",
        "в 2024 году рост составил 15%",
        "3 шага: шаг 1 регистрация, шаг 2 оплата, шаг 3 получение",
    ]
    for text in queries:
        valid, msg = validate_input_heuristics(text, "")
        assert valid, f"Expected valid for '{text}', got msg: {msg}"
        assert msg is None


def test_bullet_points_and_tables_pass():
    structured = (
        "- пункт 1\n"
        "- пункт 2\n"
        "- пункт 3"
    )
    valid, msg = validate_input_heuristics(structured, "")
    assert valid
    assert msg is None

    table = (
        "Имя | Роль\n"
        "Иван | Разработчик\n"
        "Ольга | Дизайнер"
    )
    valid, msg = validate_input_heuristics(table, "")
    assert valid
    assert msg is None


def test_substantial_descriptive_text_passes():
    text = "Система управления складом включает модуль учета остатков, интерфейс оператора и интеграцию с 1С."
    valid, msg = validate_input_heuristics(text, "")
    assert valid
    assert msg is None


def test_attachments_do_not_bypass_heuristic_check_when_data_free():
    valid, msg = validate_input_heuristics("привет", "", has_attachments=True)
    assert not valid
    assert "недостаточно данных" in msg.lower()

    valid, msg = validate_input_heuristics("ывафыавфа", "", has_attachments=True)
    assert not valid
    assert "недостаточно данных" in msg.lower()


def test_attachments_with_meaningful_request_pass():
    valid, msg = validate_input_heuristics(
        "Вот фото цеха, составь отчет о запуске линии упаковки",
        "",
        has_attachments=True,
    )
    assert valid
    assert msg is None
