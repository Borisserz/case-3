import json
from pathlib import Path

from case3.chat_act import chart_type_named, resolve_act
from case3.turn_plan import plan_turn


def test_two_edit_verbs_split_and_a_table_cell_stays_whole():
    from case3.chat_act import edit_clauses

    assert edit_clauses("убери слайд 2 и перекрась графики в ocean") == [
        "убери слайд 2",
        "перекрась графики в ocean",
    ]
    assert edit_clauses("в таблице добавь строку: Гомель; 12") == [
        "в таблице добавь строку: Гомель; 12",
    ]
    assert edit_clauses("перепиши введение и сделай короче") == [
        "перепиши введение и сделай короче",
    ]


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
    # An editing instruction after ':' or '—' must NOT be treated as literal replacement prose!
    assert (
        parse_rewrite(
            "Перепиши раздел Сводные итоги: сделай акцент на лидерах роста и отстающих инспекциях"
        )
        is None
    )
    assert (
        parse_rewrite(
            "Поправь раздел Введение — сократи и убери лишнюю воду"
        )
        is None
    )
    act_instr = resolve_act(
        "Перепиши раздел Сводные итоги: сделай акцент на лидерах роста и отстающих инспекциях",
        has_report=True,
    )
    assert act_instr.op == "rewrite"
    assert act_instr.section == "Сводные итоги"
    assert act_instr.brief != "supplied"

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

    swapped = resolve_act("поменять раздел введения", has_report=True)
    assert swapped.kind == "revise"
    assert swapped.op == "rewrite"
    assert swapped.section.casefold() == "введения"

    title = resolve_act("поменяй заголовок на Гомель", has_report=True)
    assert title.op == "retitle"


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


def test_table_row_can_be_added_or_removed():
    added = resolve_act(
        "в таблице добавь строку: Гомель; 12",
        has_report=True,
    )
    assert added.op == "add_row"
    assert added.items == ("Гомель", "12")
    removed = resolve_act("убери из таблицы строку Гомель", has_report=True)
    assert removed.op == "delete_row"
    assert removed.section == "Гомель"
    bare = resolve_act("в таблице добавь строку", has_report=True)
    assert bare.op == "ask"


def test_again_after_another_edit_does_not_rewrite_the_section():
    act = resolve_act(
        "ещё",
        has_report=True,
        has_deck=True,
        last_section="Введение",
        last_op="delete_slide",
    )
    assert act.op == "ask"


def test_table_cell_replace_names_both_sides():
    act = resolve_act("в таблице замени Гомель на Брест", has_report=True)
    assert act.op == "replace_cell"
    assert act.section == "Гомель"
    assert act.title == "Брест"
    assert act.slot == 0
    second = resolve_act("во второй таблице замени 10 на 12", has_report=True)
    assert second.op == "replace_cell"
    assert second.slot == 2
    assert second.section == "10"
    assert second.title == "12"
    missing = resolve_act("в таблице замени 10 на 12")
    assert missing.kind == "talk"
    vague = resolve_act("поправь таблицу", has_report=True)
    assert vague.op == "ask"
    assert "таблиц" in vague.say


def test_list_item_can_be_replaced_or_added():
    changed = resolve_act("в списке замени кассу на выручку", has_report=True)
    assert changed.op == "replace_item"
    assert changed.section == "кассу"
    assert changed.title == "выручку"
    added = resolve_act("добавь в список пункт риски поставки", has_report=True)
    assert added.op == "add_item"
    assert "риски поставки" in added.title
    assert resolve_act("добавь в список пункт риски").kind == "talk"


def test_diagram_edit_is_not_a_new_diagram():
    act = resolve_act("на схеме убери кассу", has_diagram=True)
    assert act.kind == "revise"
    assert act.op == "refine_diagram"
    assert "кассу" in act.title
    vague = resolve_act("поправь схему", has_diagram=True, has_report=True)
    assert vague.op == "ask"
    assert "схем" in vague.say
    built = resolve_act("сделай схему про кассу", has_diagram=True)
    assert built.kind == "build"
    assert built.build == "diagram"
    follow = resolve_act(
        "Доработай схему: сделай стрелки толще",
        has_diagram=True,
    )
    assert follow.kind == "revise"
    assert follow.op == "refine_diagram"
    assert "стрелки" in follow.title
    branch = resolve_act(
        "можешь добавить еще ветку в схему",
        has_diagram=True,
        has_report=True,
    )
    assert branch.op == "refine_diagram"
    assert "ветк" in branch.title
    user_node = resolve_act(
        "добавь раздел про пользователя",
        has_diagram=True,
        has_report=True,
    )
    assert user_node.op == "refine_diagram"
    assert "пользовател" in user_node.title
    section = resolve_act(
        "поменяй раздел введение, сделай его короче и убери воду",
        has_diagram=True,
        has_report=True,
    )
    assert section.op == "rewrite"
    assert section.section == "Введение"


