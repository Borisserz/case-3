from case3.tex_utils import extract_tex


def test_extract_fenced():
    raw = "Here:\n```latex\n\\documentclass{article}\\begin{document}Hi\\end{document}\n```\n"
    assert r"\documentclass" in extract_tex(raw)
