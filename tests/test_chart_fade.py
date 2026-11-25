from case3.chart_harden import _solidify_pale_bar_fill
from case3.chart_style import asks_for_softer_fill, fade_fill_on_html
from case3.chat_act import resolve_act


def test_softer_fill_is_not_a_chart_type_question():
    line = "а прозрачнее можешь цвета сделать на графике"
    act = resolve_act(line, has_chart=True)
    assert act.op == "fade_chart"
    assert "вид графика" not in act.say
    assert asks_for_softer_fill(line)


def test_type_word_still_retypes_even_with_transparency():
    act = resolve_act("сделай график площадью и прозрачнее", has_chart=True)
    assert act.op != "fade_chart"
    assert act.chart == "area"


def test_fade_lowers_fill_and_keeps_the_line():
    html = (
        "<canvas id='c'></canvas><script>new Chart(c,{type:'line',data:{datasets:[{"
        "borderColor:'#1B4D3E',backgroundColor:'#1B4D3E',data:[1,2]}]}});</script>"
    )
    faded = fade_fill_on_html(html)
    assert "backgroundColor:'rgba(27,77,62,0.28)'" in faded
    assert "borderColor:'#1B4D3E'" in faded
    assert "case3-soft-fill" in faded
    again = fade_fill_on_html(faded)
    assert "rgba(27,77,62,0.15)" in again


def test_bar_harden_does_not_paint_a_requested_wash_solid():
    html = "/* case3-soft-fill */ backgroundColor:'rgba(27,77,62,0.28)'"
    assert _solidify_pale_bar_fill(html) == html