def test_polite_edits_reach_every_structure():
    section = resolve_act("можешь заключение чуть строже", has_report=True)
    assert section.op == "rewrite"
    assert section.section == "Заключение"
    assert section.brief == "clearer"
    strict = resolve_act("исправь заключение чуть строже", has_report=True)
    assert strict.op == "rewrite"
    assert strict.section == "Заключение"
    again = resolve_act("чуть строже", has_report=True, last_section="Заключение")
    assert again.op == "rewrite"
    assert again.section == "Заключение"

    table = resolve_act("можешь в таблице поменять Гомель на Брест", has_report=True)
    assert table.op == "replace_cell"
    assert table.section == "Гомель"
    assert table.title == "Брест"
    polite = resolve_act("в таблице замени пожалуйста Гомель на Брест", has_report=True)
    assert polite.section == "Гомель"

    chart = resolve_act("можешь график сделать столбцами", has_chart=True)
    assert chart.op == "retype_charts"
    assert chart.chart == "bar"

    photo = resolve_act("можешь на фото убрать фон", has_report=True)
    assert photo.op == "edit_photo"
    assert "фон" in photo.title

    renamed = resolve_act(
        "можешь переименовать раздел Введение в Обзор", has_report=True
    )
    assert renamed.op == "rename_heading"
    assert renamed.section == "Введение"
    assert renamed.title == "Обзор"

    listed = resolve_act("можешь в списке заменить кассу на выручку", has_report=True)
    assert listed.op == "replace_item"
    assert listed.section == "кассу"

    simpler = resolve_act("упрости схему", has_diagram=True)
    assert simpler.op == "refine_diagram"
    softer = resolve_act("давай схему чуть проще", has_diagram=True)
    assert softer.op == "refine_diagram"
    removed = resolve_act("можешь убрать из схемы кассу", has_diagram=True)
    assert removed.op == "refine_diagram"
    assert "кассу" in removed.title

    assert resolve_act("почему график зелёный", has_chart=True).kind == "talk"
    assert resolve_act("сделай новую схему", has_diagram=True).kind == "build"
    assert resolve_act("что на схеме", has_diagram=True).kind == "talk"
    vague = resolve_act("поправь", has_report=True, has_diagram=True)
    assert vague.op == "ask"


def test_slide_points_are_not_the_title():
    act = resolve_act("на слайде 2 пункты: риски; сроки", has_deck=True)
    assert act.op == "slide_bullets"
    assert act.slide == 2
    assert act.items == ("риски", "сроки")
    title = resolve_act("на слайде 2 напиши Риски выросли", has_deck=True)
    assert title.op == "slide_text"
    assert title.title == "Риски выросли"
    assert resolve_act("на слайде 2 пункты: риски", has_deck=False).kind == "talk"


def test_keep_text_on_a_named_slide_does_not_build_a_new_deck():
    from case3.turn_plan import plan_turn

    phrase = "оставь просто январь 2025 на первом слайде"
    act = resolve_act(phrase, has_deck=True)
    assert act.op == "slide_text"
    assert act.slide == 1
    assert act.title == "январь 2025"
    assert act.brief == "only"
    other = resolve_act("на первом слайде оставь только январь 2025", has_deck=True)
    assert other.op == "slide_text"
    assert other.slide == 1
    assert other.title == "январь 2025"
    quarter = resolve_act(
        "оставь первый квартал на втором слайде",
        has_deck=True,
    )
    assert quarter.slide == 2
    assert quarter.title == "первый квартал"
    plan = plan_turn(phrase, mode_hint="presentation", has_deck=True)
    assert plan.kind == "revise"
    stray = plan_turn(
        "на слайде 2 поменяй картинку",
        mode_hint="presentation",
        has_deck=True,
    )
    assert stray.kind == "clarify"
    fresh = plan_turn(
        "Собери новую презентацию",
        mode_hint="presentation",
        has_deck=True,
    )
    assert fresh.kind == "presentation"


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


def test_a_named_slide_edit_is_not_a_section_rewrite():
    from case3.chat_act import slide_rewrite_bits

    vague = resolve_act("можешь изменить слайд первый", has_deck=True, has_report=True)
    assert vague.op == "rewrite_slide"
    assert vague.slide == 1
    assert vague.section == ""
    fixed = resolve_act("поправь слайд 1", has_deck=True, has_report=True)
    assert fixed.op == "rewrite_slide"
    assert fixed.slide == 1
    shorter = resolve_act("сделай первый слайд короче", has_deck=True, has_report=True)
    assert shorter.op == "rewrite_slide"
    assert shorter.slide == 1
    assert shorter.brief == "tighter"
    other = resolve_act("сделай название на первом слайде другое", has_deck=True)
    assert other.op == "rewrite_slide"
    assert other.slide == 1
    assert other.brief == "title"
    heading = resolve_act("измени заголовок первого слайда", has_deck=True)
    assert heading.op == "rewrite_slide"
    assert heading.slide == 1
    assert heading.brief == "title"
    unnamed = resolve_act("измени слайд", has_deck=True)
    assert unnamed.op == "ask"
    assert unnamed.slide == 0
    from case3.chat_act import usable_slide_title

    title, bullets = slide_rewrite_bits(
        "Старый заголовок. Новый заголовок про риски.",
        title_only=True,
        current_title="Старый заголовок",
    )
    assert title == "Новый заголовок про риски"
    assert bullets == ()
    echo = (
        "Вместо заголовка «Создание нейросети на базе ML.NET» "
        "на первом слайде укажите короткую фразу"
    )
    assert usable_slide_title(echo, "Создание нейросети на базе ML.NET") == ""
    assert usable_slide_title("Нейросеть на ML.NET", "Создание нейросети на базе ML.NET") == (
        "Нейросеть на ML.NET"
    )
    written = resolve_act("на первом слайде напиши теорию", has_deck=True, has_report=True)
    assert written.op == "slide_text"
    assert written.slide == 1
    assert written.title == "теорию"
    points = resolve_act("на первом слайде пункты: риски; сроки", has_deck=True)
    assert points.op == "slide_bullets"
    assert points.slide == 1
    section = resolve_act("поправь введение", has_report=True, has_deck=True)
    assert section.op == "rewrite"
    assert section.section == "Введение"


