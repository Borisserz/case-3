"""Numbers in a new report or deck. Memory is not a source of them."""

from __future__ import annotations

import re
from typing import Any

from case3.chat_turn import _NUM, _norm_num, latest_user_line, number_norms, stray_numbers

_PROTECT = re.compile(
    r"\\includegraphics\s*(?:\[[^\]]*\])?\{[^}]*\}"
    r"|\\begin\{tabularx?\*?\}\s*\{[^}]*\}"
    r"|\\(?:label|ref|pageref|cite\w*)\{[^}]*\}"
    r"|(?<!\\)%[^\n]*"
    r"|\\(?:vspace|hspace|setlength|fontsize)\{[^}]*\}",
    re.IGNORECASE,
)
_JS_ARRAY = re.compile(
    r"(data|labels)\s*:\s*\[([^\]]*)\]",
    re.IGNORECASE,
)
_QUOTED = re.compile(r"(['\"])([^'\"]*)\1")


def allowed_fact_norms(source: str, intent: str) -> set[str]:
    """Source, this message, and numbers the user wrote earlier."""
    from case3.chat_turn import user_stated_norms

    return number_norms(source) | number_norms(latest_user_line(intent)) | user_stated_norms(intent)


def fact_number_tokens(source: str, intent: str) -> frozenset[str]:
    """Spellings a slide may repeat. ``12,5`` in Source allows ``12.5``."""
    tokens: set[str] = set()
    for norm in allowed_fact_norms(source, intent):
        if not norm:
            continue
        tokens.add(norm)
        tokens.add(norm.replace(".", ","))
        tokens.add(norm + "%")
    return frozenset(tokens)


def _has_stray(chunk: str, stray: set[str]) -> bool:
    return any(_norm_num(match.group(0)) in stray for match in _NUM.finditer(chunk))


def _has_kept(chunk: str, stray: set[str]) -> bool:
    return any(_norm_num(match.group(0)) not in stray for match in _NUM.finditer(chunk))


