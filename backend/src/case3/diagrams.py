"""Sanitize / parse Mermaid diagrams (Liber UI-only; never TeX-injected)."""

from __future__ import annotations

from case3.color_util import hex_to_rgb

import logging
import os
import re
from typing import Any, Literal, overload

log = logging.getLogger("case3.diagrams")


# Product ceiling for Mermaid Liber UI schemas (API + Settings max).
# Tuned via CASE3_MAX_DIAGRAMS (default 5); code never allows above this constant.
DIAGRAMS_HARD_MAX = 5


def max_diagrams_from_env() -> int:
    """CASE3_MAX_DIAGRAMS — sole diagrams budget/ceiling; default 5; clamp 0–5."""
    raw = (os.environ.get("CASE3_MAX_DIAGRAMS") or "5").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 5
    return max(0, min(n, DIAGRAMS_HARD_MAX))


def clamp_diagram_budget(value: int | None) -> int:
    """Per-request diagram ceiling. None follows the env default. Never a hidden 3."""
    if value is None:
        return max_diagrams_from_env()
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 0
    return max(0, min(n, DIAGRAMS_HARD_MAX))


DIAGRAM_TYPES = frozenset(
    {"flowchart", "sequence", "mindmap", "timeline", "stateDiagram"}
)

# First-line keywords allowed for each diagrams[].type (after normalize).
_TYPE_HEADERS: dict[str, frozenset[str]] = {
    "flowchart": frozenset({"flowchart", "graph"}),
    "sequence": frozenset({"sequencediagram", "sequence"}),
    "mindmap": frozenset({"mindmap"}),
    "timeline": frozenset({"timeline"}),
    "stateDiagram": frozenset({"statediagram-v2", "statediagram", "state"}),
}

_ID_OK = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_FENCE = re.compile(r"^```(?:mermaid)?\s*\n([\s\S]*?)\n?```\s*$", re.I)
_MAX_BODY = 6000
_MAX_TITLE = 80
_FIRST_TOKEN = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)")
_HEX_COLOR = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_CLICK_LINE = re.compile(r"(?im)^\s*click\s+.*$")
# LLM writes ``Node]::role`` (two colons). Mermaid class suffix is ``:::role``.
_SHORT_ROLE_SUFFIX = re.compile(r"(?<=[\]\)\}>])::(?!:)(?=[A-Za-z])")
# `class A,B foo` is valid; `class A,B foo bar baz` (N names) is not — LLM leak.
# Also catches space-separated nodes: `class A B C process`.
_CLASS_ASSIGN_LINE = re.compile(
    r"(?im)^([ \t]*)class(?!Def\b)[ \t]+(.+?)\s*$"
)
# LLM writes style on `class` instead of `classDef`: `class start fill:#abc,...`
_CLASS_AS_CLASSDEF = re.compile(
    r"(?im)^([ \t]*)class(?!Def\b)[ \t]+([A-Za-z][\w-]*)[ \t]+(fill\s*:.*)$"
)
# Spaces inside edge labels: `B -- |Да| C` → `B -->|Да| C`.
_EDGE_LABEL_SPACES = re.compile(r"([-=.~]{2,})\s+\|([^|]+)\|\s+")

# Sequence diagram alias repair (LLM emits `Actor as Label` missing participant keyword)
_SEQ_KEYWORDS = re.compile(
    r"^(participant|actor|note|box|create|destroy|activate|deactivate|rect|loop|alt|opt|par|critical|break|end|autonumber|links?|title|accTitle|accDescr)\b",
    re.I,
)
_SEQ_ARROW = re.compile(r"->|-->|->>|-->>|-x|--x|-\)|--\)")
_SEQ_KEYWORD_AS = re.compile(
    r"^([ \t]*)(participant|actor)\s+(.+?)\s+as\s+(.+)$", re.I
)
_AS_LINE = re.compile(r"^([ \t]*)(.+?\s+as\s+.+)$", re.I)
# Flowchart with nodes but no edges: dagre puts them on one rank (a row for TD)
# and draws no lines. Models do this when they emit classDefs and forget `-->`.
_FLOW_HEADER = re.compile(r"(?im)^\s*flowchart\b")
_FLOW_EDGE = re.compile(r"-->|---|-\.->|==>|~~~|--o|o--|--x")
_FLOW_NODE = re.compile(r"^\s*([A-Za-z][\w-]*)\s*(?:@\{|\[|\(|\{|>|/)")
_FLOW_SKIP_IDS = frozenset(
    {
        "flowchart",
        "subgraph",
        "graph",
        "end",
        "class",
        "classdef",
        "style",
        "direction",
        "linkstyle",
        "click",
    }
)