def test_one_named_chart_does_not_retype_the_rest():
    one = resolve_act("второй график сделай линейным", has_report=True)
    assert one.op == "retype_chart"
    assert one.chart == "line"
    assert one.chart_at == 2
    all_charts = resolve_act("сделай график линейным", has_report=True)
    assert all_charts.op == "retype_charts"
    assert all_charts.chart_at == 0


def test_green_edit_of_an_existing_chart_is_not_a_type_question():
    from case3.chat_act import resolve_act

    for line in (
        "Доработай график: сделай в зеленых цветах",
        "Сделай график в зеленом цвете",
        "зеленый цвет сделай",
        "столбцы зеленые",
    ):
        act = resolve_act(line, has_chart=True)
        assert act.kind == "revise", line
        assert act.op == "recolor_hue", line
        assert act.palette == "green", line
        assert "вид графика" not in act.say


def test_named_chart_type_still_retypes_when_no_color():
    act = resolve_act("сделай график линейным", has_chart=True)
    assert act.op == "retype_charts"
    assert act.chart == "line"


def test_change_to_pie_retypes_the_open_chart():
    for line in (
        "изменить на круговую",
        "измени график на круговую",
        "переделай в круговую",
        "переделай график на пончик",
    ):
        act = resolve_act(line, has_chart=True)
        assert act.kind == "revise", line
        assert act.op == "retype_charts", line
        assert act.chart == "donut", line
    with_report = resolve_act(
        "изменить на круговую", has_chart=True, has_report=True
    )
    assert with_report.op == "retype_charts"
    assert with_report.chart == "donut"
    assert resolve_act("переделай введение", has_report=True).op == "rewrite"
    assert resolve_act("измени формат вывода в чате").kind == "talk"


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


def test_chart_type_named_donut_without_grafik_word():
    assert chart_type_named("пончик") == "donut"
    assert chart_type_named("круговую") == "donut"
    assert chart_type_named("сделай круговую") == "donut"


def test_chart_type_named_ignores_area_without_grafik_word():
    assert chart_type_named("сделай площадь меньше") == ""
    assert chart_type_named("сделай график площадью") == "area"
    assert resolve_act("сделай площадь меньше", has_chart=True).kind == "talk"


def test_chart_style_edit_is_not_a_fake_section():
    labels = resolve_act("поправь подписи на графике", has_chart=True, has_report=True)
    assert labels.kind == "revise"
    assert labels.op == "restyle_chart"
    legend = resolve_act("убери легенду у графика", has_chart=True, has_report=True)
    assert legend.op == "restyle_chart"
    bare = resolve_act("отредактируй график", has_chart=True)
    assert bare.op == "ask"
    assert "подписи" in bare.say
    still = resolve_act("а сделай ее кругового формата", has_chart=True)
    assert still.op == "retype_charts"
    assert still.chart == "donut"


def test_section_edit_stays_on_the_report_not_in_chat():
    """«редактируй раздел введение…» used to be a chat essay beside the old PDF."""
    phrases = (
        "редактируй раздел введение напиши больше текста с числами",
        "отредактируй введение",
        "правь раздел введение",
        "в введении напиши больше текста",
        "допиши введение",
        "сделай введение длиннее",
        "напиши больше текста в разделе введение",
        "раздел введение сделай подробнее",
        "доработай введение",
    )
    for line in phrases:
        act = resolve_act(line, has_report=True)
        assert act.kind == "revise", line
        assert act.op == "rewrite", line
        assert act.section.casefold().startswith("введен"), (line, act.section)
        assert "напиш" not in act.section.casefold(), (line, act.section)
    longer = resolve_act(
        "редактируй раздел введение напиши больше текста с числами",
        has_report=True,
    )
    assert longer.brief == "longer"
    chart = resolve_act("редактируй график", has_chart=True, has_report=True)
    assert chart.op != "rewrite"
    assert resolve_act("почему введение слабое?", has_report=True).kind == "talk"
    assert resolve_act("напиши отчёт", has_report=True).op != "rewrite"


