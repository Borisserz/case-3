from case3.chat_turn import opening_fallback, try_chat_answer, try_opening


class _Fake:
    def __init__(self, text: str) -> None:
        self.text = text

    def stream(self, **_kwargs):
        yield self.text


def test_opening_fallback_does_not_claim_the_file_is_done():
    line = opening_fallback("presentation", "Выручка 10 и 12")
    assert "презентац" in line.lower()
    assert "готово" not in line.lower()
    assert "10" in line


def test_bad_opening_is_replaced_and_only_the_fallback_is_emitted():
    seen: list[str] = []
    text = try_opening(
        "report",
        "Собери отчёт по выручке 10",
        client=_Fake("Готово. PDF готов, можно скачивать."),
        on_delta=seen.append,
    )
    assert text == seen[0]
    assert "готово" not in text.lower()
    assert "отч" in text.lower()


def test_section_draft_keeps_only_numbers_already_in_the_text():
    from case3.chat_turn import draft_section

    allowed = "Выручка была 10, стала 12."
    kept = draft_section(
        section="Введение",
        current=allowed,
        source="Выручка была 10, стала 12.",
        brief="clearer",
        client=_Fake(
            "Выручка была 10, затем стала 12. Других цифр в тексте нет."
        ),
    )
    assert "10" in kept and "12" in kept

    rejected = draft_section(
        section="Введение",
        current=allowed,
        source=allowed,
        brief="clearer",
        client=_Fake("Выручка выросла на 20 процентов, с 10 до 12."),
    )
    assert rejected == ""


def test_chat_answer_uses_the_model_text():
    seen: list[str] = []
    answer = (
        "Выручка выросла с 10 до 12. "
        "Доля рынка в тексте не указана, поэтому её не считаю."
    )
    text = try_chat_answer(
        "Выручка 10, потом 12.",
        "Проанализируй динамику",
        client=_Fake(answer),
        on_delta=seen.append,
    )
    assert text == answer
    assert seen == [answer]
