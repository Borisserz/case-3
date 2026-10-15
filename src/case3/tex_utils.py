"""Extract and validate LaTeX from model output."""

from __future__ import annotations

import re

_FENCE = re.compile(r"```(?:latex|tex)?\s*([\s\S]*?)```", re.I)


def extract_tex(raw: str) -> str:
    """Prefer fenced ```latex block; else whole answer; strip chatter."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty model output")
    m = _FENCE.search(text)
    if m:
        text = m.group(1).strip()
    # Drop leading prose before \documentclass
    idx = text.find(r"\documentclass")
    if idx > 0:
        text = text[idx:]
    if r"\documentclass" not in text:
        raise ValueError("no \\documentclass in model output — not a full .tex document")
    if r"\begin{document}" not in text or r"\end{document}" not in text:
        raise ValueError("missing \\begin{document} / \\end{document}")
    return text.strip() + "\n"


def list_includegraphics(tex: str) -> list[str]:
    return re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