# Liber soft-premium fallbacks (atelier) — never purple neon.
_SAFE_FILL = "#dce8df"
_SAFE_STROKE = "#6b8f76"


class DiagramError(ValueError):
    """Invalid Mermaid diagram payload."""


def _is_purple_hex(hex_color: str) -> bool:
    """Reject purple / violet neon (product: no нейрослоп)."""
    rgb = hex_to_rgb(hex_color)
    if rgb is None:
        return True
    r, g, b = rgb
    # High R+B with suppressed G → purple/magenta family.
    if b >= 110 and r >= 90 and g <= min(r, b) * 0.78 and ((r + b) / 2 - g) >= 36:
        return True
    # Saturated violet: B dominant, R mid, G low.
    if b > r >= g and (b - g) >= 70 and r >= 60:
        return True
    return False


def _rewrite_unsafe_colors(mermaid: str) -> str:
    """Swap purple fills/strokes in style/classDef to Liber sage."""

    def repl(m: re.Match[str]) -> str:
        full = m.group(0)
        if not _is_purple_hex(full):
            return full
        before = mermaid[max(0, m.start() - 16) : m.start()].lower()
        return _SAFE_STROKE if "stroke" in before else _SAFE_FILL

    return _HEX_COLOR.sub(repl, mermaid)


def _repair_class_assign_lines(mermaid: str) -> str:
    """Fix LLM class / classDef leaks.

    - ``class start fill:#…`` → ``classDef start fill:#…``
    - ``class A,B,C start decision process`` → one class per node (zip)
    - ``class A B C process`` (space-separated nodes, one class) → ``class A,B,C process``
    """
    out: list[str] = []
    for line in (mermaid or "").splitlines():
        as_def = _CLASS_AS_CLASSDEF.match(line)
        if as_def:
            indent, name, style = as_def.group(1), as_def.group(2), as_def.group(3).strip()
            out.append(f"{indent}classDef {name} {style}")
            continue
        m = _CLASS_ASSIGN_LINE.match(line)
        if not m:
            out.append(line)
            continue
        indent, rest = m.group(1), m.group(2).strip()
        tokens = [t.lstrip(":") for t in rest.split()]
        if len(tokens) < 2:
            out.append(line)
            continue
        # Comma-joined first token(s): `A,B,C start decision process`
        if "," in tokens[0]:
            nodes = [n.strip() for n in tokens[0].split(",") if n.strip()]
            names = tokens[1:]
            if len(names) <= 1:
                # `class A,B,C process` — valid Mermaid (one class, many nodes)
                out.append(f"{indent}class {','.join(nodes)} {names[0]}")
                continue
            if len(names) == len(nodes) and all(
                re.match(r"^[A-Za-z][\w-]*$", n) for n in names
            ):
                for node, cls in zip(nodes, names):
                    out.append(f"{indent}class {node} {cls}")
                continue
            log.warning(
                "dropped invalid mermaid class line (%d nodes / %d names): %s",
                len(nodes),
                len(names),
                line.strip()[:120],
            )
            continue
        # Space-separated: `class A B C process` or `class A start`
        if len(tokens) == 2 and re.match(r"^[A-Za-z][\w-]*$", tokens[0]) and re.match(r"^[A-Za-z][\w-]*$", tokens[1]):
            out.append(f"{indent}class {tokens[0]} {tokens[1]}")
            continue
        if len(tokens) >= 3 and all(
            re.match(r"^[A-Za-z][\w-]*$", t) for t in tokens
        ):
            nodes, cls = tokens[:-1], tokens[-1]
            out.append(f"{indent}class {','.join(nodes)} {cls}")
            continue
        log.warning(
            "dropped invalid mermaid class line: %s",
            line.strip()[:120],
        )
    return "\n".join(out)


def _normalize_edge_label_spaces(mermaid: str) -> str:
    """``B -- |Да| C`` → ``B -->|Да| C`` (tolerant of LLM spacing)."""
    return _EDGE_LABEL_SPACES.sub(r"\1|\2| ", mermaid or "")


