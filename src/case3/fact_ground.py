"""Numbers in a new report or deck. Memory is not a source of them."""

from __future__ import annotations

import re
from typing import Any

from case3.chart_number import compact_chart_number_text, take_chart_number
from case3.chat_turn import _NUM, _norm_num, latest_user_line, number_norms, stray_numbers

_PROTECT = re.compile(
    r"\\includegraphics\s*(?:\[[^\]]*\])?\{[^}]*\}"
    r"|\\begin\{tabularx?\*?\}\s*\{[^}]*\}"
    r"|\\(?:label|ref|pageref|cite\w*)\{[^}]*\}"
    r"|(?<!\\)%[^\n]*"
    r"|\\(?:vspace|hspace|setlength|fontsize)\{[^}]*\}"
    r"|\\(?:multicolumn|multirow)\{[^}]*\}\{[^}]*\}"
    r"|\\(?:cmidrule|cline|hhline)\{[^}]*\}"
    r"|\\\\\[[^\]]*\]",
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


class TableGrid:
    """Row stem → numbers that belong on that row, split by column."""

    def __init__(self) -> None:
        self.rows: dict[str, set[str]] = {}
        self.values: dict[tuple[str, str], set[str]] = {}
        self.shares: dict[tuple[str, str], set[str]] = {}
        self.ranks: dict[tuple[str, str], set[str]] = {}
        self.columns: set[str] = set()

    def add(
        self,
        bucket: dict[tuple[str, str], set[str]],
        row: str,
        col: str,
        norms: set[str],
    ) -> None:
        clean = {norm for norm in norms if norm}
        if not clean or not row:
            return
        if col:
            bucket.setdefault((row, col), set()).update(clean)
            self.columns.add(col)
        else:
            bucket.setdefault((row, ""), set()).update(clean)
        if bucket is self.values:
            self.rows.setdefault(row, set()).update(clean)


_GENERIC_ROW = frozenset(
    {
        "область",
        "област",
        "регион",
        "район",
        "итого",
        "итог",
        "всего",
        "всег",
        "total",
    }
)
_DERIV_LINE = re.compile(
    r"^[-*]\s+(.+?)\s+[—-]\s+доля\s+(\d[\d \u00a0.,]*%?)\s*,\s*место\s+(\d+)\s*$"
)


def _name_stems(label: str) -> set[str]:
    from case3.chat_memory import _stem

    found: set[str] = set()
    for word in re.findall(r"[0-9A-Za-zА-Яа-яЁё]{4,}", label or ""):
        stem = _stem(word)
        if len(stem) < 4 or stem in _GENERIC_ROW:
            continue
        found.add(stem)
    return found


def table_grid(source: str) -> TableGrid:
    """One cell stays on its row and its column. A shared word is not a row key."""
    from collections import Counter

    from case3.dashboard_source import _label_column, _markdown_tables

    grid = TableGrid()
    stem_rows: list[set[str]] = []
    row_cells: list[dict[str, set[str]]] = []
    for _title, rows in _markdown_tables(source or ""):
        if len(rows) < 2:
            continue
        header, body = rows[0], rows[1:]
        label_at = _label_column(body)
        width = max(len(row) for row in rows)
        col_stems: dict[int, str] = {}
        for col in range(width):
            if label_at is not None and col == label_at:
                continue
            name = header[col].strip() if col < len(header) else ""
            stems = _name_stems(name)
            if stems:
                col_stems[col] = max(stems, key=len)
        for row in body:
            label = row[label_at].strip() if label_at is not None and label_at < len(row) else ""
            cells: dict[str, set[str]] = {}
            for col in range(width):
                if label_at is not None and col == label_at:
                    continue
                cell = row[col].strip() if col < len(row) else ""
                norms = number_norms(cell)
                if not norms:
                    continue
                # «Май» is three letters, so it never becomes a column stem.
                # The number still belongs to the row.
                cells.setdefault(col_stems.get(col, ""), set()).update(norms)
            stem_rows.append(_name_stems(label))
            row_cells.append(cells)
    counts = Counter(stem for stems in stem_rows for stem in stems)
    for stems, cells in zip(stem_rows, row_cells):
        for key in {stem for stem in stems if counts[stem] == 1}:
            for col, norms in cells.items():
                grid.add(grid.values, key, col, norms)
    _add_derivatives(grid, source or "")
    return grid


def _add_derivatives(grid: TableGrid, source: str) -> None:
    column = ""
    for raw in (source or "").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith("#"):
            continue
        match = _DERIV_LINE.match(stripped)
        if not match:
            if "Доли и места" in stripped:
                continue
            column = stripped
            continue
        label, share, rank = match.group(1), match.group(2), match.group(3)
        named = _name_stems(column)
        col = max(named, key=len) if named else ""
        for stem in _name_stems(label):
            if stem not in grid.rows:
                continue
            grid.add(grid.shares, stem, col, number_norms(share))
            grid.add(grid.ranks, stem, col, number_norms(rank))


def _mentions_share(clause: str) -> bool:
    folded = (clause or "").casefold().replace("ё", "е")
    return "дол" in folded or "%" in clause


def _mentions_rank(clause: str) -> bool:
    return "мест" in (clause or "").casefold()


def _row_mentions(clause: str, grid: TableGrid) -> list[tuple[int, int, str]]:
    from case3.chat_memory import _stem

    found: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[0-9A-Za-zА-Яа-яЁё]{4,}", clause or ""):
        stem = _stem(match.group(0))
        if len(stem) < 4 or stem not in grid.rows:
            continue
        found.append((match.start(), match.end(), stem))
    return found


def _owner_row(mentions: list[tuple[int, int, str]], start: int) -> str | None:
    """The region name closest to this number. The one before it wins a tie."""
    before = [item for item in mentions if item[1] <= start]
    if before:
        return max(before, key=lambda item: item[1])[2]
    after = [item for item in mentions if item[0] >= start]
    if after:
        return min(after, key=lambda item: item[0])[2]
    return None


def _norms_on_row(grid: TableGrid, row: str, clause: str, columns: list[str]) -> set[str]:
    share = _mentions_share(clause)
    rank = _mentions_rank(clause)
    buckets = []
    if share:
        buckets.append(grid.shares)
    if rank:
        buckets.append(grid.ranks)
    if not share and not rank:
        buckets.append(grid.values)
    allowed: set[str] = set()
    for bucket in buckets:
        if columns:
            for col in columns:
                allowed |= bucket.get((row, col), set())
        else:
            for (key, _col), norms in bucket.items():
                if key == row:
                    allowed |= norms
    return allowed


def _row_allows(clause: str, norm: str, grid: TableGrid | None) -> bool | None:
    """False when the sentence names a row and the number is not on it.

    Two region names in one sentence do not share a sum. A share is not a sum:
    ``52,9`` is allowed only where the sentence says «доля» or writes ``%``.
    """
    if grid is None or not grid.rows or not norm:
        return None
    mentions = _row_mentions(clause, grid)
    if not mentions:
        return None
    from case3.chat_memory import _stem_set

    columns = [stem for stem in _stem_set(clause) if stem in grid.columns]
    rows: list[str] = []
    for _start, _end, stem in mentions:
        if stem not in rows:
            rows.append(stem)
    spans = [
        match.start()
        for match in _NUM.finditer(clause)
        if _norm_num(match.group(0)) == norm
    ]
    if len(rows) > 1 and spans:
        for start in spans:
            owner = _owner_row(mentions, start)
            if owner is None or norm not in _norms_on_row(grid, owner, clause, columns):
                return False
        return True
    if len(rows) > 1:
        return all(norm in _norms_on_row(grid, row, clause, columns) for row in rows)
    return norm in _norms_on_row(grid, rows[0], clause, columns)


def wrong_row_tokens(
    text: str | None,
    source: str | None,
    message: str | None = "",
) -> list[str]:
    """A number that exists, but on a different row from the one named here."""
    from case3.chat_turn import _is_list_marker

    grid = table_grid(source or "")
    if not grid.rows:
        return []
    message_ok = number_norms(message)
    source_ok = number_norms(source)
    found: list[str] = []
    seen: set[str] = set()
    for line in (text or "").split("\n"):
        for chunk in re.split(r"[.!?]+", line):
            for part in re.split(r",(?!\d)\s*", chunk):
                for match in _NUM.finditer(part):
                    if _is_list_marker(part, match.start(), match.end()):
                        continue
                    norm = _norm_num(match.group(0))
                    if not norm or norm in message_ok or norm in seen or norm not in source_ok:
                        continue
                    if _row_allows(part, norm, grid) is False:
                        seen.add(norm)
                        found.append(match.group(0))
    return found


def _chart_labels(html: str) -> list[str]:
    """Category names in order. One labels array per chart."""
    match = re.search(r"labels\s*:\s*\[([^\]]*)\]", html or "", re.IGNORECASE)
    if not match:
        return []
    return [item.group(2) for item in _QUOTED.finditer(match.group(1))]


def _row_norms_for_label(label: str, grid: TableGrid | None) -> set[str] | None:
    """Numbers on the one table row this label names. None when it names none."""
    if grid is None or not grid.rows:
        return None
    hits = [stem for stem in _name_stems(label) if stem in grid.rows]
    if len(hits) != 1:
        return None
    return grid.rows[hits[0]]


def _rewrite_chart_body(kind: str, body: str, reject, slot_reject=None) -> str:
    """``[100,40]`` is two points. ``12,5`` is one point and is written with a dot."""
    empty = "null" if kind.lower() == "data" else "''"
    is_data = kind.lower() == "data"
    slot = 0
    text = compact_chart_number_text(body)
    parts: list[str] = []
    index = 0
    size = len(text)
    while index < size:
        if text[index : index + 4].lower() == "null" and (
            index == 0 or not text[index - 1].isalnum()
        ):
            parts.append("null")
            index += 4
            if is_data:
                slot += 1
            continue
        taken = take_chart_number(text, index)
        if taken:
            token, index = taken
            bad = reject(token)
            if not bad and is_data and slot_reject is not None:
                bad = slot_reject(token, slot)
            parts.append(empty if bad else token)
            if is_data:
                slot += 1
            continue
        parts.append(text[index])
        index += 1
    return f"{kind}: [{''.join(parts)}]"


def _clause_allows(
    clause: str,
    norm: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    grid: TableGrid | None = None,
    message_ok: set[str] | None = None,
) -> bool:
    if message_ok and norm in message_ok:
        return True
    on_row = _row_allows(clause, norm, grid)
    if on_row is not None:
        return on_row
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
    grid: TableGrid | None = None,
    message_ok: set[str] | None = None,
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
        bad = {
            norm
            for norm in norms
            if not _clause_allows(
                judged, norm, global_ok, bindings, grid, message_ok
            )
        }
        if not bad:
            return clause
        # One illegal number ruins the clause. Cutting it out leaves «в раза».
        return ""

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
            cut = False
            for part in re.split(r"(?<![{\\]),(?!\d)\s*", chunk):
                raw = part.strip()
                cleaned = clean_clause(part).strip()
                if not cleaned or re.fullmatch(r"[\s\\%{},.;:–—\-]*", cleaned):
                    if raw and (_NUM.search(raw) or _SPOKEN_RE.search(raw)):
                        cut = True
                    continue
                # «три месяца: март, апрель и май» leaves the lowercase tail.
                if cut and cleaned[:1].islower() and not _NUM.search(cleaned):
                    continue
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


def _scrub_title(
    head: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    *,
    grid: TableGrid | None,
    message_ok: set[str] | None,
) -> str:
    """A foreign number in ``\\title`` would print on the first page."""

    def repl(match: re.Match[str]) -> str:
        inner = _scrub_bound(
            match.group(1),
            global_ok,
            bindings,
            grid=grid,
            message_ok=message_ok,
        ).strip()
        if not re.search(r"[0-9A-Za-zА-Яа-яЁё]", inner):
            inner = "Отчёт"
        return r"\title{" + inner + "}"

    return re.sub(r"\\title\{([^{}]*)\}", repl, head or "", count=1)


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
        return _rewrite_chart_body(kind, match.group(2), lambda token: _norm_num(token) in stray)

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
    grid = table_grid(source)
    message_ok = number_norms(latest_user_line(intent))
    visible = _visible(tex, charts, figures, diagrams)
    dropped = [
        token
        for token in stray_numbers(visible, global_ok)
        if not _clause_allows(
            visible, _norm_num(token), global_ok, bindings, grid, message_ok
        )
    ]
    # A bound number can be legal in one sentence and illegal in the next.
    # Scrub per sentence even when the flat list still contains the value.
    head, body, tail = _split_document(tex)
    head = _scrub_title(
        head, global_ok, bindings, grid=grid, message_ok=message_ok
    )
    body = "".join(
        piece
        if protected
        else _scrub_bound(
            piece, global_ok, bindings, grid=grid, message_ok=message_ok
        )
        for piece, protected in _parts(body)
    )
    tex = head + body + tail
    for item in charts:
        for key in ("caption", "insight"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(
                    item[key], global_ok, bindings, grid=grid, message_ok=message_ok
                ).strip()
        if isinstance(item.get("html"), str):
            item["html"] = _scrub_html_bound(
                item["html"], global_ok, bindings, grid, message_ok
            )
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
                        grid=grid,
                        message_ok=message_ok,
                    ).strip()
            if before_value.strip() and not str(nxt.get("value") or "").strip():
                continue
            rows.append(nxt)
        if rows:
            item["highlights"] = rows
    for item in figures:
        for key in ("caption", "prompt"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(
                    item[key], global_ok, bindings, grid=grid, message_ok=message_ok
                ).strip()
    for item in diagrams:
        for key in ("title", "caption", "mermaid"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(
                    item[key], global_ok, bindings, grid=grid, message_ok=message_ok
                )
    return tex, charts, figures, diagrams, dropped


def _scrub_html_bound(
    html: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    grid: TableGrid | None = None,
    message_ok: set[str] | None = None,
) -> str:
    """Chart data takes only Source and this message. A label keeps its own row.

    A caption may use a bound word. A month label is not a table row, so its
    point stays when the number itself is in Source.
    """
    labels = _chart_labels(html)

    def slot_reject(token: str, slot: int) -> bool:
        norm = _norm_num(token)
        if message_ok and norm in message_ok:
            return False
        if slot >= len(labels):
            return False
        allowed = _row_norms_for_label(labels[slot], grid)
        if allowed is None:
            return False
        return norm not in allowed

    def repl(match: re.Match[str]) -> str:
        kind = match.group(1)
        return _rewrite_chart_body(
            kind,
            match.group(2),
            lambda token: _norm_num(token) not in global_ok,
            slot_reject if kind.lower() == "data" else None,
        )

    def repl_quote(match: re.Match[str]) -> str:
        if not _quote_is_fact(match.group(2)):
            return match.group(0)
        return (
            match.group(1)
            + _scrub_bound(
                match.group(2),
                global_ok,
                bindings,
                grid=grid,
                message_ok=message_ok,
            )
            + match.group(1)
        )

    return _QUOTED.sub(repl_quote, _JS_ARRAY.sub(repl, html or ""))


def bind_deck_numbers(deck: dict[str, Any], *, source: str, intent: str) -> dict[str, Any]:
    """A historical user number stays on a slide only beside its word."""
    global_ok, bindings = fact_context(source, intent)
    grid = table_grid(source)
    message_ok = number_norms(latest_user_line(intent))
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
                nxt[key] = _scrub_bound(
                    str(nxt[key]), global_ok, bindings, grid=grid, message_ok=message_ok
                ).strip()
        if isinstance(nxt.get("bullets"), list):
            nxt["bullets"] = [
                cleaned
                for item in nxt["bullets"]
                if (
                    cleaned := _scrub_bound(
                        str(item), global_ok, bindings, grid=grid, message_ok=message_ok
                    ).strip()
                )
            ]
        if isinstance(nxt.get("rows"), list):
            rows: list[list[str]] = []
            for row in nxt["rows"]:
                if not isinstance(row, list):
                    continue
                cells = [
                    _scrub_bound(
                        str(cell),
                        global_ok,
                        bindings,
                        grid=grid,
                        message_ok=message_ok,
                    ).strip()
                    for cell in row
                ]
                if any(cell.strip() for cell in cells):
                    rows.append(cells)
            if rows:
                header, data = rows[0], rows[1:]
                data = [row for row in data if any(re.search(r"\d", cell) for cell in row)]
                rows = [header] + data if data else []
            nxt["rows"] = rows
        if isinstance(nxt.get("cards"), list):
            cards = []
            for card in nxt["cards"]:
                if not isinstance(card, dict):
                    continue
                nxt_card = dict(card)
                for key in ("title", "body", "kicker"):
                    if isinstance(nxt_card.get(key), str):
                        nxt_card[key] = _scrub_bound(
                            str(nxt_card[key]),
                            global_ok,
                            bindings,
                            grid=grid,
                            message_ok=message_ok,
                        ).strip()
                if str(nxt_card.get("title") or "").strip():
                    cards.append(nxt_card)
            nxt["cards"] = cards
        if isinstance(nxt.get("kpis"), list):
            kept = []
            for kpi in nxt["kpis"]:
                if not isinstance(kpi, dict):
                    continue
                label = str(kpi.get("label") or "")
                value = str(kpi.get("value") or "")
                clause = f"{label} {value}"
                norms = {_norm_num(token) for token in _NUM.findall(value)}
                if norms and not all(
                    _clause_allows(clause, norm, global_ok, bindings, grid, message_ok)
                    for norm in norms
                ):
                    continue
                kept.append(kpi)
            nxt["kpis"] = kept
        slides.append(nxt)
    out = dict(deck)
    out["slides"] = slides
    return _repass_blank_slides(out)


def _has_letters(value: object) -> bool:
    return bool(re.search(r"[0-9A-Za-zА-Яа-яЁё]", str(value or "")))


def _slide_still_visible(slide: dict[str, Any]) -> bool:
    if str(slide.get("media_id") or slide.get("chart_id") or "").strip():
        return True
    for key in (
        "title",
        "subtitle",
        "caption",
        "body",
        "kicker",
        "takeaway",
        "term",
        "definition",
    ):
        if _has_letters(slide.get(key)):
            return True
    for item in slide.get("bullets") or []:
        if _has_letters(item):
            return True
    for card in slide.get("cards") or []:
        if isinstance(card, dict) and any(
            _has_letters(card.get(key)) for key in ("title", "body", "kicker")
        ):
            return True
    for kpi in slide.get("kpis") or []:
        if isinstance(kpi, dict) and str(kpi.get("value") or "").strip():
            return True
    for row in slide.get("rows") or []:
        if isinstance(row, list) and any(str(cell).strip() and str(cell).strip() != "—" for cell in row):
            return True
    return False


def _repass_blank_slides(deck: dict[str, Any]) -> dict[str, Any]:
    """Drop a slide the number pass wiped. Never leave the deck empty."""
    kept = [
        slide
        for slide in deck.get("slides") or []
        if isinstance(slide, dict) and _slide_still_visible(slide)
    ]
    if not kept:
        kept = [{"id": "s01", "layout": "title", "title": "Итоги"}]
    out = dict(deck)
    out["slides"] = kept
    return out
