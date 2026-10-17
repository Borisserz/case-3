"""Strict dual-fence parse + slot↔json consistency."""

import pytest

from case3.parse_output import ParseError, parse_model_output


GOOD = """
```latex
\\documentclass{article}
\\begin{document}
Hello
%CASE3_FIG:fig_01%
\\end{document}
```

```json
{"figures":[{"id":"fig_01","caption":"C","prompt":"a blue diagram of a network","width":"0.8\\\\textwidth"}],"charts":[]}
```
"""


def test_ok_matching_slot_and_json():
    tex, figs, charts = parse_model_output(GOOD, max_images=2, max_charts=0)
    assert r"\documentclass" in tex
    assert [f["id"] for f in figs] == ["fig_01"]
    assert charts == []


def test_missing_json_fence_with_slot_raises():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
%CASE3_FIG:fig_01%
\\end{document}
```
"""
    with pytest.raises(ParseError, match="json"):
        parse_model_output(raw, max_images=2, max_charts=0)


def test_invalid_json_with_slot_raises():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
%CASE3_FIG:fig_01%
\\end{document}
```

```json
{not json
```
"""
    with pytest.raises(ParseError, match="JSON"):
        parse_model_output(raw, max_images=2, max_charts=0)


def test_slot_without_json_entry_raises():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
%CASE3_FIG:fig_01%
%CASE3_FIG:fig_02%
\\end{document}
```

```json
{"figures":[{"id":"fig_01","caption":"C","prompt":"blue sky landscape photo","width":"0.8\\\\textwidth"}],"charts":[]}
```
"""
    with pytest.raises(ParseError, match="fig_02"):
        parse_model_output(raw, max_images=2, max_charts=0)


def test_json_without_slot_dropped():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
%CASE3_FIG:fig_01%
\\end{document}
```

```json
{"figures":[
  {"id":"fig_01","caption":"C","prompt":"blue sky landscape photo","width":"0.8\\\\textwidth"},
  {"id":"fig_99","caption":"X","prompt":"orphan figure prompt here","width":"0.8\\\\textwidth"}
],"charts":[]}
```
"""
    _, figs, _ = parse_model_output(raw, max_images=2, max_charts=0)
    assert [f["id"] for f in figs] == ["fig_01"]


def test_no_slots_empty_figures_ok():
    raw = """
```latex
\\documentclass{article}
\\begin{document}
Only text
\\end{document}
```

```json
{"figures":[],"charts":[]}
```
"""
    tex, figs, charts = parse_model_output(raw, max_images=2, max_charts=2)
    assert "Only text" in tex
    assert figs == []
    assert charts == []


def test_max_images_zero_strips_figures_even_with_slots():
    tex, figs, _ = parse_model_output(GOOD, max_images=0, max_charts=0)
    assert figs == []
    assert "%CASE3_FIG:" in tex