def _repair_sequence_diagram_lines(mermaid: str) -> str:
    """Prepends ``participant `` to ``Alias as Label`` lines and quotes multi-word IDs."""
    lines = (mermaid or "").splitlines()
    if not any(re.match(r"^\s*sequenceDiagram\b", l, re.I) for l in lines):
        return mermaid
    out: list[str] = []
    for line in lines:
        trimmed = line.strip()
        if (
            not trimmed
            or trimmed.startswith("%%")
            or _SEQ_ARROW.search(trimmed)
        ):
            out.append(line)
            continue
        kw_m = _SEQ_KEYWORD_AS.match(line)
        if kw_m:
            indent, kw, ident, alias = kw_m.group(1), kw_m.group(2), kw_m.group(3).strip(), kw_m.group(4).strip()
            if " " in ident and not (ident.startswith('"') and ident.endswith('"')):
                ident = f'"{ident}"'
            out.append(f"{indent}{kw} {ident} as {alias}")
            continue
        if _SEQ_KEYWORDS.match(trimmed):
            out.append(line)
            continue
        m = _AS_LINE.match(line)
        if m:
            indent, rest = m.group(1), m.group(2).strip()
            parts = re.split(r"\s+as\s+", rest, maxsplit=1, flags=re.I)
            if len(parts) == 2:
                ident, alias = parts[0].strip(), parts[1].strip()
                if " " in ident and not (ident.startswith('"') and ident.endswith('"')):
                    ident = f'"{ident}"'
                out.append(f"{indent}participant {ident} as {alias}")
            else:
                out.append(f"{indent}participant {rest}")
        else:
            out.append(line)
    return "\n".join(out)


_FLOW_HDR = re.compile(r"^\s*(?:flowchart|graph|mindmap)\b", re.IGNORECASE)
_META_LINE = re.compile(
    r"^\s*(?:%%|classDef\b|class\s|style\s|linkStyle\b|subgraph\b|end\b|direction\b|click\b)",
    re.IGNORECASE,
)
# Longest pair first so `((` is a circle, not two rounded nodes.
_SHAPE_PAIRS = (
    ("((", "))"),
    ("[[", "]]"),
    ("{{", "}}"),
    ("([", "])"),
    ("[(", ")]"),
    ("[/", "/]"),
    ("[\\", "\\]"),
    ("[", "]"),
    ("{", "}"),
    ("(", ")"),
)
_LABEL_SPECIAL = ('(', ')', ':', '"', '%')
# A real next node (`B[Конец]`) or an edge. Cyrillic prose after `]` is a broken label.
_NEXT_NODE = re.compile(r"^[A-Za-z_][\w-]*\s*[\[\(\{]")
_EDGE_PREFIX = re.compile(r"^(?:-->|---|==>|-\.->|==|~~~|-\.-|--|:::|&|\|)")
_EDGE_IN_TAIL = re.compile(r"\s(?:-->|---|==>|-\.->|:::|&)\s")
_NEXT_SHAPE = re.compile(
    r"\s+[A-Za-z_][\w-]*\s*(?:\(\(|\[\[|\{\{|\(\[|\[\(|\[|\{|\()"
)


def _shape_pair(line: str, i: int) -> tuple[str, str] | None:
    for open_d, close_d in _SHAPE_PAIRS:
        if line.startswith(open_d, i):
            return open_d, close_d
    return None


def _circle_close(line: str, content_start: int) -> int:
    """Last ``))`` before the next node or edge.

    ``((текст (2025)))`` ends with three parens. The first ``))`` is the
    label's ``)`` plus one closer, so a depth scan cuts the year off.
    """
    limit = len(line)
    edge = _EDGE_IN_TAIL.search(line, content_start)
    if edge:
        limit = edge.start()
    nxt = _NEXT_SHAPE.search(line, content_start)
    if nxt and nxt.start() < limit:
        limit = nxt.start()
    return line.rfind("))", content_start, limit)


def _close_at(line: str, start: int, open_d: str, close_d: str) -> int:
    """Index of the matching close token, or -1."""
    depth = 1
    i = start
    n = len(line)
    ol, cl = len(open_d), len(close_d)
    while i < n:
        if line.startswith(open_d, i):
            depth += 1
            i += ol
            continue
        if line.startswith(close_d, i):
            depth -= 1
            if depth == 0:
                return i
            i += cl
            continue
        i += 1
    return -1


def _stray_label_tail(rest: str) -> tuple[str, int] | None:
    """Prose after a closed node that Mermaid reads as a new shape.

    ``A[январь 2025)] Консолидированный --> B`` returns the stray words and
    the offset where `` --> B`` begins. A following ``B[Конец]`` or ``-->``
    is left alone.
    """
    stripped = rest.lstrip()
    if not stripped:
        return None
    if _EDGE_PREFIX.match(stripped) or _NEXT_NODE.match(stripped):
        return None
    edge = _EDGE_IN_TAIL.search(rest)
    if edge:
        extra = rest[: edge.start()].strip()
        if not extra:
            return None
        return extra, edge.start()
    extra = rest.strip()
    if not extra:
        return None
    return extra, len(rest)