def test_report_wording_hits_the_named_section():
    para = resolve_act("поменяй абзац во введении", has_report=True)
    assert para.op == "rewrite"
    assert para.section.casefold().startswith("введен")
    body = resolve_act("измени текст раздела анализ", has_report=True)
    assert body.op == "rewrite"
    assert body.section.casefold().startswith("анализ")
    short = resolve_act("поменяй раздел введения на более короткий", has_report=True)
    assert short.op == "rewrite"
    assert short.section.casefold().startswith("введен")
    assert "коротк" not in short.section.casefold()
    assert short.brief == "tighter"


def test_screenshot_chart_phrases_do_not_stay_talk():
    """«давай пончиком» and «сделай другого типа его» used to be talk.

    The model then claimed a new chart that was never drawn.
    """
    donut = resolve_act("давай пончиком", has_chart=True)
    assert donut.kind == "revise"
    assert donut.op == "retype_charts"
    assert donut.chart == "donut"
    bare = resolve_act("пончиком", has_chart=True)
    assert bare.op == "retype_charts"
    assert bare.chart == "donut"
    other = resolve_act("сделай другого типа его", has_chart=True)
    assert other.kind == "revise"
    assert other.op == "ask"
    assert "пончик" in other.say
    assert resolve_act("давай пончиком").kind == "talk"


def test_krugovaya_retypes_chart_without_grafik_word():
    act = resolve_act("сделай круговую", has_chart=True)
    assert act.kind == "revise"
    assert act.op == "retype_charts"
    assert act.chart == "donut"
    assert act.op != "ask"


def test_typo_rezentaciya_retitle_and_recolor():
    title = resolve_act(
        "поменяй заголовок резентации на Итоги",
        has_deck=True,
    )
    assert title.op == "retitle"
    assert title.title == "Итоги"
    assert title.title_on == "deck"
    recolor = resolve_act(
        "перекрась резентацию в Northstar",
        has_deck=True,
    )
    assert recolor.op == "recolor_deck"
    assert recolor.pack == "board"


def test_question_mark_on_a_clear_edit_still_edits():
    act = resolve_act("убери слайд 2?", has_deck=True)
    assert act.kind == "revise"
    assert act.op == "delete_slide"
    assert act.slide == 2


def test_why_with_an_edit_verb_stays_talk():
    act = resolve_act("почему бы не убрать слайд 2?", has_deck=True, has_report=True)
    assert act.kind == "talk"


def test_bare_question_stays_talk():
    act = resolve_act("что это?", has_deck=True, has_report=True)
    assert act.kind == "talk"


def test_change_photo_keeps_the_original_and_the_instruction():
    act = resolve_act("измени фото сделай небо темнее")
    assert act.kind == "revise"
    assert act.op == "edit_photo"
    assert act.title == "небо темнее"
    bare = resolve_act("измени фото")
    assert bare.op == "ask"
    fresh = resolve_act("сделай фото цеха")
    assert fresh.op != "edit_photo"


def test_photo_phrase_is_a_pixel_edit():
    act = resolve_act("на фото сделай небо темнее", has_report=True)
    assert act.kind == "revise"
    assert act.op == "edit_photo"
    assert act.title == "небо темнее"
    assert act.section == ""


def test_named_photo_keeps_its_id():
    act = resolve_act("поправь фото usr_01: убери людей", has_report=True)
    assert act.op == "edit_photo"
    assert act.section == "usr_01"
    assert "люди" in act.title or "убери людей" in act.title


def test_caption_phrase_is_not_a_pixel_edit():
    act = resolve_act("подпись фото: цех ночью", has_report=True)
    assert act.op == "caption"


def test_a_new_photo_request_is_not_a_pixel_edit():
    act = resolve_act("сделай фото цеха", has_report=True)
    assert act.op != "edit_photo"


def test_a_visual_change_edits_the_photo_even_without_the_word_photo():
    from case3.turn_plan import plan_turn

    samples = (
        ("сделай там машину красной а не синей", "красн"),
        ("сделай машину красной а не синей", "красн"),
        ("сделай машину красной", "красн"),
        ("отредактируй, сделай машину красной", "красн"),
        ("измени, сделай машину красной", "красн"),
        ("перекрась машину в красный", "машин"),
        ("поменяй цвет машины на красный", "машин"),
        ("убери людей с фото", "люд"),
    )
    for line, bit in samples:
        act = resolve_act(line, has_report=True, has_chart=True)
        assert act.op == "edit_photo", line
        assert bit in act.title.casefold(), (line, act.title)
        plan = plan_turn(line, has_report=True, has_chart=True)
        assert plan.kind == "revise", line
        assert plan.reason == "photo_edit", line


def test_creating_a_picture_does_not_edit_or_recolor_a_chart():
    from case3.turn_plan import plan_turn
    from case3.turn_route import asks_for_generated_photo

    for line in (
        "создай фото красной машины",
        "сделай фото цеха",
        "создай картинку цеха",
        "нарисуй красную машину",
        "сделай красную машину",
    ):
        act = resolve_act(line, has_report=True, has_chart=True)
        assert act.op != "edit_photo", line
        assert act.op != "recolor_hue", line
        assert asks_for_generated_photo(line), line
        plan = plan_turn(line, has_report=True, has_chart=True)
        assert plan.kind != "revise", line


