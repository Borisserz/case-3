"""Point 8: Kandinsky image-prompt filter."""

import pytest

from case3.image_prompt import ImagePromptError, sanitize_image_prompt
from case3.parse_output import ParseError, parse_model_output


def test_ok_english_prompt():
    assert "blue" in sanitize_image_prompt("a blue network diagram, clean photo style")


def test_rejects_cyrillic():
    with pytest.raises(ImagePromptError, match="Cyrillic|non-Latin|English"):
        sanitize_image_prompt("схема сети blue diagram")


def test_rejects_empty():
    with pytest.raises(ImagePromptError):
        sanitize_image_prompt("   ")


def test_rejects_too_short():
    with pytest.raises(ImagePromptError, match="short"):
        sanitize_image_prompt("ab")


def test_truncates_too_long():
    long = "a clear photo of " + ("word " * 200)
    out = sanitize_image_prompt(long)
    assert len(out) <= 800


def test_strips_control_chars():
    out = sanitize_image_prompt("a blue diagram\x00\x07 with sky")
    assert "\x00" not in out
    assert "blue" in out


def test_parse_drops_bad_prompt_and_raises_if_slot_left():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
%CASE3_FIG:fig_01%
\\end{document}
```

```json
{"figures":[{"id":"fig_01","caption":"Схема","prompt":"русская схема сети","width":"0.8\\\\textwidth"}]}
```
"""
    with pytest.raises(ParseError, match="fig_01|prompt"):
        parse_model_output(raw, max_images=2, max_charts=0)
