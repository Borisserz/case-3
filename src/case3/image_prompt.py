"""Validate / sanitize Kandinsky image prompts from the LLM."""

from __future__ import annotations

import re
import unicodedata

_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Allow common punctuation; reject most other scripts / symbols spam.
_ALLOWED = re.compile(r"[^A-Za-z0-9\s.,;:!?()\[\]{}'\"\-_/\\%@&+=*#]")


class ImagePromptError(ValueError):
    """Image prompt failed validation."""


def sanitize_image_prompt(
    prompt: str,
    *,
    min_len: int = 8,
    max_len: int = 800,
) -> str:
    text = unicodedata.normalize("NFKC", prompt or "")
    text = _CTRL.sub("", text)
    text = " ".join(text.split())
    if not text:
        raise ImagePromptError("empty image prompt")
    if _CYRILLIC.search(text):
        raise ImagePromptError("image prompt must be English (no Cyrillic)")
    # Strip leftover non-Latin letters (Greek, CJK, etc.)
    cleaned = []
    for ch in text:
        if ch.isalpha() and ord(ch) > 127:
            raise ImagePromptError("image prompt must use Latin letters only")
        cleaned.append(ch)
    text = "".join(cleaned)
    text = _ALLOWED.sub(" ", text)
    text = " ".join(text.split())
    if len(text) < min_len:
        raise ImagePromptError(f"image prompt too short (<{min_len})")
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text
