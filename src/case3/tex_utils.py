"""Extract LaTeX from model output."""

from __future__ import annotations

import re

_FENCE = re.compile(r"```(?:latex|tex)?\s*([\s\S]*?)```", re.I)


def extract_tex(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty model output")
    m = _FENCE.search(text)
    if m:
        text = m.group(1).strip()
    idx = text.find(r"\documentclass")
    if idx > 0:
        text = text[idx:]
    if r"\documentclass" not in text:
        raise ValueError("no \\documentclass in model output")
    if r"\begin{document}" not in text or r"\end{document}" not in text:
        raise ValueError("missing \\begin{document} / \\end{document}")
    return text.strip() + "\n"
