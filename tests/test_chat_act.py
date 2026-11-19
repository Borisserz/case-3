from case3.chat_act import resolve_act


def test_question_stays_talk_even_with_a_deck():
    act = resolve_act("Почему доля 30%?", has_deck=True, has_report=True)
    assert act.kind == "talk"


def test_new_diagram_is_a_build():
    act = resolve_act("Дай новую схему по этим цифрам", has_diagram=True)
    assert act.kind == "build"
    assert act.build == "diagram"


def test_recolor_deck_names_the_pack():
    act = resolve_act("Перекрась презу в сапфир", has_deck=True)
    assert act.kind == "revise"
    assert act.op == "recolor_deck"
    assert act.pack == "board"
    assert "Northstar" in act.say


def test_recolor_without_a_color_asks():
    act = resolve_act("Измени цвет презентации", has_deck=True)
    assert act.op == "ask"
    assert "Northstar" in act.say


def test_recolor_charts_uses_the_report_palette():
    act = resolve_act("Перекрась графики в закат", has_report=True)
    assert act.op == "recolor_charts"
    assert act.palette == "sunset"


def test_undo_is_short_and_needs_an_artifact():
    assert resolve_act("Отмени", has_report=True).op == "undo"
    assert resolve_act("Отмени", has_report=False).kind == "talk"
    long = resolve_act(
        "Отмени вывод, если доля не 30, и объясни почему выручка стала 12, а не осталась прежней",
        has_report=True,
    )
    assert long.kind == "talk"


def test_rewrite_with_a_section_and_text_is_parsed():
    from case3.chat_act import parse_rewrite

    assert parse_rewrite("Перепиши раздел Введение: выручка была 10, стала 12.") == (
        "Введение",
        "выручка была 10, стала 12.",
    )
    assert parse_rewrite("Перепиши тот раздел") is None
    act = resolve_act("Перепиши тот раздел", has_report=True)
    assert act.op == "ask"
    assert "раздел" in act.say.lower()


def test_named_section_without_new_text_is_a_rewrite():
    redo = resolve_act("мне не нравится, переделай введение", has_report=True)
    assert redo.kind == "revise"
    assert redo.op == "rewrite"
    assert redo.section.casefold() == "введение"
    assert redo.brief != "supplied"

    precise = resolve_act("сделай введение точнее", has_report=True)
    assert precise.op == "rewrite"
    assert precise.section.casefold() == "введение"

    supplied = resolve_act(
        "Перепиши раздел Введение: выручка была 10, стала 12.",
        has_report=True,
    )
    assert supplied.brief == "supplied"
    assert supplied.section == "Введение"


def test_unnamed_section_complaint_asks_which_one():
    act = resolve_act("точнее раздел, мне не нравится", has_report=True)
    assert act.op == "ask"
    assert act.section == ""


def test_make_prettier_cycles_the_deck_when_one_exists():
    both = resolve_act("сделай красивее", has_deck=True, has_report=True)
    assert both.op == "ask"
    assert "текст" in both.say.lower()
    assert "стиль" in both.say.lower()

    report = resolve_act("сделай отчёт красивее", has_deck=True, has_report=True)
    assert report.op == "rewrite"
    assert report.brief == "prettier"

    only_report = resolve_act("сделай красивее", has_report=True)
    assert only_report.op == "rewrite"
    assert only_report.brief == "prettier"

    assert resolve_act("сделай красивее").kind == "talk"


def test_vague_edit_asks_instead_of_building_a_new_file():
    vague = resolve_act("поправь отчёт", has_report=True)
    assert vague.kind == "revise"
    assert vague.op == "ask"
    assert vague.build == ""

    loose = resolve_act("измени вот это", has_report=True, has_deck=True)
    assert loose.op == "ask"
    assert "раздел" in loose.say.lower() or "стиль" in loose.say.lower()


def test_followup_uses_the_last_section():
    again = resolve_act("ещё точнее", has_report=True, last_section="Введение")
    assert again.op == "rewrite"
    assert again.section == "Введение"
    assert again.brief == "clearer"

    shorter = resolve_act(
        "тот раздел короче", has_report=True, last_section="Введение"
    )
    assert shorter.op == "rewrite"
    assert shorter.section == "Введение"
    assert shorter.brief == "tighter"


def test_again_without_a_target_asks():
    act = resolve_act("ещё", has_report=True, has_deck=True)
    assert act.op == "ask"
    assert "Введение" not in act.say


def test_again_repeats_a_deck_restyle():
    act = resolve_act("ещё", has_deck=True, last_op="recolor_deck")
    assert act.op == "recolor_deck"
    assert act.pack == ""


def test_a_question_does_not_become_an_edit():
    act = resolve_act(
        "почему введение слабое?",
        has_report=True,
        last_section="Введение",
    )
    assert act.kind == "talk"
    from case3.chat_act import next_deck_pack

    assert next_deck_pack("atelier") == "board"
    assert next_deck_pack("botanical") == "atelier"
    assert next_deck_pack("pastel") == "ink"
    assert next_deck_pack("") == "board"


