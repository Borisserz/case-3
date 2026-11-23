"""Numbers in a new report or deck. Memory is not a source of them."""

from __future__ import annotations

import re
from typing import Any

from case3.chart_number import compact_chart_number_text, take_chart_number
from case3.chat_turn import _NUM, _norm_num, latest_user_line, number_norms, stray_numbers

_PROTECT = re.compile(
    r"\\includegraphics\s*(?:\[[^\]]*\])?\{[^}]*\}"
    r"|\\begin\{(?P<tbl>tabularx?\*?|xltabular|tabular\*?)\}[\s\S]*?\\end\{(?P=tbl)\}"
    r"|\\(?:begin|end)\{[^}]*\}(?:\s*\[[^\]]*\])?"
    r"|\\(?:label|ref|pageref|autoref|eqref|cite\w*)\{[^}]*\}"
    r"|(?<!\\)%[^\n]*"
    r"|\\(?:vspace|hspace|setlength|fontsize|rule)\{[^}]*\}(?:\{[^}]*\})?"
    r"|\\(?:multicolumn|multirow)\{[^}]*\}\{[^}]*\}"
    r"|\\(?:cmidrule|cline|hhline)\{[^}]*\}"
    r"|\\(?:rowcolor|cellcolor|color)\{[^}]*\}"
    r"|\\(?:href|url)\{[^}]*\}"
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
        rf"({_NUM.pattern})(?:\s+([0-9A-Za-zА-Яа-яЁё]{{3,}}))?",
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
        self.aggregates: set[str] = set()
        self.all_row_norms: set[str] = set()
        self.phrase_norms: list[tuple[re.Pattern[str], set[str]]] = []

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
        expanded = set(clean)
        for n in clean:
            if n.startswith("-") and len(n) > 1:
                expanded.add(n[1:])
        self.all_row_norms.update(expanded)
        if col:
            bucket.setdefault((row, col), set()).update(expanded)
            self.columns.add(col)
        else:
            bucket.setdefault((row, ""), set()).update(expanded)
        if bucket is self.values:
            self.rows.setdefault(row, set()).update(expanded)


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
_FP_DERIV_LINE = re.compile(
    r"^[-*]\s+(.+?):\s+откл\.\s+([+\-−]?[\d \u00a0.,]+)(?:,\s*вып\.\s+([\d \u00a0.,]+%))?\s*$"
)


def _label_key(label: str) -> str:
    return " ".join(
        re.findall(r"[0-9a-zа-я]+", (label or "").casefold().replace("ё", "е"))
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
    """One cell stays on its row and its column. Shared group words stay excluded."""
    from case3.dashboard_source import _label_column, _markdown_tables

    grid = TableGrid()
    row_entries: list[tuple[str, str, set[str], dict[str, set[str]]]] = []
    stem_labels: dict[str, set[str]] = {}
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
            stems = _name_stems(label)
            lkey = _label_key(label)
            if lkey:
                for stem in stems:
                    stem_labels.setdefault(stem, set()).add(lkey)
            row_entries.append((label, lkey, stems, cells))

    phrase_map: dict[str, tuple[str, set[str]]] = {}
    for raw_label, lkey, stems, cells in row_entries:
        unique = {stem for stem in stems if len(stem_labels.get(stem, set())) == 1}
        keys = unique or stems
        row_all_norms: set[str] = set()
        for norms in cells.values():
            row_all_norms.update(norms)
            for n in list(norms):
                if n.startswith("-") and len(n) > 1:
                    row_all_norms.add(n[1:])
        for key in keys:
            for col, norms in cells.items():
                grid.add(grid.values, key, col, norms)
        if lkey and row_all_norms and len(stem_labels) > 0 and not unique and stems:
            prev_raw, prev_norms = phrase_map.get(lkey, (raw_label, set()))
            phrase_map[lkey] = (prev_raw, prev_norms | row_all_norms)
    for lkey, (raw_label, pnorms) in phrase_map.items():
        tokens = lkey.split()
        if len(tokens) >= 2:
            pat = re.compile(
                r"\b" + r"\s+".join(re.escape(t) for t in tokens) + r"\w*",
                re.IGNORECASE,
            )
            grid.phrase_norms.append((pat, pnorms))
    _add_derivatives(grid, source or "")
    return grid


def _add_derivatives(grid: TableGrid, source: str) -> None:
    column = ""
    for raw in (source or "").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith("#"):
            continue
        match = _DERIV_LINE.match(stripped)
        if match:
            label, share, rank = match.group(1), match.group(2), match.group(3)
            named = _name_stems(column)
            col = max(named, key=len) if named else ""
            for stem in _name_stems(label):
                if stem not in grid.rows:
                    continue
                grid.add(grid.shares, stem, col, number_norms(share))
                grid.add(grid.ranks, stem, col, number_norms(rank))
            continue
        fp_match = _FP_DERIV_LINE.match(stripped)
        if fp_match:
            label, diff = fp_match.group(1), fp_match.group(2)
            pct = fp_match.group(3) or ""
            for stem in _name_stems(label):
                if stem not in grid.rows:
                    continue
                grid.add(grid.values, stem, "", number_norms(diff))
                if pct:
                    grid.add(grid.values, stem, "", number_norms(pct))
                    grid.add(grid.shares, stem, "", number_norms(pct))
            continue
        if "Доли и места" in stripped:
            continue
        if stripped.startswith(
            (
                "Сумма по строкам:",
                "Среднее:",
                "По «",
                "Сводно:",
                "Отклонение и выполнение",
                "- По «",
                "Выше плана",
            )
        ):
            agg_part = stripped.split("; макс:", 1)[0].split("; мин:", 1)[0]
            grid.aggregates.update(number_norms(agg_part))
            continue
        if stripped.startswith(("Топ-5", "Отстающие")):
            continue
        column = stripped


def _mentions_share(clause: str) -> bool:
    folded = (clause or "").casefold().replace("ё", "е")
    return "%" in (clause or "") or bool(re.search(r"\bдол[яеиюйь]", folded))


def _mentions_rank(clause: str) -> bool:
    folded = (clause or "").casefold().replace("ё", "е")
    return bool(re.search(r"\bмест[оаеу]?\b", folded))


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
    buckets = [grid.values]
    if share:
        buckets.append(grid.shares)
    if rank:
        buckets.append(grid.ranks)
    allowed: set[str] = set()
    # Any value cell on this row is valid even if prose casually names another column («перевыполнила план: 102,3%»).
    for (key, _col), norms in grid.values.items():
        if key == row:
            allowed |= norms
    for bucket in buckets[1:]:
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
    if norm in grid.aggregates:
        return True
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
    if len(rows) == 1 and grid.phrase_norms:
        folded_clause = (clause or "").casefold().replace("ё", "е")
        for pat, pnorms in grid.phrase_norms:
            if pat.search(folded_clause):
                row_norms = _norms_on_row(grid, rows[0], clause, columns)
                # Keep share/rank from _norms_on_row while scoping values to matched phrase.
                scoped = set(pnorms)
                for bucket in (grid.shares, grid.ranks):
                    for (k, _c), ns in bucket.items():
                        if k == rows[0]:
                            scoped |= ns
                return _has_norm(scoped & row_norms or pnorms, norm)
    return _has_norm(_norms_on_row(grid, rows[0], clause, columns), norm)


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


_SMALL_COUNT_CLAUSE = re.compile(
    r"(?:\bтоп[-\s]?(\d{1,2})\b|\b(\d{1,2})\s+(?:регион\w*|област\w*|район\w*|инспекц\w*|позиц\w*|строк\w*|категор\w*|город\w*|лидер\w*|аутсайдер\w*))",
    re.IGNORECASE,
)


def _has_norm(pool: set[str], norm: str) -> bool:
    return bool(norm) and (
        norm in pool or (not norm.startswith("-") and f"-{norm}" in pool)
    )


def _is_small_cardinal_in_clause(clause: str, norm: str) -> bool:
    if not norm.isdigit():
        return False
    val = int(norm)
    if not (1 <= val <= 50):
        return False
    for m in _SMALL_COUNT_CLAUSE.finditer(clause or ""):
        hit = m.group(1) or m.group(2)
        if hit and int(hit) == val:
            return True
    return False


def _verifies_math(
    clause: str,
    norm: str,
    allowed_pool: set[str],
    extra_operands: set[str] | None = None,
) -> bool:
    """Allow arithmetic outputs derived directly from grounded operands."""
    from decimal import Decimal, InvalidOperation

    try:
        target = Decimal(norm)
    except InvalidOperation:
        return False
    clause_operands: list[Decimal] = []
    seen_op: set[str] = set()
    for match in _NUM.finditer(clause or ""):
        cand = _norm_num(match.group(0))
        if not cand or cand == norm or cand in seen_op:
            continue
        if _has_norm(allowed_pool, cand) or (extra_operands and cand in extra_operands):
            try:
                clause_operands.append(Decimal(cand))
                seen_op.add(cand)
            except InvalidOperation:
                continue
    pool_operands: list[Decimal] = list(clause_operands)
    for src_set in (extra_operands or set(),):
        for cand in src_set:
            if cand == norm or cand in seen_op:
                continue
            try:
                pool_operands.append(Decimal(cand))
                seen_op.add(cand)
            except InvalidOperation:
                continue
    if not pool_operands:
        return False

    tol = max(Decimal("0.15"), abs(target) * Decimal("0.005"))

    # 1. Unit scaling (thousands <-> millions)
    for val in pool_operands:
        if val == 0:
            continue
        for factor in (Decimal("1000"), Decimal("0.001"), Decimal("1000000"), Decimal("0.000001")):
            if abs(val * factor - target) <= tol:
                return True

    # 2. Multi-addend sum from grounded operands present in the sentence/clause
    if len(clause_operands) >= 2:
        total = sum(clause_operands, Decimal(0))
        if abs(total - target) <= tol:
            return True

    if extra_operands and len(pool_operands) >= 2:
        # Pairwise combinations among grounded operands in sentence + extra (row / message)
        for i in range(len(pool_operands)):
            a = pool_operands[i]
            for j in range(i + 1, len(pool_operands)):
                b = pool_operands[j]
                cands = [a + b, a - b, b - a, abs(a - b)]
                if b != 0:
                    cands.extend([a * Decimal(100) / b, (a - b) * Decimal(100) / b])
                if a != 0:
                    cands.extend([b * Decimal(100) / a, (b - a) * Decimal(100) / a])
                for calc in cands:
                    if abs(calc - target) <= tol:
                        return True
    elif len(clause_operands) >= 2:
        for i in range(len(clause_operands)):
            a = clause_operands[i]
            for j in range(i + 1, len(clause_operands)):
                b = clause_operands[j]
                cands = [a + b, a - b, b - a, abs(a - b)]
                if b != 0:
                    cands.extend([a * Decimal(100) / b, (a - b) * Decimal(100) / b])
                if a != 0:
                    cands.extend([b * Decimal(100) / a, (b - a) * Decimal(100) / a])
                for calc in cands:
                    if abs(calc - target) <= tol:
                        return True
    return False


def _clause_allows(
    clause: str,
    norm: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    grid: TableGrid | None = None,
    message_ok: set[str] | None = None,
    extra_math_operands: set[str] | None = None,
) -> bool:
    if message_ok and _has_norm(message_ok, norm):
        return True
    if _is_small_cardinal_in_clause(clause, norm):
        return True
    metadata_ok = (
        (global_ok - grid.all_row_norms) | grid.aggregates
        if grid is not None and grid.rows
        else set()
    )
    if metadata_ok and _has_norm(metadata_ok, norm):
        return True
    on_row = _row_allows(clause, norm, grid)
    if on_row is not None:
        if on_row:
            return True
    elif _has_norm(global_ok, norm):
        return True
    from case3.chat_memory import _stem_set

    stems = _stem_set(clause)
    if any(bound == norm and stem and stem in stems for bound, stem in bindings):
        return True
    math_pool = set(global_ok) | (set(message_ok) if message_ok else set())
    row_pool: set[str] = set(extra_math_operands or set())
    if grid is not None and grid.rows:
        mentions = _row_mentions(clause, grid)
        for _s, _e, rstem in mentions:
            row_pool |= grid.rows.get(rstem, set())
    if message_ok:
        row_pool |= set(message_ok)
    if _verifies_math(clause, norm, math_pool, row_pool):
        return True
    return False


def _split_commas(chunk: str) -> list[str]:
    """Split on top-level commas outside TeX {...} groups and not inside decimals."""
    parts: list[str] = []
    start = 0
    depth = 0
    size = len(chunk)
    i = 0
    while i < size:
        ch = chunk[i]
        if ch == "\\" and i + 1 < size:
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
        elif ch == "," and depth == 0:
            after = chunk[i + 1 : i + 2]
            if not after.isdigit():
                parts.append(chunk[start:i])
                j = i + 1
                while j < size and chunk[j].isspace():
                    j += 1
                start = j
                i = j
                continue
        i += 1
    parts.append(chunk[start:])
    return parts


def _balance_braces(text: str) -> str:
    """Close any unclosed TeX braces or drop unmatched closing braces."""
    out: list[str] = []
    depth = 0
    i = 0
    size = len(text)
    while i < size:
        ch = text[i]
        if ch == "\\" and i + 1 < size:
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch == "{":
            depth += 1
            out.append(ch)
        elif ch == "}":
            if depth > 0:
                depth -= 1
                out.append(ch)
        else:
            out.append(ch)
        i += 1
    if depth > 0:
        out.append("}" * depth)
    return "".join(out)


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

    raw_text = text or ""
    if not raw_text:
        return ""
    if not raw_text.strip():
        return raw_text
    lead_len = len(raw_text) - len(raw_text.lstrip())
    lead = raw_text[:lead_len]
    trail_start = len(raw_text.rstrip())
    trail = raw_text[trail_start:]
    core = raw_text[lead_len:trail_start]

    def spoken_norm(token: str) -> str:
        stem = token.casefold().replace("ё", "е")
        for prefix, digit in _SPOKEN_NUMBER:
            if stem.startswith(prefix):
                return digit
        return ""

    def clean_clause(clause: str, sentence_ok: set[str]) -> tuple[str, set[str]]:
        digits = [_norm_num(match.group(0)) for match in _NUM.finditer(clause)]
        words = [(match.group(0), spoken_norm(match.group(0))) for match in _SPOKEN_RE.finditer(clause)]
        norms = [norm for norm in digits + [digit for _word, digit in words] if norm]
        if not norms:
            return clause, set()
        judged = f"{context} {clause}".strip() if context else clause
        extra = set(sentence_ok)
        if message_ok:
            extra |= message_ok
        kept_here: set[str] = set()
        bad: set[str] = set()
        for norm in norms:
            if _clause_allows(
                judged,
                norm,
                global_ok,
                bindings,
                grid,
                message_ok,
                extra,
            ):
                kept_here.add(norm)
                extra.add(norm)
            else:
                bad.add(norm)
        if not bad:
            return clause, kept_here
        # One illegal number ruins the clause. Cutting it out leaves «в раза».
        return "", set()

    kept_lines: list[str] = []
    for line in core.split("\n"):
        if not line.strip():
            if kept_lines and kept_lines[-1] != "":
                kept_lines.append("")
            continue
        bits = re.split(r"([.!?]+(?:\s+|$))", line)
        kept: list[str] = []
        index = 0
        while index < len(bits):
            chunk = bits[index]
            delim = bits[index + 1] if index + 1 < len(bits) else ""
            index += 2 if delim else 1
            parts = []
            cut = False
            sentence_ok: set[str] = set()
            for part in _split_commas(chunk):
                raw = part.strip()
                cleaned_raw, part_norms = clean_clause(part, sentence_ok)
                cleaned = cleaned_raw.strip()
                if not cleaned or re.fullmatch(r"[\s,.;:–—\-]+", cleaned):
                    if raw and (_NUM.search(raw) or _SPOKEN_RE.search(raw)):
                        cut = True
                    continue
                sentence_ok.update(part_norms)
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
            kept_lines.append(_balance_braces("".join(kept).strip()))
    while kept_lines and kept_lines[-1] == "":
        kept_lines.pop()
    result = "\n".join(kept_lines)
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r" +([,.;:!?])", r"\1", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    if not result:
        return ""
    return f"{lead}{result}{trail}"


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
    """A caption or tooltip. HTML dimensions, hex colors, and CSS '%'-options are not facts."""
    if re.search(r"[А-Яа-яЁё]", inner or ""):
        return True
    if re.search(r"тыс|млн|млрд|чел|°", inner or "", re.IGNORECASE):
        return True
    return False


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
        for key in ("title", "caption"):
            if isinstance(item.get(key), str):
                item[key] = _scrub_bound(
                    item[key], global_ok, bindings, grid=grid, message_ok=message_ok
                )
        if isinstance(item.get("mermaid"), str):
            item["mermaid"] = _scrub_mermaid(
                item["mermaid"], global_ok, bindings, grid=grid, message_ok=message_ok
            )
    return tex, charts, figures, diagrams, dropped


_MERMAID_DIRECTIVE = re.compile(
    r"^\s*(?:%%|flowchart\b|graph\b|sequenceDiagram\b|classDiagram\b|stateDiagram(?:-v2)?\b|"
    r"erDiagram\b|classDef\b|class\b|style\b|linkStyle\b|click\b|direction\b|subgraph\b|end\b)",
    re.IGNORECASE,
)


def _scrub_mermaid(
    mermaid: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    *,
    grid: TableGrid | None = None,
    message_ok: set[str] | None = None,
) -> str:
    """Drop stray numbers in node/edge labels without mangling Mermaid directives or edges."""
    out_lines: list[str] = []
    for line in (mermaid or "").splitlines():
        if _MERMAID_DIRECTIVE.match(line):
            out_lines.append(line)
            continue

        def _clean_match(match: re.Match[str]) -> str:
            norm = _norm_num(match.group(0))
            if not norm or _clause_allows(
                line, norm, global_ok, bindings, grid, message_ok
            ):
                return match.group(0)
            return ""

        cleaned = _NUM.sub(_clean_match, line)
        cleaned = re.sub(r" {2,}", " ", cleaned)
        cleaned = re.sub(r" +([\]\)\"\|])", r"\1", cleaned)
        out_lines.append(cleaned)
    return "\n".join(out_lines)


def _kicker_chrome(value: object) -> bool:
    return bool(re.fullmatch(r"\d{1,2}(?:/\d{1,2})?", str(value or "").strip()))


def _scrub_html_bound(
    html: str,
    global_ok: set[str],
    bindings: list[tuple[str, str]],
    grid: TableGrid | None = None,
    message_ok: set[str] | None = None,
) -> str:
    """Chart data takes only Source, this message, and matching user bindings.

    A caption may use a bound word. A month label is not a table row, so its
    point stays when the number itself is in Source.
    """
    from case3.chat_memory import _stem_set

    labels = _chart_labels(html)
    html_stems = _stem_set(html)

    def _bound_allows(norm: str, slot: int | None = None) -> bool:
        if not bindings:
            return False
        slot_stems = _stem_set(labels[slot]) if slot is not None and 0 <= slot < len(labels) else set()
        for b_norm, stem in bindings:
            if b_norm != norm:
                continue
            if not stem or stem in slot_stems or stem in html_stems:
                return True
        return False

    def token_reject(token: str) -> bool:
        norm = _norm_num(token)
        if not norm:
            return False
        if _has_norm(global_ok, norm) or (message_ok and _has_norm(message_ok, norm)):
            return False
        return not _bound_allows(norm)

    def slot_reject(token: str, slot: int) -> bool:
        norm = _norm_num(token)
        if message_ok and _has_norm(message_ok, norm):
            return False
        if _bound_allows(norm, slot):
            return False
        if slot >= len(labels):
            return False
        allowed = _row_norms_for_label(labels[slot], grid)
        if allowed is None:
            return False
        return not _has_norm(allowed, norm)

    def repl(match: re.Match[str]) -> str:
        kind = match.group(1)
        return _rewrite_chart_body(
            kind,
            match.group(2),
            token_reject,
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
                if key == "kicker" and _kicker_chrome(nxt[key]):
                    continue
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
            raw_rows = [row for row in nxt["rows"] if isinstance(row, list)]
            had_digits = [
                any(bool(_NUM.search(str(cell))) for cell in row) for row in raw_rows
            ]
            rows: list[list[str]] = []
            row_digits: list[bool] = []
            for row, row_has_digit in zip(raw_rows, had_digits):
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
                    row_digits.append(row_has_digit)
            if rows:
                header, data = rows[0], rows[1:]
                data_had = row_digits[1:]
                kept_data = [
                    row
                    for row, had in zip(data, data_had)
                    if not had or any(bool(_NUM.search(cell)) for cell in row)
                ]
                rows = [header] + kept_data if kept_data else []
            nxt["rows"] = rows
        if isinstance(nxt.get("cards"), list):
            cards = []
            for card in nxt["cards"]:
                if not isinstance(card, dict):
                    continue
                nxt_card = dict(card)
                for key in ("title", "body", "kicker"):
                    if isinstance(nxt_card.get(key), str):
                        if key == "kicker" and _kicker_chrome(nxt_card[key]):
                            continue
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
                nxt_kpi = dict(kpi)
                label = str(nxt_kpi.get("label") or "")
                value = str(nxt_kpi.get("value") or "")
                clause = f"{label} {value}"
                norms = {_norm_num(token) for token in _NUM.findall(value)}
                if norms and not all(
                    _clause_allows(clause, norm, global_ok, bindings, grid, message_ok)
                    for norm in norms
                ):
                    continue
                for extra_key in ("delta", "hint"):
                    if isinstance(nxt_kpi.get(extra_key), str):
                        nxt_kpi[extra_key] = _scrub_bound(
                            nxt_kpi[extra_key],
                            global_ok,
                            bindings,
                            context=label,
                            grid=grid,
                            message_ok=message_ok,
                        ).strip()
                kept.append(nxt_kpi)
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