def _scrub_tokens(chunk: str, stray: set[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        if _norm_num(match.group(0)) in stray:
            return ""
        return match.group(0)

    return _NUM.sub(repl, chunk)


def _scrub_clauses(sentence: str, stray: set[str]) -> str:
    """Drop a clause whose only numbers are foreign. A heading on its own line stays."""
    kept_lines: list[str] = []
    for line in sentence.split("\n"):
        kept: list[str] = []
        for part in re.split(r",(?!\d)\s*", line):
            if not part.strip():
                continue
            if _has_stray(part, stray) and not _has_kept(part, stray):
                continue
            if _has_stray(part, stray):
                part = _scrub_tokens(part, stray)
            if part.strip():
                kept.append(part.strip())
        if kept:
            kept_lines.append(", ".join(kept))
    return "\n".join(kept_lines)


def _scrub_region(text: str, stray: set[str]) -> str:
    """Drop the clause that carried a foreign number. Leave the next sentence."""
    if not text or not stray:
        return text or ""
    kept_lines: list[str] = []
    for line in text.split("\n"):
        bits = re.split(r"([.!?]+(?:\s+|$))", line)
        kept: list[str] = []
        index = 0
        while index < len(bits):
            chunk = bits[index]
            delim = bits[index + 1] if index + 1 < len(bits) else ""
            index += 2 if delim else 1
            cleaned = _scrub_clauses(chunk, stray)
            if not cleaned.strip():
                continue
            kept.append(cleaned)
            if delim and (not _has_stray(chunk, stray) or _has_kept(chunk, stray)):
                kept.append(delim)
        if kept:
            kept_lines.append("".join(kept).strip())
    result = "\n".join(kept_lines)
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r" +([,.;:!?])", r"\1", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def _parts(body: str) -> list[tuple[str, bool]]:
    """(text, protected). Protected spans stay byte for byte."""
    parts: list[tuple[str, bool]] = []
    pos = 0
    for match in _PROTECT.finditer(body):
        if match.start() > pos:
            parts.append((body[pos : match.start()], False))
        parts.append((match.group(0), True))
        pos = match.end()
    if pos < len(body):
        parts.append((body[pos:], False))
    return parts


def _split_document(tex: str) -> tuple[str, str, str]:
    begin = re.search(r"\\begin\{document\}", tex or "")
    if not begin:
        return tex or "", "", ""
    end = tex.find(r"\end{document}", begin.end())
    if end < 0:
        return tex[: begin.end()], tex[begin.end() :], ""
    return tex[: begin.end()], tex[begin.end() : end], tex[end:]


def _quote_is_fact(inner: str) -> bool:
    """A caption or tooltip. A color or an rgba() string is not a fact."""
    if re.search(r"[А-Яа-яЁё]", inner or ""):
        return True
    if re.search(r"тыс|млн|млрд|чел|°|%", inner or "", re.IGNORECASE):
        return True
    return bool(re.fullmatch(r"\s*\d+(?:[.,]\d+)?%?\s*", inner or ""))


def _scrub_html(html: str, stray: set[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        kind = match.group(1)
        empty = "null" if kind.lower() == "data" else "''"

        def one(num: re.Match[str]) -> str:
            if _norm_num(num.group(0)) in stray:
                return empty
            return num.group(0)

        return f"{kind}: [{_NUM.sub(one, match.group(2))}]"

    def repl_quote(match: re.Match[str]) -> str:
        if not _quote_is_fact(match.group(2)):
            return match.group(0)
        return match.group(1) + _scrub_region(match.group(2), stray) + match.group(1)

    return _QUOTED.sub(repl_quote, _JS_ARRAY.sub(repl, html or ""))


def _visible(tex: str, charts: list, figures: list, diagrams: list) -> str:
    _head, body, _tail = _split_document(tex)
    chunks = [piece for piece, protected in _parts(body) if not protected]
    for item in list(charts) + list(figures) + list(diagrams):
        if not isinstance(item, dict):
            continue
        for key in ("caption", "insight", "title", "prompt", "mermaid"):
            val = item.get(key)
            if isinstance(val, str):
                chunks.append(val)
        html = item.get("html")
        if isinstance(html, str):
            chunks.append(html)
        for row in item.get("highlights") or []:
            if isinstance(row, dict):
                chunks.extend(str(row.get(k) or "") for k in ("label", "value", "pct"))
    return "\n".join(chunks)


def ground_generated(
    tex: str,
    charts: list[dict[str, Any]] | None,
    figures: list[dict[str, Any]] | None,
    diagrams: list[dict[str, Any]] | None,
    *,
    source: str,
    intent: str,
) -> tuple[str, list, list, list, list[str]]:
    """Drop fact-numbers that are not in Source and not in the user's message."""
    charts = [dict(item) for item in (charts or []) if isinstance(item, dict)]
    figures = [dict(item) for item in (figures or []) if isinstance(item, dict)]
    diagrams = [dict(item) for item in (diagrams or []) if isinstance(item, dict)]
    dropped = stray_numbers(
        _visible(tex, charts, figures, diagrams),
        allowed_fact_norms(source, intent),
    )
    stray = {_norm_num(token) for token in dropped}
    if not stray:
        return tex, charts, figures, diagrams, []
    head, body, tail = _split_document(tex)
    body = "".join(
        piece if protected else _scrub_region(piece, stray)
        for piece, protected in _parts(body)
    )
    tex = head + body + tail
    for item in charts:
        for key in ("caption", "insight"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_region(item[key], stray).strip()
        if isinstance(item.get("html"), str):
            item["html"] = _scrub_html(item["html"], stray)
        rows = []
        for row in item.get("highlights") or []:
            if not isinstance(row, dict):
                continue
            nxt = dict(row)
            for key in ("label", "value", "pct"):
                if isinstance(nxt.get(key), str):
                    nxt[key] = _scrub_region(nxt[key], stray).strip()
            rows.append(nxt)
        if rows:
            item["highlights"] = rows
    for item in figures:
        for key in ("caption", "prompt"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_region(item[key], stray).strip()
    for item in diagrams:
        for key in ("title", "caption", "mermaid"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_region(item[key], stray)
    return tex, charts, figures, diagrams, dropped
