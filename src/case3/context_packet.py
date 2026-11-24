"""Grounded Context Packet (GCP) — schema and builder."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from case3.turn_plan import TurnPlan

from case3.context_select import (
    catalog_sources,
    chunk_source,
    detect_comparison,
    select_dialogue,
    select_evidence,
    source_ids_for_query,
)

GCP_VERSION = "gcp-v1"

EVIDENCE_BUDGET_CHAT = 80_000
DIALOGUE_BUDGET = 24_000
ARTIFACT_BUDGET = 12_000


@dataclass
class PacketRoute:
    """TTG route projection for one packet."""

    kind: str
    want_chat_chart: bool = False
    want_chat_diagram: bool = False
    build_media: dict[str, bool] = field(default_factory=dict)


@dataclass
class PacketRequest:
    """Current user turn request slice."""

    text: str
    named_source_ids: list[str] = field(default_factory=list)
    compare: bool = False


@dataclass
class PacketBudgets:
    """Token/character budgets for context assembly."""

    evidence: int
    dialogue: int
    artifact: int
    per_source_quota: int | None = None


@dataclass
class SourceCatalogEntry:
    """Registered source in the catalog."""

    id: str
    title: str
    ordinal: int | None = None
    kind: str = "document"
    edited: bool = False
    content_hash: str = ""


@dataclass
class EvidenceChunk:
    """Selectable evidence with number-grounding flag."""

    chunk_id: str
    source_id: str
    title: str
    text: str
    reasons: list[str] = field(default_factory=list)
    number_evidence: bool = True


@dataclass
class DialogueExcerpt:
    """Dialogue memory excerpt — never number evidence."""

    turn_id: str
    role: str
    text: str
    number_evidence: bool = False


@dataclass
class HistoricalUserBinding:
    """ADR-0015/16 user number stem binding."""

    stem: str
    value: str


@dataclass
class ArtifactTarget:
    """Phase B artifact slice — not number evidence."""

    artifact_id: str
    label: str
    number_evidence: bool = False


@dataclass
class PacketCoverage:
    """What was selected, omitted, or truncated."""

    selected: list[str] = field(default_factory=list)
    omitted: list[str] = field(default_factory=list)
    truncated: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


@dataclass
class SelectionManifest:
    """Inspectable selection record for persistence."""

    evidence_ids: list[str] = field(default_factory=list)
    dialogue_ids: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    quotas: dict[str, int] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)
    omitted: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ContextPacket:
    """Full grounded context package after TTG, before LLM."""

    version: str
    packet_id: str
    route: PacketRoute
    request: PacketRequest
    budgets: PacketBudgets
    source_catalog: list[SourceCatalogEntry] = field(default_factory=list)
    evidence: list[EvidenceChunk] = field(default_factory=list)
    dialogue: list[DialogueExcerpt] = field(default_factory=list)
    historical_user_bindings: list[HistoricalUserBinding] = field(default_factory=list)
    artifact_targets: list[ArtifactTarget] = field(default_factory=list)
    coverage: PacketCoverage = field(default_factory=PacketCoverage)
    selection_manifest: SelectionManifest = field(default_factory=SelectionManifest)


def _route_from_plan(plan: TurnPlan) -> PacketRoute:
    return PacketRoute(
        kind=plan.kind,
        want_chat_chart=plan.want_chat_chart,
        want_chat_diagram=plan.want_chat_diagram,
        build_media=dict(plan.build_media or {}),
    )


def build_context_packet(
    *,
    plan: TurnPlan,
    user_text: str,
    source_text: str,
    root: Path | None = None,
    prior_run_id: str | None = None,
    attachments: list | None = None,
) -> ContextPacket:
    """Build a source-aware GCP with deterministic evidence selection."""
    catalog_items = catalog_sources(source_text, attachments)
    comparison = detect_comparison(user_text)
    named_source_ids = source_ids_for_query(
        user_text,
        catalog_items,
        comparison=comparison,
    )
    compared_ids = (
        named_source_ids or [item.source_id for item in catalog_items]
        if comparison
        else []
    )
    per_source_quota = (
        EVIDENCE_BUDGET_CHAT // len(compared_ids) if compared_ids else None
    )
    budgets = PacketBudgets(
        evidence=EVIDENCE_BUDGET_CHAT,
        dialogue=DIALOGUE_BUDGET,
        artifact=ARTIFACT_BUDGET,
        per_source_quota=per_source_quota,
    )
    request = PacketRequest(
        text=user_text or "",
        named_source_ids=named_source_ids,
        compare=comparison,
    )
    route = _route_from_plan(plan)

    catalog = [
        SourceCatalogEntry(
            id=item.source_id,
            title=item.title,
            ordinal=item.ordinal,
            kind=item.kind,
            edited=item.edited,
            content_hash=item.content_hash,
        )
        for item in catalog_items
    ]
    selected_chunks = select_evidence(
        user_text,
        catalog_items,
        budget=budgets.evidence,
        comparison=comparison,
    )
    evidence = [
        EvidenceChunk(
            chunk_id=chunk.chunk_id,
            source_id=chunk.source_id,
            title=chunk.title,
            text=chunk.text,
            reasons=list(chunk.reasons),
            number_evidence=True,
        )
        for chunk in selected_chunks
    ]
    dialogue_items = (
        select_dialogue(
            root,
            prior_run_id,
            user_text,
            budget=budgets.dialogue,
        )
        if root is not None and prior_run_id
        else []
    )
    dialogue = [
        DialogueExcerpt(
            turn_id=item.turn_id,
            role=item.role,
            text=item.text,
            number_evidence=False,
        )
        for item in dialogue_items
    ]

    selected_ids = list(dict.fromkeys(chunk.source_id for chunk in selected_chunks))
    omitted_ids = [
        item.source_id for item in catalog_items if item.source_id not in selected_ids
    ]
    explicit_focus = bool(named_source_ids and not comparison)
    selected_counts = {
        source_id: sum(
            chunk.source_id == source_id for chunk in selected_chunks
        )
        for source_id in selected_ids
    }
    truncated_ids = [
        item.source_id
        for item in catalog_items
        if item.source_id in selected_counts
        and (
            selected_counts[item.source_id] < len(chunk_source(item))
            or any(
                chunk.source_id == item.source_id
                and "budget_truncated" in chunk.reasons
                for chunk in selected_chunks
            )
        )
    ]
    coverage = PacketCoverage(
        selected=selected_ids,
        omitted=omitted_ids,
        truncated=truncated_ids,
        notices=["explicit_focus"] if explicit_focus else [],
    )
    quota_ids = compared_ids if comparison else selected_ids
    quota = per_source_quota or budgets.evidence
    manifest = SelectionManifest(
        evidence_ids=[chunk.chunk_id for chunk in selected_chunks],
        dialogue_ids=[item.turn_id for item in dialogue],
        scores={chunk.chunk_id: chunk.score for chunk in selected_chunks},
        quotas={source_id: quota for source_id in quota_ids},
        hashes={item.source_id: item.content_hash for item in catalog_items},
        omitted=[
            {"source_id": source_id, "reason": "explicit_focus"}
            for source_id in omitted_ids
            if explicit_focus
        ],
    )

    return ContextPacket(
        version=GCP_VERSION,
        packet_id=f"gcp-{uuid.uuid4().hex[:12]}",
        route=route,
        request=request,
        budgets=budgets,
        source_catalog=catalog,
        evidence=evidence,
        dialogue=dialogue,
        coverage=coverage,
        selection_manifest=manifest,
    )


_ROUTE_KIND_LABELS = {
    "chat": "чат",
    "report": "отчёт",
    "diagram": "схема",
    "presentation": "презентация",
    "revise": "правка",
    "clarify": "уточнение",
}

_GROUNDING_LIMITS = (
    "Числа и факты бери только из «Выбранные источники» и текущего запроса.",
    "Контекст диалога и открытый артефакт — не Source.",
    "Число из прошлого ответа повторяй, только если оно есть в выбранных источниках.",
)


def _join_sections(sections: list[str]) -> str:
    parts = [section.strip() for section in sections if section and section.strip()]
    return "\n\n".join(parts)


def _render_route(route: PacketRoute) -> str:
    lines = ["## Маршрут хода", f"- цель: {_ROUTE_KIND_LABELS.get(route.kind, route.kind)}"]
    if route.want_chat_chart:
        lines.append("- в чате: график")
    if route.want_chat_diagram:
        lines.append("- в чате: схема")
    media = route.build_media or {}
    if media.get("chart"):
        lines.append("- в документе: графики")
    if media.get("diagram"):
        lines.append("- в документе: схемы")
    if media.get("images"):
        lines.append("- в документе: фото")
    return "\n".join(lines)


def _catalog_title(packet: ContextPacket, source_id: str) -> str:
    for entry in packet.source_catalog:
        if entry.id == source_id:
            return entry.title
    for chunk in packet.evidence:
        if chunk.source_id == source_id:
            return chunk.title
    return source_id


def _render_evidence(packet: ContextPacket) -> str:
    lines = ["## Выбранные источники"]
    if not packet.evidence:
        lines.append("(нет выбранных фрагментов)")
        return "\n".join(lines)
    by_source: dict[str, list[EvidenceChunk]] = {}
    for chunk in packet.evidence:
        by_source.setdefault(chunk.source_id, []).append(chunk)
    for source_id, chunks in by_source.items():
        title = _catalog_title(packet, source_id)
        lines.append(f"### [{source_id}] {title}")
        for chunk in chunks:
            lines.append(chunk.text.strip())
    return "\n".join(lines)


def _render_coverage(packet: ContextPacket) -> str:
    lines = ["## Покрытие источников"]
    coverage = packet.coverage
    if coverage.selected:
        lines.append("Выбрано: " + ", ".join(coverage.selected))
    if coverage.omitted:
        lines.append("Пропущено: " + ", ".join(coverage.omitted))
    if coverage.truncated:
        lines.append("Обрезано: " + ", ".join(coverage.truncated))
    if coverage.notices:
        lines.append("Заметки: " + ", ".join(coverage.notices))
    if packet.request.compare and packet.budgets.per_source_quota:
        lines.append(
            f"Сравнение: по {packet.budgets.per_source_quota} символов на источник."
        )
    return "\n".join(lines)


def _render_dialogue(packet: ContextPacket) -> str:
    if not packet.dialogue:
        return ""
    lines = [
        "## Контекст диалога — не источник чисел",
        "Числа и факты бери из «Выбранные источники». "
        "Прошлые ответы нужны, чтобы понять, о чём речь.",
    ]
    for item in packet.dialogue:
        prefix = "Вспоминание:" if item.role == "recall" else "Недавний ход:"
        lines.append(f"{prefix}\n{item.text.strip()}")
    return "\n".join(lines)


def _render_artifacts(packet: ContextPacket) -> str:
    if not packet.artifact_targets:
        return ""
    lines = [
        "## Открытый артефакт — не Source",
        "Это уже собранный файл, не источник чисел.",
    ]
    for target in packet.artifact_targets:
        lines.append(f"### [{target.artifact_id}] {target.label}")
    return "\n".join(lines)


def _render_user_bindings(packet: ContextPacket) -> str:
    if not packet.historical_user_bindings:
        return ""
    shown = [
        f"{binding.value} {binding.stem}".strip()
        for binding in packet.historical_user_bindings
    ]
    return "\n".join(
        [
            "## Числа из прошлых реплик пользователя",
            "(его слова, не ответ модели):",
            ", ".join(shown),
        ]
    )


def _render_limits() -> str:
    return "\n".join(["## Ограничение ответа", *_GROUNDING_LIMITS])


def render_chat_user_block(packet: ContextPacket) -> str:
    """Render GCP into the spec-ordered chat user block."""
    sections = [
        f"## Текущий запрос\n{(packet.request.text or '').strip()}",
        _render_route(packet.route),
        _render_evidence(packet),
        _render_coverage(packet),
        _render_dialogue(packet),
        _render_artifacts(packet),
        _render_user_bindings(packet),
        _render_limits(),
    ]
    return _join_sections(sections)