def _quote_flowchart_nodes(mermaid: str) -> str:
    """Quote flowchart and mindmap labels that contain ``() : " %``.

    Words left after the closing bracket (``2025)] Консолидированный``) are
    pulled back into the label. Otherwise Mermaid closes the node at the
    first ``)`` / ``]`` and the next ``(`` fails with NODE_DSTART.
    """
    lines = (mermaid or "").splitlines()
    first = ""
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("%%") and not s.startswith("---"):
            first = s
            break
    if not _FLOW_HDR.match(first):
        return mermaid
    out_lines: list[str] = []
    for line in lines:
        if _META_LINE.match(line) or _FLOW_HDR.match(line):
            out_lines.append(line)
            continue
        buf: list[str] = []
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            # Preserve quoted strings & edge labels |...| outside a node.
            if ch == '"':
                end = line.find('"', i + 1)
                if end < 0:
                    buf.append(line[i:])
                    break
                buf.append(line[i : end + 1])
                i = end + 1
                continue
            if ch == "|":
                end = line.find("|", i + 1)
                if end < 0:
                    buf.append(line[i:])
                    break
                buf.append(line[i : end + 1])
                i = end + 1
                continue
            pair = (
                _shape_pair(line, i)
                if i > 0 and (line[i - 1].isalnum() or line[i - 1] in "_-")
                else None
            )
            if pair:
                open_d, close_d = pair
                content_start = i + len(open_d)
                close_at = (
                    _circle_close(line, content_start)
                    if open_d == "(("
                    else _close_at(line, content_start, open_d, close_d)
                )
                if close_at < 0:
                    buf.append(ch)
                    i += 1
                    continue
                shape_end = close_at + len(close_d)
                inner = line[i + len(open_d) : close_at]
                stripped = inner.strip()
                already = (
                    len(stripped) >= 2
                    and stripped.startswith('"')
                    and stripped.endswith('"')
                )
                tail = _stray_label_tail(line[shape_end:])
                extra = ""
                extra_end = 0
                if tail:
                    extra, extra_end = tail
                if already and not extra:
                    buf.append(line[i:shape_end])
                    i = shape_end
                    continue
                bare = stripped[1:-1] if already else inner
                if extra or any(c in bare for c in _LABEL_SPECIAL):
                    text = bare.strip()
                    if extra:
                        text = f"{text} {extra}".strip()
                    safe = text.replace('"', "#quot;")
                    buf.append(f'{open_d}"{safe}"{close_d}')
                    i = shape_end + extra_end
                    continue
                buf.append(line[i:shape_end])
                i = shape_end
                continue
            buf.append(ch)
            i += 1
        out_lines.append("".join(buf))
    return "\n".join(out_lines)


def _chain_edgeless_flowchart(text: str) -> str:
    """Connect consecutive flowchart nodes when the source has no edges at all.

    A ``flowchart TD`` of bare nodes lays out as one horizontal row with empty
    gaps. Sequence, state, mindmap, and timeline are left untouched. An existing
    ``-->`` / ``---`` keeps the graph as written, including orphan nodes.
    """
    lines = text.splitlines()
    if not any(_FLOW_HEADER.match(line) for line in lines):
        return text
    if any(
        _FLOW_EDGE.search(line) and not line.strip().startswith("%%") for line in lines
    ):
        return text
    ids: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line.strip().startswith("%%"):
            continue
        match = _FLOW_NODE.match(line)
        if not match:
            continue
        node_id = match.group(1)
        if node_id.lower() in _FLOW_SKIP_IDS or node_id in seen:
            continue
        seen.add(node_id)
        ids.append(node_id)
    if len(ids) < 2:
        return text
    edges = [f"  {left} --> {right}" for left, right in zip(ids, ids[1:])]
    return text.rstrip() + "\n" + "\n".join(edges)


