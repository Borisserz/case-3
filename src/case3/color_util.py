"""Shared hex helpers for decks / charts / DOCX (no purple invent)."""

from __future__ import annotations

import re

_HEX6 = re.compile(r"^[0-9a-fA-F]{6}$")
_HEX3 = re.compile(r"^[0-9a-fA-F]{3}$")


def expand_hex(hx: str) -> str:
    """``#abc`` → ``#AABBCC``; already-6 stays upper with leading ``#``."""
    raw = (hx or "").strip().lstrip("#")
    if _HEX3.fullmatch(raw):
        raw = "".join(c * 2 for c in raw)
    if _HEX6.fullmatch(raw):
        return f"#{raw.upper()}"
    return f"#{raw}"


def norm_hex(value: str | None, fallback: str = "#000000") -> str:
    """Normalize to ``#RRGGBB`` or return normalized ``fallback`` if invalid/empty."""
    raw = (value or "").strip()
    if raw:
        if not raw.startswith("#"):
            raw = f"#{raw}"
        body = raw.lstrip("#")
        if _HEX3.fullmatch(body) or _HEX6.fullmatch(body):
            return expand_hex(raw)
    fb = (fallback or "#000000").strip()
    if not fb.startswith("#"):
        fb = f"#{fb}"
    body = fb.lstrip("#")
    if _HEX3.fullmatch(body) or _HEX6.fullmatch(body):
        return expand_hex(fb)
    return "#000000"


def hex_to_rgb(hx: str) -> tuple[int, int, int] | None:
    """Parse ``#RGB`` / ``#RRGGBB`` → (r, g, b) or None."""
    raw = (hx or "").strip().lstrip("#")
    if _HEX3.fullmatch(raw):
        raw = "".join(c * 2 for c in raw)
    if not _HEX6.fullmatch(raw):
        return None
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