def test_editing_a_named_section_is_not_a_photo_edit():
    act = resolve_act("отредактируй введение", has_report=True, has_chart=True)
    assert act.op == "rewrite"
    assert act.section == "Введение"


def test_unnamed_color_asks_photo_or_chart_when_both_are_open():
    for line in (
        "сделай красным",
        "поменяй цвет",
        "измени цвет",
        "перекрась",
        "перекрась в красный",
        "зеленый цвет сделай",
    ):
        act = resolve_act(line, has_report=True, has_chart=True, has_photo=True)
        assert act.op == "ask", line
        folded = act.say.casefold()
        assert "фото" in folded and "график" in folded, line


def test_named_photo_and_chart_stay_apart_when_both_are_open():
    photo = resolve_act(
        "сделай машину красной", has_report=True, has_chart=True, has_photo=True
    )
    assert photo.op == "edit_photo"
    on_photo = resolve_act(
        "на фото сделай красным", has_report=True, has_chart=True, has_photo=True
    )
    assert on_photo.op == "edit_photo"
    car = resolve_act(
        "поменяй цвет машины на красный", has_report=True, has_chart=True, has_photo=True
    )
    assert car.op == "edit_photo"
    chart = resolve_act("столбцы зеленые", has_chart=True, has_photo=True)
    assert chart.op == "recolor_hue"
    graphs = resolve_act(
        "перекрась графики в красный", has_report=True, has_chart=True, has_photo=True
    )
    assert graphs.op == "recolor_hue"
    deck = resolve_act(
        "Перекрась презу в синий", has_deck=True, has_chart=True, has_photo=True
    )
    assert deck.op == "recolor_deck"


def test_prior_run_photo_is_visible_to_the_router(tmp_path: Path) -> None:
    from case3.api import _prior_artifact_flags

    run = tmp_path / "runs" / "out" / "source_photo"
    figs = run / "figures"
    figs.mkdir(parents=True)
    (figs / "fig_01.png").write_bytes(b"png")
    (run / "meta.json").write_text("{}", encoding="utf-8")
    flags = _prior_artifact_flags(tmp_path, "source_photo")
    assert flags["has_photo"] is True


def test_color_followup_of_the_open_photo_edits_every_time():
    """A leading «а» or «измени» without the word «фото» still edits the open photo."""
    from case3.turn_plan import plan_turn
    from case3.turn_route import asks_for_generated_photo

    lines = {
        "а сделай ее красного цвета": "красн",
        "измени сделай синей": "син",
        "а сделай ее синей": "син",
    }
    for line, color in lines.items():
        act = resolve_act(line, has_photo=True)
        assert act.op == "edit_photo", line
        assert color in act.title.casefold(), (line, act.title)
        assert not act.title.casefold().startswith("а "), act.title
        plan = plan_turn(line, has_photo=True)
        assert plan.kind == "revise", line
        assert asks_for_generated_photo(line) is False
    fresh = plan_turn("сделай картинку машины бмв белую", has_photo=True)
    assert fresh.kind != "revise"
    assert asks_for_generated_photo("сделай картинку машины бмв белую")
    both = resolve_act("а сделай ее красного цвета", has_photo=True, has_chart=True)
    assert both.op == "ask"
    chart = resolve_act("а сделай ее красного цвета", has_chart=True)
    assert chart.op == "recolor_hue"


def test_color_of_the_open_photo_does_not_need_the_word_change():
    """«сделай красным» edits the photo. «и покажи фото» is not a new picture."""
    from case3.turn_plan import plan_turn
    from case3.turn_route import asks_for_generated_photo

    lines = (
        "сделай ее красного цвета",
        "сделай красным цветом",
        "сделай красным и покажи фото",
    )
    for line in lines:
        act = resolve_act(line, has_photo=True)
        assert act.op == "edit_photo", line
        assert "красн" in act.title.casefold(), (line, act.title)
        plan = plan_turn(line, has_photo=True)
        assert plan.kind == "revise", line
        assert plan.edit_act is not None and plan.edit_act.op == "edit_photo"
    fresh = plan_turn("сделай красную машину", has_photo=True)
    assert fresh.kind != "revise"
    assert asks_for_generated_photo("сделай красную машину")
    assert asks_for_generated_photo("сделай красным и покажи фото")
    both = resolve_act("сделай ее красного цвета", has_photo=True, has_chart=True)
    assert both.op == "ask"
    chart = resolve_act("сделай ее красного цвета", has_chart=True)
    assert chart.op == "recolor_hue"


def test_unnamed_color_follows_the_only_open_picture():
    photo = resolve_act("сделай красным", has_report=True, has_photo=True)
    assert photo.op == "edit_photo"
    assert "красн" in photo.title.casefold()
    chart = resolve_act("сделай красным", has_report=True, has_chart=True)
    assert chart.op == "recolor_hue"
    painted = resolve_act("перекрась в красный", has_report=True, has_chart=True)
    assert painted.op == "recolor_hue"
    bare = resolve_act("поменяй цвет", has_report=True, has_chart=True)
    assert bare.op != "edit_photo"
    assert "график" in bare.say.casefold()


