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


def fact_context(source: str, intent: str) -> tuple[set[str], list[tuple[str, str]]]:
    """Norms that may stand anywhere, and (norm, stem) pairs from earlier user lines."""
    from case3.chat_memory import _stem
    from case3.chat_turn import latest_user_line, number_norms

    message = latest_user_line(intent)
    global_ok = number_norms(source) | number_norms(message)
    bindings: list[tuple[str, str]] = []
    text = intent or ""
    mark = "Числа из реплик пользователя"
    at = text.find(mark)
    if at < 0:
        return global_ok, bindings
    rest = text[at + len(mark) :]
    body = rest.split("\n", 1)[1] if "\n" in rest else ""
    line = body.split("\n", 1)[0]
    for match in re.finditer(
        r"(\d+(?:[.,]\d+)?%?)(?:\s+([0-9A-Za-zА-Яа-яЁё]{3,}))?",
        line,
    ):
        norm = _norm_num(match.group(1))
        raw = match.group(2) or ""
        stem = _stem(raw) if raw else ""
        if len(stem) < 4:
            stem = ""
        if norm:
            bindings.append((norm, stem))
    return global_ok, bindings


def _clause_allows(
    clause: str,
    norm: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
) -> bool:
    if norm in global_ok:
        return True
    from case3.chat_memory import _stem_set

    stems = _stem_set(clause)
    return any(bound == norm and stem and stem in stems for bound, stem in bindings)


def _scrub_bound(
    text: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    *,
    context: str = "",
) -> str:
    """Drop a number that is not in Source, this message, or beside its own word."""
    from case3.chat_turn import _SPOKEN_NUMBER, _SPOKEN_RE

    def spoken_norm(token: str) -> str:
        stem = token.casefold().replace("ё", "е")
        for prefix, digit in _SPOKEN_NUMBER:
            if stem.startswith(prefix):
                return digit
        return ""

    def clean_clause(clause: str) -> str:
        digits = [_norm_num(match.group(0)) for match in _NUM.finditer(clause)]
        words = [(match.group(0), spoken_norm(match.group(0))) for match in _SPOKEN_RE.finditer(clause)]
        norms = [norm for norm in digits + [digit for _word, digit in words] if norm]
        if not norms:
            return clause
        judged = f"{context} {clause}".strip() if context else clause
        bad = {norm for norm in norms if not _clause_allows(judged, norm, global_ok, bindings)}
        if not bad:
            return clause
        if len(bad) == len(set(norms)):
            return ""

        def digit_repl(match: re.Match[str]) -> str:
            if _norm_num(match.group(0)) in bad:
                return ""
            return match.group(0)

        def word_repl(match: re.Match[str]) -> str:
            if spoken_norm(match.group(0)) in bad:
                return ""
            return match.group(0)

        return _SPOKEN_RE.sub(word_repl, _NUM.sub(digit_repl, clause))

    kept_lines: list[str] = []
    for line in (text or "").split("\n"):
        bits = re.split(r"([.!?]+(?:\s+|$))", line)
        kept: list[str] = []
        index = 0
        while index < len(bits):
            chunk = bits[index]
            delim = bits[index + 1] if index + 1 < len(bits) else ""
            index += 2 if delim else 1
            parts = []
            for part in re.split(r",(?!\d)\s*", chunk):
                cleaned = clean_clause(part).strip()
                if cleaned:
                    parts.append(cleaned)
            if not parts:
                continue
            kept.append(", ".join(parts))
            if delim:
                kept.append(delim)
        if kept:
            kept_lines.append("".join(kept).strip())
    result = "\n".join(kept_lines)
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r" +([,.;:!?])", r"\1", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


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
    global_ok, bindings = fact_context(source, intent)
    visible = _visible(tex, charts, figures, diagrams)
    dropped = [
        token
        for token in stray_numbers(visible, global_ok)
        if not _clause_allows(visible, _norm_num(token), global_ok, bindings)
    ]
    # A bound number can be legal in one sentence and illegal in the next.
    # Scrub per sentence even when the flat list still contains the value.
    head, body, tail = _split_document(tex)
    body = "".join(
        piece if protected else _scrub_bound(piece, global_ok, bindings)
        for piece, protected in _parts(body)
    )
    tex = head + body + tail
    for item in charts:
        for key in ("caption", "insight"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(item[key], global_ok, bindings).strip()
        if isinstance(item.get("html"), str):
            item["html"] = _scrub_html_bound(item["html"], global_ok, bindings)
        rows = []
        for row in item.get("highlights") or []:
            if not isinstance(row, dict):
                continue
            nxt = dict(row)
            label = str(nxt.get("label") or "")
            before_value = str(nxt.get("value") or "")
            for key in ("label", "value", "pct"):
                if isinstance(nxt.get(key), str):
                    nxt[key] = _scrub_bound(
                        nxt[key],
                        global_ok,
                        bindings,
                        context="" if key == "label" else label,
                    ).strip()
            if before_value.strip() and not str(nxt.get("value") or "").strip():
                continue
            rows.append(nxt)
        if rows:
            item["highlights"] = rows
    for item in figures:
        for key in ("caption", "prompt"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(item[key], global_ok, bindings).strip()
    for item in diagrams:
        for key in ("title", "caption", "mermaid"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(item[key], global_ok, bindings)
    return tex, charts, figures, diagrams, dropped


def _scrub_html_bound(
    html: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
) -> str:
    """Chart data takes only Source and this message. A caption may use a bound word."""

    def repl(match: re.Match[str]) -> str:
        kind = match.group(1)
        empty = "null" if kind.lower() == "data" else "''"

        def one(num: re.Match[str]) -> str:
            if _norm_num(num.group(0)) not in global_ok:
                return empty
            return num.group(0)

        return f"{kind}: [{_NUM.sub(one, match.group(2))}]"

    def repl_quote(match: re.Match[str]) -> str:
        if not _quote_is_fact(match.group(2)):
            return match.group(0)
        return match.group(1) + _scrub_bound(match.group(2), global_ok, bindings) + match.group(1)

    return _QUOTED.sub(repl_quote, _JS_ARRAY.sub(repl, html or ""))


def bind_deck_numbers(deck: dict[str, Any], *, source: str, intent: str) -> dict[str, Any]:
    """A historical user number stays on a slide only beside its word."""
    global_ok, bindings = fact_context(source, intent)
    if not isinstance(deck, dict):
        return deck
    slides = []
    for slide in deck.get("slides") or []:
        if not isinstance(slide, dict):
            slides.append(slide)
            continue
        nxt = dict(slide)
        for key in ("title", "subtitle", "caption", "body", "kicker", "takeaway", "term", "definition"):
            if isinstance(nxt.get(key), str):
                nxt[key] = _scrub_bound(str(nxt[key]), global_ok, bindings).strip()
        if isinstance(nxt.get("bullets"), list):
            nxt["bullets"] = [
                cleaned
                for item in nxt["bullets"]
                if (cleaned := _scrub_bound(str(item), global_ok, bindings).strip())
            ]
        if isinstance(nxt.get("kpis"), list):
            kept = []
            for kpi in nxt["kpis"]:
                if not isinstance(kpi, dict):
                    continue
                label = str(kpi.get("label") or "")
                value = str(kpi.get("value") or "")
                clause = f"{label} {value}"
                norms = {_norm_num(token) for token in _NUM.findall(value)}
                if norms and not all(_clause_allows(clause, norm, global_ok, bindings) for norm in norms):
                    continue
                kept.append(kpi)
            nxt["kpis"] = kept
        slides.append(nxt)
    out = dict(deck)
    out["slides"] = slides
    return out
