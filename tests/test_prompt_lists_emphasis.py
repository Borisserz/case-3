"""D6: system prompt must teach itemize/enumerate/emph as first-class."""

from __future__ import annotations

from pathlib import Path

PROMPT = Path(__file__).resolve().parents[1] / "prompt" / "system_tex.md"


def test_system_tex_lists_and_emphasis_guidance() -> None:
    text = PROMPT.read_text(encoding="utf-8")
    assert r"\begin{itemize}" in text
    assert r"\begin{enumerate}" in text
    assert r"\textbf{" in text or r"\textbf{…}" in text
    assert r"\emph{" in text or r"\emph{…}" in text
    assert "Lists & emphasis" in text or "D6" in text
