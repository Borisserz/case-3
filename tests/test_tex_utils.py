from case3.tex_utils import extract_tex, list_includegraphics


def test_extract_fenced():
    raw = "Here:\n```latex\n\\documentclass{article}\\begin{document}Hi\\end{document}\n```\n"
    tex = extract_tex(raw)
    assert r"\documentclass" in tex
    assert tex.strip().endswith(r"\end{document}")


def test_extract_plain():
    raw = r"\documentclass{article}\begin{document}x\end{document}"
    assert "documentclass" in extract_tex(raw)


def test_includegraphics_paths():
    tex = r"\includegraphics[width=1]{images/a.png}"
    assert list_includegraphics(tex) == ["images/a.png"]
