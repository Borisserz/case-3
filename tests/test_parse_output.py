from case3.parse_output import parse_model_output


RAW = """
```latex
\\documentclass{article}
\\begin{document}
Hello
%CASE3_FIG:fig_01%
\\end{document}
```

```json
{"figures":[{"id":"fig_01","caption":"C","prompt":"a blue diagram of network","width":"0.8\\\\textwidth"}],"charts":[]}
```
"""


def test_parse_two_fences():
    tex, figs, charts = parse_model_output(RAW, max_images=2, max_charts=0)
    assert r"\documentclass" in tex
    assert figs[0]["id"] == "fig_01"
    assert "diagram" in figs[0]["prompt"]
    assert charts == []


def test_cap_images():
    _, figs, charts = parse_model_output(RAW, max_images=0, max_charts=0)
    assert figs == []
    assert charts == []