def test_pink_recolors_and_keeps_a_named_chart_type():
    bare = resolve_act("розовый", has_chart=True)
    assert bare.op == "recolor_hue"
    assert bare.palette == "pink"
    pointed = resolve_act("измени ему цвет на розовый", has_chart=True)
    assert pointed.op == "recolor_hue"
    assert pointed.palette == "pink"
    both = resolve_act("сделай круговой график розовым", has_chart=True)
    assert both.op == "recolor_hue"
    assert both.palette == "pink"
    assert both.chart == "donut"
    missing = resolve_act("сделай круговой график фиолетовым", has_chart=True)
    assert missing.op == "ask"
    assert "розов" in missing.say.casefold()


def test_photo_without_a_change_asks():
    act = resolve_act("поправь фото", has_report=True)
    assert act.op == "ask"
    assert "фото" in act.say.lower()


def test_delete_section_names_the_heading():
    act = resolve_act("убери раздел Введение", has_report=True)
    assert act.kind == "revise"
    assert act.op == "delete_section"
    assert act.section == "Введение"


def test_delete_section_without_a_name_asks():
    act = resolve_act("удали раздел", has_report=True)
    assert act.op == "ask"
    assert "раздел" in act.say.lower()


def test_list_delete_is_not_a_section_delete():
    act = resolve_act("убери кассу из списка", has_report=True)
    assert act.op == "delete_item"


def test_slide_delete_is_not_a_section_delete():
    act = resolve_act("убери слайд 2", has_deck=True, has_report=True)
    assert act.op == "delete_slide"


def test_chart_numbers_stay_talk():
    act = resolve_act("поменяй числа на графике", has_report=True, has_deck=True)
    assert act.kind == "talk"


def test_diagram_legend_stays_talk():
    act = resolve_act("поправь легенду схемы", has_diagram=True, has_report=True)
    assert act.kind == "talk"


def test_chart_type_is_still_a_retype():
    act = resolve_act("сделай график линейным", has_report=True)
    assert act.op == "retype_charts"
    assert act.chart == "line"


def test_dialogue_math_and_concise_chat_without_artifact_stay_talk_for_llm():
    from case3.chat_act import asks_without_order

    scenario = "Допустим, для Гомеля выделили резерв 450. На сколько изменится отклонение?"
    assert asks_without_order(scenario) is True
    act_scenario = resolve_act(scenario, has_report=False, has_deck=False)
    assert act_scenario.kind == "talk"
    assert not act_scenario.say

    # Without an open report, "напиши короче" is a chat style request — do not hijack with canned refusal
    act_short = resolve_act("напиши короче", has_report=False, has_deck=False)
    assert act_short.kind == "talk"
    assert not act_short.say

    # Generic edit verb without an artifact must not return op="ask"
    act_change = resolve_act("измени формат вывода в чате", has_report=False, has_deck=False)
    assert act_change.kind == "talk"
    assert not act_change.say


def test_new_build_artifact_handles_long_middle_phrase_and_rebuilds():
    long_order = "сделай по нашему подробному анализу выше по областям отчёт"
    act = resolve_act(long_order, has_report=True, has_deck=True)
    assert act.kind == "build"
    assert act.build == "report"

    rebuild = resolve_act("перестрой презентацию", has_deck=True)
    assert rebuild.kind == "build"
    assert rebuild.build == "presentation"


