"""Extract LaTeX from model output."""

from __future__ import annotations

import re

_FENCE = re.compile(r"```(\w*)\s*([\s\S]*?)```", re.I)

_MIN_PREAMBLE = r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\usepackage{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\usepackage{graphicx}
\usepackage{hyperref}
\setdefaultlanguage{russian}
\setotherlanguage{english}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
\geometry{margin=2.5cm}
"""


def _normalize_backslashes(text: str) -> str:
    """Models sometimes emit \\\\documentclass or unicode dashes — normalize."""
    t = text.replace("\u200b", "").replace("\ufeff", "")
    # Double-escaped TeX control words → single backslash
    t = re.sub(r"\\\\(documentclass|begin|end|usepackage|section)\b", r"\\\1", t)
    return t


def _looks_like_tex(body: str) -> bool:
    b = body or ""
    return r"\documentclass" in b or (
        r"\begin{document}" in b and r"\end{document}" in b
    )


def _ensure_documentclass(text: str) -> str:
    """If body has begin/end document but no class, prepend our preamble."""
    if r"\documentclass" in text:
        return text
    if r"\begin{document}" in text and r"\end{document}" in text:
        # Drop a leading title-only fragment before \begin{document}
        idx = text.find(r"\begin{document}")
        return _MIN_PREAMBLE + "\n" + text[idx:].lstrip()
    return text


def extract_tex(raw: str) -> str:
    text = _normalize_backslashes((raw or "").strip())
    if not text:
        raise ValueError("empty model output")

    # Prefer fenced bodies that look like a full document
    candidates: list[str] = []
    for m in _FENCE.finditer(text):
        lang = (m.group(1) or "").lower()
        body = m.group(2).strip()
        if lang in ("latex", "tex") or (lang == "" and _looks_like_tex(body)):
            candidates.append(body)
        elif lang in ("",) and r"\begin{document}" in body:
            candidates.append(body)

    chosen = None
    for body in candidates:
        if r"\documentclass" in body:
            chosen = body
            break
    if chosen is None:
        for body in candidates:
            if r"\begin{document}" in body:
                chosen = body
                break
    if chosen is None and candidates:
        chosen = candidates[0]

    if chosen is not None:
        text = chosen
    else:
        # Unfenced: cut from first \documentclass if present
        idx = text.find(r"\documentclass")
        if idx >= 0:
            text = text[idx:]
        else:
            idx = text.find(r"\begin{document}")
            if idx >= 0:
                text = text[idx:]

    text = _ensure_documentclass(text.strip())

    if r"\documentclass" not in text:
        preview = (raw or "").strip().replace("\n", " ")[:240]
        raise ValueError(
            "no \\documentclass in model output "
            "(нужен полный LaTeX: ```latex … \\documentclass … \\end{document}```). "
            f"Начало ответа модели: {preview!r}"
        )
    if r"\begin{document}" not in text or r"\end{document}" not in text:
        raise ValueError("missing \\begin{document} / \\end{document}")
    return text.strip() + "\n"
