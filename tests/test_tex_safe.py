from case3.tex_safe import escape_tex_text, sanitize_width


def test_width_ok():
    assert sanitize_width(r"0.85\textwidth") == r"0.85\textwidth"
    assert sanitize_width(r"0.9\linewidth") == r"0.9\linewidth"


def test_width_rejects_injection():
    bad = r"0.85\textwidth]{x}\write18{id}"
    assert sanitize_width(bad) == r"0.85\textwidth"


def test_width_json_double_escape():
    assert sanitize_width("0.8\\\\textwidth") == r"0.8\textwidth"


def test_escape_caption():
    s = escape_tex_text(r"a_b % & # { }")
    assert r"\_" in s and r"\%" in s and r"\&" in s
