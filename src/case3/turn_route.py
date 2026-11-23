"""Decide chat vs artifact from the user's words and an optional plaque.

The plaque is a default, not a gate. A named action in the message wins.
An analyze line that names no artifact uses the plaque, unless that plaque
was negated («без схемы, расскажи»).
"""

from __future__ import annotations

import re

TurnKind = str  # chat | report | diagram | presentation

_MAKE = re.compile(
    r"\b("
    r"сделай|сделать|собери|собрать|подготовь|подготовить|"
    r"оформи|оформить|сверстай|нарисуй|построй|построить|"
    r"сгенерируй|сгенерировать|напиши|написать|выгрузи|экспортируй"
    r")\b",
    re.IGNORECASE,
)
_ANALYZE = re.compile(
    r"\b("
    r"проанализируй|проанализировать|разбери|разобрать|разложи|разложить|"
    r"сравни|сравнить|объясни|объяснить|посчитай|посчитать|"
    r"расскажи|рассказать|поясни|пояснить|оцени|оценить|"
    r"перескажи|почему|зачем|"
    r"опиши|описать|выдели|выделить|"
    r"суммируй|суммировать|перечисли|кратко"
    r")\b",
    re.IGNORECASE,
)
_PRESENTATION = re.compile(
    r"презентац|презу|преза|слайд|pptx|\bdeck\b",
    re.IGNORECASE,
)
_DIAGRAM = re.compile(
    r"схем|flowchart|mermaid",
    re.IGNORECASE,
)
_REPORT = re.compile(
    r"отч[её]т|\bpdf\b|\bdocx\b|\bword\b|ворд|справк",
    re.IGNORECASE,
)
_CHART_REQ = re.compile(
    r"график|диаграмм|чарт|\bchart\b|гистограмм|кругов\w*|линейн\w*",
    re.IGNORECASE,
)
_IN_CHAT = re.compile(
    r"(?:^|\s)(?:в\s+чат[е]?|без\s+отч[её]т[ао]?)\b",
    re.IGNORECASE,
)
_ON_THIS_DATA = re.compile(
    r"по\s+(?:этим\s+)?данным",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"\?\s*$|"
    r"(?:^|[\s,])(?:"
    r"что|как|где|какой|какая|какие|какое|каких|какую|"
    r"сколько|когда|кто|чем|чему"
    r")\b",
    re.IGNORECASE,
)
# «не делай отчёт», «без схемы» — noun is present, the request is not.
_NEG_BEFORE = re.compile(
    r"(?:^|\s)(?:не|без)(?:\s+(?:надо|нужно|нужен|нужна|делай|сделай|собери|хочу))?\s*$",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return (text or "").replace("ё", "е").replace("Ё", "Е")


def _plaque_blocked(raw: str, plaque: str) -> bool:
    """True when every mention of this plaque's artifact is negated."""
    pattern = {
        "presentation": _PRESENTATION,
        "diagram": _DIAGRAM,
        "report": _REPORT,
    }[plaque]
    matches = list(pattern.finditer(raw))
    if not matches:
        return False
    for match in matches:
        window = raw[max(0, match.start() - 32) : match.start()]
        if not _NEG_BEFORE.search(window):
            return False
    return True


def _live_kinds(raw: str) -> list[str]:
    found: list[str] = []
    for kind, pattern in (
        ("presentation", _PRESENTATION),
        ("diagram", _DIAGRAM),
        ("report", _REPORT),
    ):
        for match in pattern.finditer(raw):
            window = raw[max(0, match.start() - 32) : match.start()]
            if _NEG_BEFORE.search(window):
                continue
            found.append(kind)
            break
    return found


def _asked(pattern: re.Pattern[str], text: str | None) -> bool:
    raw = _norm(text or "")
    for match in pattern.finditer(raw):
        window = raw[max(0, match.start() - 32) : match.start()]
        if not _NEG_BEFORE.search(window):
            return True
    return False


def wants_chat_chart(text: str | None) -> bool:
    """True when the user asks to draw a chart/graph without negating it."""
    return _asked(_CHART_REQ, text)


def wants_chat_diagram(text: str | None) -> bool:
    """True when the user asks for a schema in the chat, not a file."""
    return _asked(_DIAGRAM, text)


def resolve_turn(text: str | None, bias: str | None) -> TurnKind:
    """Return chat, report, diagram, or presentation."""
    raw = _norm(text or "")
    plaque = (bias or "").strip().lower()
    if plaque not in {"report", "diagram", "presentation"}:
        plaque = ""

    kinds = _live_kinds(raw)

    make = bool(_MAKE.search(raw))
    analyze = bool(_ANALYZE.search(raw))
    # Explicit «в чате» / «без отчёта» keeps chart/analysis requests out of file builds.
    if _IN_CHAT.search(raw) and not kinds:
        return "chat"
    # A question reads the file. It does not start a new one.
    if _QUESTION.search(raw) and not make:
        return "chat"

    if (
        kinds == ["diagram"]
        and plaque != "diagram"
        and (_ON_THIS_DATA.search(raw) or _IN_CHAT.search(raw))
    ):
        return "chat"
    if kinds and (make or not analyze):
        return kinds[0]
    if analyze:
        if plaque and not kinds and not _plaque_blocked(raw, plaque):
            return plaque
        return "chat"
    if plaque:
        return plaque
    if kinds:
        return kinds[0]
    return "chat"