def sanitize_mermaid(text: str) -> str:
    """Strip optional fences; reject empty / oversized bodies; normalize graph→flowchart.

    Keeps model ``classDef`` / ``:::role`` / ``style`` coloring. Strips ``click``
    lines; rewrites purple hex fills to Liber sage; repairs broken ``class`` lines.
    """
    raw = (text or "").strip()
    if not raw:
        raise DiagramError("empty mermaid")
    if "\n" not in raw and ("\\n" in raw or "\\r\\n" in raw):
        raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n")
    m = _FENCE.match(raw)
    if m:
        raw = m.group(1).strip()
    # Also strip a leading ```mermaid line if model left an open fence fragment
    if raw.lower().startswith("```mermaid"):
        raw = re.sub(r"^```mermaid\s*\n?", "", raw, count=1, flags=re.I).strip()
        if raw.endswith("```"):
            raw = raw[: -3].rstrip()
    if not raw:
        raise DiagramError("empty mermaid after fence strip")
    if len(raw) > _MAX_BODY:
        raise DiagramError(f"mermaid too long ({len(raw)} > {_MAX_BODY})")
    # Mermaid accepts `graph` as alias of flowchart — normalize for Liber + type gate.
    raw = re.sub(r"(?im)^(\s*)graph(\s+)", r"\1flowchart\2", raw, count=1)
    raw = _CLICK_LINE.sub("", raw)
    raw = _SHORT_ROLE_SUFFIX.sub(":::", raw)
    raw = _repair_class_assign_lines(raw)
    raw = _repair_sequence_diagram_lines(raw)
    raw = _normalize_edge_label_spaces(raw)
    raw = _quote_flowchart_nodes(raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    raw = _rewrite_unsafe_colors(raw)
    raw = _chain_edgeless_flowchart(raw)
    return raw


def first_meaningful_line(mermaid: str) -> str:
    """Return the first non-empty, non-comment line, skipping frontmatter blocks."""
    lines = (mermaid or "").splitlines()
    in_frontmatter = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if stripped.startswith("%%"):
            continue
        return stripped
    return ""


def _first_keyword(mermaid: str) -> str:
    line = first_meaningful_line(mermaid)
    m = _FIRST_TOKEN.match(line)
    return (m.group(1) if m else "").lower()


def _normalize_type(dtype: str) -> str:
    t = (dtype or "").strip()
    aliases = {
        "state": "stateDiagram",
        "statediagram": "stateDiagram",
        "statediagram-v2": "stateDiagram",
        "sequencediagram": "sequence",
        "flow": "flowchart",
        "graph": "flowchart",
    }
    key = t.lower()
    return aliases.get(key, t)


def header_matches_type(dtype: str, mermaid: str) -> bool:
    """True when first Mermaid keyword matches diagrams[].type whitelist."""
    kw = _first_keyword(mermaid)
    allowed = _TYPE_HEADERS.get(dtype)
    if not allowed:
        return False
    return kw in allowed


@overload
def parse_diagrams(
    raw: Any, *, max_diagrams: int, with_drops: Literal[False] = False
) -> list[dict[str, Any]]: ...


@overload
def parse_diagrams(
    raw: Any, *, max_diagrams: int, with_drops: Literal[True]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]: ...


def parse_diagrams(
    raw: Any, *, max_diagrams: int, with_drops: bool = False
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Validate LLM diagrams[]; drop bad entries (soft-fail).

    When with_drops=True, also return [{id, reason}, ...] for meta/UI later.
    """
    out: list[dict[str, Any]] = []
    drops: list[dict[str, str]] = []
    if not isinstance(raw, list) or max_diagrams <= 0:
        return (out, drops) if with_drops else out
    for item in raw:
        if not isinstance(item, dict):
            continue
        did = str(item.get("id", "")).strip()
        dtype = _normalize_type(str(item.get("type", "")).strip())
        title = str(item.get("title", "") or item.get("caption", "") or "").strip()
        mermaid_raw = str(item.get("mermaid", "")).strip()
        if not _ID_OK.match(did):
            drops.append({"id": did or "?", "reason": "bad id"})
            continue
        if dtype not in DIAGRAM_TYPES:
            drops.append({"id": did, "reason": f"unknown type {dtype!r}"})
            continue
        if not mermaid_raw:
            drops.append({"id": did, "reason": "empty mermaid"})
            continue
        try:
            mermaid = sanitize_mermaid(mermaid_raw)
        except DiagramError as exc:
            log.warning("drop diagram %s: %s", did, exc)
            drops.append({"id": did, "reason": str(exc)})
            continue
        if not header_matches_type(dtype, mermaid):
            reason = (
                f"type/header mismatch: type={dtype} "
                f"first={_first_keyword(mermaid)!r}"
            )
            log.warning("drop diagram %s: %s", did, reason)
            drops.append({"id": did, "reason": reason})
            continue
        if not title:
            title = did
        out.append(
            {
                "id": did,
                "title": title[:_MAX_TITLE],
                "type": dtype,
                "mermaid": mermaid,
            }
        )
        if len(out) >= max_diagrams:
            break
    return (out, drops) if with_drops else out
