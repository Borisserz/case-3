"""Sanitize untrusted LLM fields before they touch TeX."""

from __future__ import annotations

import re

# Only fractional textwidth / linewidth — no free-form TeX.
_WIDTH_OK = re.compile(r"^(?:0?\.\d+|1(?:\.0+)?|0)\\(?:text|line)width$")


def sanitize_width(raw: str | None, *, default: str = r"0.85\textwidth") -> str:
    value = (raw or default).strip().replace(" ", "")
    # JSON often double-escapes: 0.85\\textwidth
    while "\\\\" in value:
        value = value.replace("\\\\", "\\")
    if _WIDTH_OK.match(value):
        return value
    return default


def escape_tex_text(text: str) -> str:
    """Escape LaTeX specials in captions / short prose from the model."""
    out: list[str] = []
    for ch in text or "":
        if ch == "\\":
            out.append(r"\textbackslash{}")
        elif ch == "{":
            out.append(r"\{")
        elif ch == "}":
            out.append(r"\}")
        elif ch == "$":
            out.append(r"\$")
        elif ch == "&":
            out.append(r"\&")
        elif ch == "%":
            out.append(r"\%")
        elif ch == "#":
            out.append(r"\#")
        elif ch == "_":
            out.append(r"\_")
        elif ch == "^":
            out.append(r"\^{}")
        elif ch == "~":
            out.append(r"\textasciitilde{}")
        else:
            out.append(ch)
    return "".join(out)