def test_bare_shorter_continues_the_last_section():
    shorter = resolve_act("короче", has_report=True, last_section="Введение")
    assert shorter.op == "rewrite"
    assert shorter.section == "Введение"
    assert shorter.brief == "tighter"

    clearer = resolve_act("точнее", has_report=True, last_section="Введение")
    assert clearer.op == "rewrite"
    assert clearer.section == "Введение"
    assert clearer.brief == "clearer"


def test_blue_is_the_northstar_deck():
    act = resolve_act("Перекрась презу в синий", has_deck=True)
    assert act.op == "recolor_deck"
    assert act.pack == "board"


def test_delete_slide_uses_its_place_in_the_deck():
    act = resolve_act("убери второй слайд", has_deck=True)
    assert act.kind == "revise"
    assert act.op == "delete_slide"
    assert act.slide == 2
    assert resolve_act("убери второй слайд").kind == "talk"


def test_new_title_is_taken_from_the_message():
    act = resolve_act("поменяй заголовок на Гомель", has_report=True)
    assert act.op == "retitle"
    assert act.title == "Гомель"
    assert act.title_on == "report"
    missing = resolve_act("поменяй заголовок", has_report=True)
    assert missing.op == "ask"


def test_title_asks_which_file_when_both_exist():
    both = resolve_act(
        "поменяй заголовок на Гомель",
        has_report=True,
        has_deck=True,
    )
    assert both.op == "ask"
    assert "отч" in both.say.casefold()
    assert "презентац" in both.say.casefold()
    deck = resolve_act(
        "поменяй заголовок презентации на Гомель",
        has_report=True,
        has_deck=True,
    )
    assert deck.op == "retitle"
    assert deck.title_on == "deck"
    assert deck.title == "Гомель"
    report = resolve_act(
        "поменяй заголовок отчёта на Гомель",
        has_report=True,
        has_deck=True,
    )
    assert report.title_on == "report"
    assert report.title == "Гомель"
    only_deck = resolve_act("поменяй заголовок на Гомель", has_deck=True)
    assert only_deck.title_on == "deck"
    missing_deck = resolve_act(
        "поменяй заголовок презентации на Гомель",
        has_report=True,
    )
    assert missing_deck.kind == "talk"
    assert "презентац" in missing_deck.say.casefold()


def test_slide_move_names_both_places():
    act = resolve_act("переставь слайд 3 на место 1", has_deck=True)
    assert act.op == "reorder_slide"
    assert act.slide == 3
    assert act.slide_to == 1
    vague = resolve_act("переставь слайд", has_deck=True)
    assert vague.op == "ask"


def test_rewrite_without_a_section_name_asks():
    bare = resolve_act("перепиши раздел", has_report=True, last_section="Введение")
    assert bare.op == "ask"
    named = resolve_act("перепиши раздел Введение", has_report=True)
    assert named.op == "rewrite"
    assert named.section.casefold().startswith("введен")


def test_rename_section_is_not_a_document_title():
    act = resolve_act(
        "переименуй раздел Введение в Контекст",
        has_report=True,
        has_deck=True,
    )
    assert act.op == "rename_heading"
    assert act.section == "Введение"
    assert act.title == "Контекст"
    missing = resolve_act("переименуй раздел Введение в Контекст")
    assert missing.kind == "talk"


def test_slide_text_allows_the_number_before_the_word():
    text = resolve_act("напиши на 2 слайде KPI", has_deck=True)
    assert text.op == "slide_text"
    assert text.slide == 2
    assert "KPI" in text.title
    assert resolve_act("напиши на 2 слайде KPI").kind == "talk"


def test_a_named_color_recolors_the_deck_already_on_the_table():
    act = resolve_act("презу в сапфир пж", has_deck=True)
    assert act.op == "recolor_deck"
    assert act.pack == "board"
    fresh = resolve_act("сделай презу в сапфир", has_deck=True)
    assert fresh.kind == "build"
    assert fresh.build == "presentation"


def test_slide_text_and_a_new_slide_stay_on_the_deck():
    text = resolve_act("на слайде 2 напиши Риски выросли", has_deck=True)
    assert text.op == "slide_text"
    assert text.slide == 2
    assert text.title == "Риски выросли"
    added = resolve_act("добавь слайд про риски", has_deck=True)
    assert added.op == "add_slide"
    assert added.title == "риски"
    vague = resolve_act("добавь слайд", has_deck=True)
    assert vague.op == "ask"
    assert resolve_act("добавь слайд про риски").kind == "talk"


def test_one_named_chart_does_not_retype_the_rest():
    one = resolve_act("второй график сделай линейным", has_report=True)
    assert one.op == "retype_chart"
    assert one.chart == "line"
    assert one.chart_at == 2
    all_charts = resolve_act("сделай график линейным", has_report=True)
    assert all_charts.op == "retype_charts"
    assert all_charts.chart_at == 0


def test_chart_word_picks_a_real_type():
    line = resolve_act("сделай график линейным", has_report=True)
    assert line.op == "retype_charts"
    assert line.chart == "line"
    donut = resolve_act("смени график на пончик", has_report=True)
    assert donut.chart == "donut"
    ask = resolve_act("смени вид графика", has_report=True)
    assert ask.op == "ask"
    assert "пончик" in ask.say
    assert resolve_act("сделай график линейным").kind == "talk"
