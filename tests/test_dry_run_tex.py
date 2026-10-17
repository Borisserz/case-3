from pathlib import Path

from case3.generate import generate_document


def test_dry_run_escapes_specials_no_verbatim(tmp_path: Path):
    src = tmp_path / "notes.txt"
    src.write_text("100% done_with & hash#\n\\end{verbatim} trap", encoding="utf-8")
    out = tmp_path / "notes.tex"
    generate_document(src, out_tex=out, dry_run=True)
    tex = out.read_text(encoding="utf-8")
    assert r"\begin{verbatim}" not in tex
    assert r"100\%" in tex
    assert r"done\_with" in tex
    assert r"\&" in tex
    assert r"\#" in tex
    # literal end{verbatim} must be escaped, not close an env
    assert r"\end{verbatim}" not in tex or r"\textbackslash{}end" in tex