def test_inline_chat_chart_retype_and_recolor_in_chat_revise(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from case3.chat_revise import try_chat_revise

    act = resolve_act("Сделай этот график линейным", has_chart=True)
    assert act.kind == "revise"
    assert act.op == "retype_charts"
    assert act.chart == "line"

    run_id = "source_20261123T120000Z"
    out = tmp_path / "runs" / "out" / run_id
    figs = out / "figures"
    figs.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "status": "ok", "output_mode": "chat", "charts_planned": ["cht_01"]}),
        encoding="utf-8",
    )
    (out / "figures.json").write_text(
        json.dumps(
            {
                "figures": [],
                "diagrams": [],
                "charts": [
                    {
                        "id": "cht_01",
                        "type": "bar",
                        "caption": "Регионы",
                        "html": "<canvas id='c' width='1100' height='560'></canvas><script>new Chart(document.getElementById('c'),{type:'bar',data:{labels:['А','Б'],datasets:[{label:'Факт',data:[10,20]}]}});</script>",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def _fake_render(_chart, dest: Path, **_kw) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr("case3.chart_edit.render_chart_png", _fake_render)
    res = try_chat_revise("Сделай этот график линейным", run_id, root=tmp_path)
    assert res is not None
    assert res["mode"] == "chat_revise"
    assert res["op"] == "retype_charts"
    assert res.get("previews") and res["previews"][0]["id"] == "cht_01"
    saved = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert saved["charts"][0]["type"] == "line"

    pie = try_chat_revise("изменить на круговую", run_id, root=tmp_path)
    assert pie is not None
    assert pie["op"] == "retype_charts"
    assert pie.get("previews") and pie["previews"][0]["kind"] == "chart"
    saved = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    assert saved["charts"][0]["type"] == "donut"
    assert "doughnut" in saved["charts"][0]["html"]


def test_retype_does_not_claim_a_new_picture_when_the_file_stays(tmp_path, monkeypatch):
    import json
    from case3.chat_revise import try_chat_revise

    run_id = "source_20261123T120100Z"
    out = tmp_path / "runs" / "out" / run_id
    (out / "figures").mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "output_mode": "chat", "charts_planned": ["cht_01"]}),
        encoding="utf-8",
    )
    (out / "figures.json").write_text(
        json.dumps(
            {
                "charts": [
                    {
                        "id": "cht_01",
                        "type": "bar",
                        "html": "{type:'bar',data:{labels:['А'],datasets:[{data:[1]}]}}",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (out / "figures" / "cht_01.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    def keep(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("case3.chart_edit.edit_chart_in_run", keep)
    result = try_chat_revise("а сделай ее кругового формата", run_id, root=tmp_path)
    assert result is not None
    assert "пончик" not in result["chat"].casefold()
    assert "прежней" in result["chat"]
    assert not result.get("previews")


def test_chart_phrase_restyles_and_rebuilds_the_report(tmp_path, monkeypatch):
    import json
    from case3.chat_revise import try_chat_revise

    run_id = "source_20261123T120200Z"
    out = tmp_path / "runs" / "out" / run_id
    (out / "figures").mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps({"run_id": run_id, "output_mode": "report", "charts_planned": ["cht_01"]}),
        encoding="utf-8",
    )
    (out / "figures.json").write_text(
        json.dumps({"charts": [{"id": "cht_01", "type": "bar", "html": "{type:'bar'}"}]}),
        encoding="utf-8",
    )
    (out / "figures" / "cht_01.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (out / "report.tex").write_text("\\documentclass{article}", encoding="utf-8")
    seen: dict = {}

    def fake(_out, chart_id, **kwargs):
        seen["id"] = chart_id
        seen["style"] = kwargs.get("style")
        seen["formats"] = kwargs.get("formats")
        return {}

    monkeypatch.setattr("case3.chart_edit.edit_chart_in_run", fake)
    result = try_chat_revise("убери легенду у графика", run_id, root=tmp_path)
    assert result is not None
    assert result["op"] == "restyle_chart"
    assert seen["id"] == "cht_01"
    assert "легенду" in seen["style"]
    assert seen["formats"] == {"pdf", "docx"}
    assert "PDF" in result["chat"]
    assert result.get("previews")


def test_section_target_strips_trailing_adverbs_and_history_title_skips_generic() -> None:
    from case3.api_history import _title_from_meta
    from case3.chat_act import section_target

    assert section_target("переделай введение покороче") == "Введение"
    assert section_target("сократи раздел Итоги кратко") == "Итоги"
    assert (
        _title_from_meta(
            {
                "intent": "Сделай отчёт",
                "chat_summary": "Поступления за январь составили 412 850,4 тыс. руб.",
            },
            "source_20261123T120000Z",
        )
        == "Поступления за январь составили 412 850,4 тыс. руб."
    )


def test_undo_clears_memory_section_for_chat_and_button_undo(tmp_path: Path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from case3.api import _memory_section, app
    from case3.chat_memory import newest_edit
    from case3.chat_revise import try_chat_revise

    run_id = "source_20261123T120500Z"
    out = tmp_path / "runs" / "out" / run_id
    out.mkdir(parents=True)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "ok",
                "output_mode": "report",
                "last_edit": {"op": "rewrite", "section": "Введение", "surface": "report"},
            }
        ),
        encoding="utf-8",
    )
    (out / "report.tex").write_text("\\documentclass{article}\\begin{document}Hi\\end{document}", encoding="utf-8")

    monkeypatch.setattr("case3.run_store.ROOT", tmp_path)
    monkeypatch.setattr("case3.run_undo.apply_undo", lambda *_a, **_kw: {"kind": "prose", "target": "Введение"})

    res = try_chat_revise("отмени", run_id, root=tmp_path)
    assert res is not None
    assert res.get("memory_section") == ""
    # Follow-up edits ("короче") still remember the section, while UI plaque clears.
    assert newest_edit(tmp_path, run_id).get("section") == "Введение"
    assert _memory_section(run_id) == ""

    # Also test UI button undo endpoint resets memory_section
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    meta["last_edit"] = {"op": "rewrite", "section": "Итоги", "surface": "report"}
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    client = TestClient(app)
    resp = client.post(f"/api/runs/{run_id}/undo?rebuild=0")
    assert resp.status_code == 200
    assert resp.json()["memory_section"] == ""
    status_resp = client.get(f"/api/runs/{run_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["memory_section"] == ""


def test_retitle_slide_n_and_table_replace_verbs_and_expand_section() -> None:
    act_s3 = resolve_act("поменяй заголовок слайда 3 на Анализ областей", has_deck=True)
    assert act_s3.op == "retitle"
    assert act_s3.title_on == "deck"
    assert act_s3.slide == 3
    assert act_s3.title == "Анализ областей"

    act_s2_ord = resolve_act("поменяй заголовок второго слайда на Выводы", has_deck=True)
    assert act_s2_ord.op == "retitle"
    assert act_s2_ord.title_on == "deck"
    assert act_s2_ord.slide == 2
    assert act_s2_ord.title == "Выводы"

    act_tbl = resolve_act("в таблице поменяй Пинский р-н на г. Пинск", has_report=True)
    assert act_tbl.op == "replace_cell"
    assert act_tbl.section == "Пинский р-н"
    assert act_tbl.title == "г. Пинск"

    act_tbl_fix = resolve_act("в таблице исправь 10 на 12", has_report=True)
    assert act_tbl_fix.op == "replace_cell"
    assert act_tbl_fix.section == "10"
    assert act_tbl_fix.title == "12"

    act_expand = resolve_act("распиши раздел Выводы подробнее", has_report=True)
    assert act_expand.op == "rewrite"
    assert act_expand.section == "Выводы"

    from case3.chat_revise import _swap_text, _word_hit

    assert _word_hit("Пинский р-н", "Пинский р-н")
    assert _swap_text("Пинский р-н", "Пинский р-н", "г. Пинск") == "г. Пинск"


def test_change_section_rewrites_the_open_report() -> None:
    act = resolve_act("измени раздел введение", has_report=True)
    assert act.kind == "revise"
    assert act.op == "rewrite"
    assert act.section == "Введение"

    named = resolve_act(
        "измени введение: убери воду и оставь только факт про кассу",
        has_report=True,
    )
    assert named.op == "rewrite"
    assert named.section == "Введение"

    with_water = resolve_act(
        "измени раздел введение, сделай его короче и убери воду",
        has_report=True,
    )
    assert with_water.op == "rewrite"
    assert with_water.section == "Введение"
    assert with_water.brief == "tighter"

    plan = plan_turn("поменяй раздел выводы, сделай короче", has_report=True)
    assert plan.kind == "revise"
    assert plan.edit_act is not None
    assert plan.edit_act.op == "rewrite"
    assert plan.edit_act.section == "Выводы"
    assert plan.edit_act.brief == "tighter"


def test_delete_chart_does_not_restyle_it() -> None:
    act = resolve_act("удали график", has_report=True, has_chart=True)
    assert act.op == "delete_chart"
    assert act.chart_at == 0

    second = resolve_act("убери второй график", has_report=True, has_chart=True)
    assert second.op == "delete_chart"
    assert second.chart_at == 2

    named = resolve_act("удали график поступления", has_report=True, has_chart=True)
    assert named.op == "delete_chart"
    assert "поступлен" in named.title.casefold()

    style = resolve_act("на графике убери легенду", has_report=True, has_chart=True)
    assert style.op == "restyle_chart"


def test_delete_paragraph_or_block() -> None:
    paragraph = resolve_act("удали второй абзац введения", has_report=True)
    assert paragraph.op == "delete_paragraph"
    assert paragraph.slot == 2
    assert paragraph.section == "Введения"

    block = resolve_act("удали блок введение", has_report=True)
    assert block.op == "delete_section"
    assert block.section == "Введение"

    bare = resolve_act("удали абзац", has_report=True)
    assert bare.op == "ask"
    assert "абзац" in bare.say.lower()


def test_section_change_and_chart_delete_run_together() -> None:
    from case3.chat_act import edit_clauses

    clauses = edit_clauses("измени введение и удали график")
    assert len(clauses) == 2
    first = resolve_act(clauses[0], has_report=True, has_chart=True)
    second = resolve_act(clauses[1], has_report=True, has_chart=True)
    assert first.op == "rewrite"
    assert second.op == "delete_chart"


def test_rewrite_slide_changes_the_title_and_keeps_bullets(monkeypatch, tmp_path):
    from case3.chat_revise import _rewrite_slide

    deck = {
        "slides": [
            {
                "id": "s01",
                "layout": "bullets",
                "title": "Старое название",
                "bullets": ["первый пункт", "второй пункт"],
            }
        ]
    }
    saved: dict = {}

    def load(_run_id, _out_dir):
        return deck, tmp_path / "deck.json"

    def enqueue(_run_id, _out_dir, _ir_path, patched, **_kw):
        saved["deck"] = patched

    def draft(**_kwargs):
        return "Новый заголовок про риски"

    monkeypatch.setattr("case3.api_slides._load_deck_for_patch", load)
    monkeypatch.setattr("case3.api_slides._enqueue_deck_rebuild", enqueue)
    monkeypatch.setattr("case3.chat_turn.draft_slide_title", draft)

    say = _rewrite_slide("run_slide", tmp_path, 1, "title", "сделай название другое")
    assert "Новый заголовок про риски" in say
    slide = saved["deck"]["slides"][0]
    assert slide["title"] == "Новый заголовок про риски"
    assert slide["bullets"] == ["первый пункт", "второй пункт"]


