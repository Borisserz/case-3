"""Typed turn plan (TTG) — deterministic route before pipeline execution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from case3.chat_act import (
    ChatAct,
    _slide_number_named,
    explicit_new_artifact,
    parse_photo_edit,
    resolve_act,
)
from case3.turn_route import (
    _ANALYZE,
    _DIAGRAM,
    _IN_CHAT,
    _MAKE,
    _NEG_BEFORE,
    _PRESENTATION,
    _QUESTION,
    _REPORT,
    _live_kinds,
    _norm,
    _plaque_blocked,
    wants_chat_chart,
)

ROUTE_VERSION = "ttg-v1"
_MODE_HINTS = frozenset({"auto", "report", "diagram", "presentation", "chat"})
_PLAQUE_KINDS = frozenset({"report", "diagram", "presentation"})
_DIAGRAMMA = re.compile(r"диаграмм", re.IGNORECASE)
_PROCESS_DIAG = re.compile(
    r"процесс|этап|связ|последовательн|архитектур|flowchart|mermaid|онбординг",
    re.IGNORECASE,
)
_IN_REPORT = re.compile(r"\bв\s+отч[её]т", re.IGNORECASE)
_IN_PRESENTATION = re.compile(r"\bв\s+презентаци(?:ю|и)", re.IGNORECASE)

_PRIMARY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("presentation", _PRESENTATION),
    ("report", _REPORT),
    ("diagram", _DIAGRAM),
)
_CONTAINER_PRIMARIES = frozenset({"report", "presentation", "diagram"})


@dataclass
class TurnStep:
    """One executable step in a turn plan."""

    kind: str  # chat | report | diagram | presentation | revise


@dataclass
class TurnPlan:
    """Deterministic routing snapshot for a single user turn."""

    route_version: str
    kind: str
    steps: list[TurnStep]
    want_chat_chart: bool
    want_chat_diagram: bool
    build_media: dict[str, bool]
    edit_act: ChatAct | None
    mode_hint: str
    reason: str
    clarify_prompt: str | None
    note: str | None


def _normalize_mode_hint(mode_hint: str) -> str:
    hint = (mode_hint or "auto").strip().lower()
    if hint not in _MODE_HINTS:
        return "auto"
    return hint


def _normalize_bias(bias: str | None) -> str:
    plaque = (bias or "").strip().lower()
    if plaque not in _PLAQUE_KINDS:
        return ""
    return plaque


def _empty_build_media() -> dict[str, bool]:
    return {"chart": False, "diagram": False, "images": False}


_KIND_LABELS = {
    "chat": "чат",
    "report": "отчёт",
    "diagram": "схема",
    "presentation": "презентация",
    "revise": "правка",
}


def format_route_projection(plan: TurnPlan, *, kind: str | None = None) -> str:
    """Human-readable TTG route block for Intent (under «Требования UI»)."""
    if plan.kind == "clarify" and kind is None:
        return ""
    effective_kind = kind or plan.kind
    if effective_kind == "clarify":
        return ""
    label = _KIND_LABELS.get(effective_kind, effective_kind)
    lines = ["Маршрут:", f"- цель: {label}"]
    if plan.want_chat_chart:
        lines.append("- в чате: график")
    if plan.want_chat_diagram:
        lines.append("- в чате: схема")
    media = plan.build_media or {}
    if media.get("chart"):
        lines.append("- в документе: графики")
    if media.get("diagram"):
        lines.append("- в документе: схемы")
    if media.get("images"):
        lines.append("- в документе: фото")
    return "\n".join(lines)


def _ordered_primary_kinds(raw: str) -> list[str]:
    """Primary artifact nouns in text appearance order (first live hit per kind)."""
    hits: list[tuple[int, str]] = []
    for kind, pattern in _PRIMARY_PATTERNS:
        for match in pattern.finditer(raw):
            window = raw[max(0, match.start() - 32) : match.start()]
            if _NEG_BEFORE.search(window):
                continue
            hits.append((match.start(), kind))
            break
    hits.sort(key=lambda item: item[0])
    return [kind for _, kind in hits]


def _diagram_embedded_in_report(raw: str) -> bool:
    """True when schema/diagram is bundled inside a report request, not a second build."""
    report_m = _REPORT.search(raw)
    diag_m = _DIAGRAM.search(raw)
    if not report_m or not diag_m or diag_m.start() <= report_m.start():
        return False
    between = raw[report_m.end() : diag_m.start()]
    if _PRESENTATION.search(between):
        return False
    if re.search(r"\bс\b", between, re.IGNORECASE):
        return True
    return bool(re.search(r"и\s+схем", between, re.IGNORECASE))


def _container_primaries_ordered(raw: str) -> list[str]:
    ordered = _ordered_primary_kinds(raw)
    if _diagram_embedded_in_report(raw):
        ordered = [k for k in ordered if k != "diagram"]
    return [k for k in ordered if k in _CONTAINER_PRIMARIES]


def plan_turn(
    text: str | None,
    *,
    mode_hint: str = "auto",
    bias: str | None = None,
    has_deck: bool = False,
    has_report: bool = False,
    has_diagram: bool = False,
    has_chart: bool = False,
    has_photo: bool = False,
    last_section: str = "",
    last_op: str = "",
) -> TurnPlan:
    """Return a deterministic plan, including chart destination clarification."""
    raw = _norm(text or "")
    hint = _normalize_mode_hint(mode_hint)
    plaque = _normalize_bias(bias)
    effective_hint = hint if hint != "auto" else plaque

    kinds = _live_kinds(raw)
    make = bool(_MAKE.search(raw))
    analyze = bool(_ANALYZE.search(raw))
    in_chat = bool(_IN_CHAT.search(raw))
    chartish = wants_chat_chart(raw)
    process_diagramma = bool(_DIAGRAMMA.search(raw) and _PROCESS_DIAG.search(raw))
    schema_in_chat = kinds == ["diagram"] and in_chat
    explicit_container = bool(
        _IN_REPORT.search(raw)
        or _IN_PRESENTATION.search(raw)
        or any(kind in {"report", "presentation"} for kind in kinds)
    )
    clarify_prompt: str | None = None
    container_primaries = _container_primaries_ordered(raw)

    has_any_artifact = has_deck or has_report or has_diagram or has_chart or has_photo
    if parse_photo_edit(raw) is not None and not explicit_new_artifact(raw):
        act = resolve_act(
            raw,
            bias=bias,
            has_deck=has_deck,
            has_report=has_report,
            has_diagram=has_diagram,
            has_chart=has_chart,
            has_photo=has_photo,
            last_section=last_section,
            last_op=last_op,
        )
        if act.kind == "revise" and act.op == "edit_photo":
            return TurnPlan(
                route_version=ROUTE_VERSION,
                kind="revise",
                steps=[TurnStep(kind="revise")],
                want_chat_chart=False,
                want_chat_diagram=False,
                build_media=_empty_build_media(),
                edit_act=act,
                mode_hint=hint,
                reason="photo_edit",
                clarify_prompt=None,
                note=None,
            )
        if act.kind == "revise" and act.op == "ask":
            return TurnPlan(
                route_version=ROUTE_VERSION,
                kind="clarify",
                steps=[TurnStep(kind="clarify")],
                want_chat_chart=False,
                want_chat_diagram=False,
                build_media=_empty_build_media(),
                edit_act=act,
                mode_hint=hint,
                reason="photo_edit_clarify",
                clarify_prompt=act.say,
                note=None,
            )
    if has_any_artifact and not explicit_new_artifact(raw):
        act = resolve_act(
            raw,
            bias=bias,
            has_deck=has_deck,
            has_report=has_report,
            has_diagram=has_diagram,
            has_chart=has_chart,
            has_photo=has_photo,
            last_section=last_section,
            last_op=last_op,
        )
        if act.kind == "revise" and act.op not in {"", "ask"}:
            return TurnPlan(
                route_version=ROUTE_VERSION,
                kind="revise",
                steps=[TurnStep(kind="revise")],
                want_chat_chart=False,
                want_chat_diagram=False,
                build_media=_empty_build_media(),
                edit_act=act,
                mode_hint=hint,
                reason="existing_artifact_edit",
                clarify_prompt=None,
                note=None,
            )
        if act.kind == "revise" and act.op == "ask":
            return TurnPlan(
                route_version=ROUTE_VERSION,
                kind="clarify",
                steps=[TurnStep(kind="clarify")],
                want_chat_chart=False,
                want_chat_diagram=False,
                build_media=_empty_build_media(),
                edit_act=act,
                mode_hint=hint,
                reason="existing_artifact_clarify",
                clarify_prompt=act.say,
                note=None,
            )

    if process_diagramma:
        kind, reason = "diagram", "process_diagramma"
    elif schema_in_chat:
        kind, reason = "chat", "schema_in_chat"
    elif chartish and in_chat:
        kind, reason = "chat", "chart_in_chat"
    elif (
        chartish
        and effective_hint in {"report", "presentation", "diagram"}
        and not explicit_container
        and not process_diagramma
    ):
        # Plaque is a bias, not a destination lock: bare «создай график» draws in chat.
        # Explicit «в отчёте» / «в презентации» still goes through explicit_container.
        kind, reason = "chat", "plaque_chart_defaults_chat"
    elif _QUESTION.search(raw) and not make:
        kind, reason = "chat", "question"
    elif make and len(container_primaries) >= 2:
        kind, reason = container_primaries[0], "multi_primary"
    elif kinds and make:
        kind, reason = kinds[0], "make_noun"
    elif kinds and not analyze:
        kind, reason = kinds[0], "artifact_noun"
    elif analyze and kinds:
        kind, reason = "chat", "analyze_named_artifact"
    elif (
        analyze
        and not kinds
        and effective_hint in _PLAQUE_KINDS
        and not _plaque_blocked(raw, effective_hint)
    ):
        kind, reason = effective_hint, "analyze_bias"
    elif hint in _MODE_HINTS - {"auto"}:
        kind, reason = hint, "mode_hint"
    else:
        kind, reason = "chat", "default_chat"

    want_chat_chart = kind == "chat" and chartish and not process_diagramma
    want_chat_diagram = kind == "chat" and schema_in_chat
    build_media = _empty_build_media()
    if kind in {"report", "presentation"} and chartish:
        build_media["chart"] = True
    if kind == "report" and _diagram_embedded_in_report(raw):
        build_media["diagram"] = True

    if (
        kind == "presentation"
        and has_deck
        and _slide_number_named(raw)
        and not explicit_new_artifact(raw)
    ):
        ask = (
            "Это правка уже открытой презентации. "
            "Напиши «на слайде 1 напиши …» или «собери новую презентацию»."
        )
        return TurnPlan(
            route_version=ROUTE_VERSION,
            kind="clarify",
            steps=[TurnStep(kind="clarify")],
            want_chat_chart=False,
            want_chat_diagram=False,
            build_media=_empty_build_media(),
            edit_act=None,
            mode_hint=hint,
            reason="named_slide_is_not_a_new_deck",
            clarify_prompt=ask,
            note=None,
        )

    note: str | None = None
    if reason == "multi_primary":
        step_kinds = container_primaries[:2]
        steps = [TurnStep(kind=step_kind) for step_kind in step_kinds]
        dropped = container_primaries[2:]
        if dropped:
            labels = ", ".join(_KIND_LABELS.get(item, item) for item in dropped)
            note = (
                "За один запрос собираю не больше двух основных артефактов. "
                f"Не добавлено: {labels}."
            )
    else:
        steps = [TurnStep(kind=kind)]

    return TurnPlan(
        route_version=ROUTE_VERSION,
        kind=kind,
        steps=steps,
        want_chat_chart=want_chat_chart,
        want_chat_diagram=want_chat_diagram,
        build_media=build_media,
        edit_act=None,
        mode_hint=hint,
        reason=reason,
        clarify_prompt=clarify_prompt,
        note=note,
    )