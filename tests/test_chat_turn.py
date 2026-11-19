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


class _Seq:
    def __init__(self, texts: list[str]) -> None:
        self.texts = list(texts)
        self.calls = 0
        self.seen: list[str] = []

    def stream(self, **kwargs):
        self.calls += 1
        self.seen.append(kwargs.get("user_text") or "")
        yield self.texts.pop(0)


class _Boom:
    def stream(self, **_kwargs):
        raise AssertionError("model should not be called")
        yield ""


def test_chat_answer_asks_instead_of_inventing_a_percent():
    seen: list[str] = []
    client = _Seq(
        [
            "Выручка выросла на 20% , с 10 до 12.",
            "Выручка выросла на 20 процентов.",
        ]
    )
    text = try_chat_answer(
        "Выручка была 10, стала 12.",
        "Проанализируй динамику",
        client=client,
        on_delta=seen.append,
    )
    assert client.calls == 2
    assert "20" in text
    assert "нет" in text.lower()
    assert "выросла на 20" not in text.lower()
    assert seen == [text]


def test_chat_answer_retries_once_and_keeps_a_clean_second_draft():
    client = _Seq(
        [
            "Выручка выросла на 20%, с 10 до 12.",
            "Выручка была 10, затем стала 12. Новую долю не считаю.",
        ]
    )
    text = try_chat_answer(
        "Выручка была 10, стала 12.",
        "Проанализируй динамику",
        client=client,
    )
    assert client.calls == 2
    assert text.startswith("Выручка была 10")
    assert "20" not in text


def test_chat_answer_keeps_a_number_the_user_added():
    client = _Seq(["Открыли 3 точки. Касса в документе 20."])
    text = try_chat_answer(
        "Касса 20.",
        "Учти, что открыли 3 точки, и разбери кассу",
        client=client,
    )
    assert text.startswith("Открыли 3")
    assert client.calls == 1


def test_chat_answer_asks_when_the_user_disagrees_with_the_document():
    text = try_chat_answer(
        "Касса была 20, выручка 12.",
        "Касса была 40, разбери",
        client=_Boom(),
    )
    assert "20" in text and "40" in text
    assert "оставить" in text


def test_slide_number_does_not_look_like_a_fact_conflict():
    client = _Seq(["Касса 20. Это про третий слайд."])
    text = try_chat_answer(
        "Касса 20.",
        "почему слайд 3 про кассу",
        client=client,
    )
    assert text.startswith("Касса 20")
    assert "оставить" not in text


def test_choosing_the_document_number_drops_the_rejected_one():
    prior = (
        "20\n\n"
        "Разговор этого чата (не Source).\n"
        "Ход 1. Запрос: касса была 40\n"
        "Ответ: В документе у «касса» стоит 20, ты написал 40. "
        "Напиши 40, чтобы оставить твоё, или 20, чтобы оставить документ."
    )
    client = _Seq(
        [
            "Оставляю 40, как ты писал раньше.",
            "Оставляю 40 снова.",
        ]
    )
    text = try_chat_answer(
        "Касса была 20.",
        prior,
        client=client,
    )
    assert "нет" in text.lower()
    assert "40" in text
    assert "Оставляю 40" not in text
    assert any("выбрал 20" in blob for blob in client.seen)


def test_section_draft_keeps_a_number_the_user_wrote():
    from case3.chat_turn import draft_section

    kept = draft_section(
        section="Введение",
        current="Касса была 20.",
        source="Касса была 20.",
        brief="clearer",
        user_text="поставь в кассе 40",
        client=_Fake("В кассе теперь 40."),
    )
    assert "40" in kept


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
