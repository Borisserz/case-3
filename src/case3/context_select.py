"""Deterministic source catalog, chunking, and evidence selection for GCP."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from case3.chat_memory import (
    _RECALL,
    _query_stems,
    _stem,
    _stem_set,
    _topic_words,
    _turn_blob,
    format_thread,
    load_chain,
    split_sources,
)

CURRENT_DOC_ID = "doc:current"
CHUNK_SIZE = 6_000

_COMPARE = re.compile(
    r"\b(?:сравни\w*|оба|обе|перв\w*\s+и\s+втор\w*)\b",
    re.IGNORECASE,
)
_ORDINALS = (
    (1, re.compile(r"\bперв\w*", re.IGNORECASE)),
    (2, re.compile(r"\bвтор\w*", re.IGNORECASE)),
    (3, re.compile(r"\bтрет\w*", re.IGNORECASE)),
    (4, re.compile(r"\bчетверт\w*", re.IGNORECASE)),
    (5, re.compile(r"\bпят\w*", re.IGNORECASE)),
)
_DOC_NUMBER = re.compile(
    r"\b(?:файл|документ)\w*\s*(?:№\s*)?([1-5])\b"
    r"|\b([1-5])\s*(?:-?[йяе]|-?го)?\s*(?:файл|документ)",
    re.IGNORECASE,
)
_MARKED_TITLE = re.compile(r"^Документ\s+\d+\s*:\s*(.+)$", re.IGNORECASE)
_WORD = re.compile(r"[0-9A-Za-zА-Яа-яЁё]{3,}")
_GENERIC_TITLES = frozenset({"документ", "источник", "файл"})


@dataclass(frozen=True)
class SourceItem:
    """One source with content retained for deterministic chunking."""

    source_id: str
    title: str
    text: str
    ordinal: int
    kind: str = "document"
    edited: bool = False
    content_hash: str = ""


@dataclass(frozen=True)
class Chunk:
    """A selectable, source-bound evidence window."""

    chunk_id: str
    source_id: str
    title: str
    text: str
    reasons: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass(frozen=True)
class DialogueItem:
    """One recent or recalled turn; dialogue never grounds numbers."""

    turn_id: str
    role: str
    text: str
    number_evidence: bool = False


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _slug(text: str) -> str:
    value = re.sub(r"[^0-9a-zа-яё]+", "-", text.casefold()).strip("-")
    return value[:64] or "document"


def _attachment_values(attachment: Any) -> tuple[str, str, str, bool]:
    if isinstance(attachment, (tuple, list)) and len(attachment) >= 2:
        return str(attachment[0] or "Документ"), str(attachment[1] or ""), "document", False
    if isinstance(attachment, dict):
        title = attachment.get("title") or attachment.get("name") or attachment.get("filename")
        text = attachment.get("text") or attachment.get("content") or attachment.get("source_text")
        return (
            str(title or "Документ"),
            str(text or ""),
            str(attachment.get("kind") or "document"),
            bool(attachment.get("edited", False)),
        )
    title = (
        getattr(attachment, "title", None)
        or getattr(attachment, "name", None)
        or getattr(attachment, "filename", None)
    )
    text = (
        getattr(attachment, "text", None)
        or getattr(attachment, "content", None)
        or getattr(attachment, "source_text", None)
    )
    return (
        str(title or "Документ"),
        str(text or ""),
        str(getattr(attachment, "kind", "document") or "document"),
        bool(getattr(attachment, "edited", False)),
    )


def catalog_sources(source_text: str, attachments: list | None) -> list[SourceItem]:
    """Catalog marked source blobs and optional attachment records."""
    raw = (source_text or "").strip()
    marked = bool(re.search(r"^===== .+? =====\s*$", raw, re.MULTILINE))
    records: list[tuple[str, str, str, bool]] = [
        (title, text, "document", False) for title, text in split_sources(raw)
    ]
    records.extend(_attachment_values(item) for item in attachments or [])

    items: list[SourceItem] = []
    used_ids: set[str] = set()
    for ordinal, (raw_title, body, kind, edited) in enumerate(records, start=1):
        text = body.strip()
        if not text:
            continue
        marker_match = _MARKED_TITLE.match(raw_title.strip())
        title = marker_match.group(1).strip() if marker_match else raw_title.strip()
        title = title or "Документ"
        if raw and not marked and ordinal == 1:
            source_id = CURRENT_DOC_ID
        else:
            prefix = "screen" if kind == "screen" else "doc"
            source_id = f"{prefix}:{_slug(title)}"
            if source_id in used_ids:
                source_id = f"{source_id}-{ordinal}"
        used_ids.add(source_id)
        items.append(
            SourceItem(
                source_id=source_id,
                title=title,
                text=text,
                ordinal=ordinal,
                kind=kind,
                edited=edited,
                content_hash=_hash(text),
            )
        )
    return items


def _windows(item: SourceItem) -> list[str]:
    lines = item.text.splitlines()
    if not lines:
        return []
    windows: list[str] = []
    current: list[str] = []
    heading = ""
    size = 0
    for line in lines:
        line_size = len(line) + 1
        if current and size + line_size > CHUNK_SIZE:
            windows.append("\n".join(current).strip())
            current = [heading] if heading and not line.startswith("#") else []
            size = sum(len(value) + 1 for value in current)
        if line.startswith("#"):
            heading = line
        current.append(line)
        size += line_size
    if current:
        windows.append("\n".join(current).strip())
    return [window for window in windows if window]


def chunk_source(item: SourceItem) -> list[Chunk]:
    """Split on line boundaries, preserving markdown rows and active headings."""
    return [
        Chunk(
            chunk_id=f"{item.source_id}:{index}",
            source_id=item.source_id,
            title=item.title,
            text=text,
        )
        for index, text in enumerate(_windows(item))
    ]


def detect_comparison(query: str) -> bool:
    return bool(_COMPARE.search(query or ""))


def _ordinal_mentions(query: str) -> list[int]:
    mentions = {index for index, pattern in _ORDINALS if pattern.search(query or "")}
    for match in _DOC_NUMBER.finditer(query or ""):
        mentions.add(int(match.group(1) or match.group(2)))
    return sorted(mentions)


def source_ids_for_query(
    query: str,
    catalog: list[SourceItem],
    *,
    comparison: bool,
) -> list[str]:
    """Resolve explicit ordinals or filenames without collapsing comparisons."""
    ordinal_ids = [
        catalog[index - 1].source_id
        for index in _ordinal_mentions(query)
        if 0 < index <= len(catalog)
    ]
    if ordinal_ids:
        return ordinal_ids if comparison else ordinal_ids[:1]

    title_ids = [
        item.source_id
        for item in catalog
        if _title_in_query(item.title, query)
    ]
    if title_ids:
        return title_ids if comparison else title_ids[:1]
    if comparison:
        return [item.source_id for item in catalog]
    return []


def _tokens(text: str) -> set[str]:
    return {word.casefold() for word in _WORD.findall(text or "")}


def _title_in_query(title: str, query: str) -> bool:
    folded_title = title.casefold().strip()
    stem = folded_title.rsplit(".", 1)[0]
    if folded_title in _GENERIC_TITLES or stem in _GENERIC_TITLES:
        return False
    folded_query = (query or "").casefold()
    return folded_title in folded_query or bool(
        re.search(rf"(?<!\w){re.escape(stem)}(?!\w)", folded_query)
    )


def _score(chunk: Chunk, query: str, item: SourceItem, focused: set[str]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    if item.source_id in focused:
        score += 1_000.0
        reasons.append("explicit_source")
    if _title_in_query(item.title, query):
        score += 800.0
        reasons.append("filename")
    overlap = len(_tokens(query) & _tokens(chunk.text))
    if overlap:
        score += float(overlap * 10)
        reasons.append("body_overlap")
    if chunk.text.lstrip().startswith("#"):
        score += 1.0
        reasons.append("heading")
    return score, reasons or ["catalog_order"]


def _fit_chunk(chunk: Chunk, remaining: int) -> Chunk | None:
    if remaining <= 0:
        return None
    if len(chunk.text) <= remaining:
        return chunk
    lines: list[str] = []
    used = 0
    for line in chunk.text.splitlines():
        needed = len(line) + (1 if lines else 0)
        if used + needed > remaining:
            break
        lines.append(line)
        used += needed
    if not lines:
        return None
    return replace(
        chunk,
        text="\n".join(lines),
        reasons=[*chunk.reasons, "budget_truncated"],
    )


def select_evidence(
    query: str,
    catalog: list[SourceItem],
    *,
    budget: int,
    comparison: bool,
) -> list[Chunk]:
    """Select relevant chunks with strict, non-transferable comparison quotas."""
    if budget <= 0 or not catalog:
        return []
    named_ids = source_ids_for_query(query, catalog, comparison=comparison)
    selected_ids = named_ids or [item.source_id for item in catalog]
    selected_set = set(selected_ids)
    candidates = [item for item in catalog if item.source_id in selected_set]
    quota = budget // len(candidates) if comparison and candidates else budget

    selected: list[Chunk] = []
    focused = set(named_ids)
    for item in candidates:
        ranked: list[Chunk] = []
        for chunk in chunk_source(item):
            score, reasons = _score(chunk, query, item, focused)
            ranked.append(replace(chunk, score=score, reasons=reasons))
        ranked.sort(key=lambda chunk: (-chunk.score, chunk.chunk_id))
        remaining = quota
        for chunk in ranked:
            fitted = _fit_chunk(chunk, remaining)
            if fitted is None:
                continue
            selected.append(fitted)
            remaining -= len(fitted.text)
            if remaining <= 0:
                break
    return selected


def _dialogue_text(turn: dict[str, Any], *, offset: int = 0) -> str:
    """Format one turn with the same age-dependent caps as format_thread."""
    thread = format_thread([turn, *({} for _ in range(offset))])
    lines = thread.splitlines()
    return "\n".join(lines[2:]).strip() if len(lines) > 2 else ""


def _recall_stems(user_text: str) -> list[str]:
    raw = (user_text or "").replace("ё", "е").replace("Ё", "Е")
    if _RECALL.search(raw):
        return [_stem(word) for word in _topic_words(raw)]
    return _query_stems(raw)


def _recall_turns(
    older: list[dict[str, Any]],
    user_text: str,
) -> list[tuple[int, dict[str, Any]]]:
    stems = _recall_stems(user_text)
    if not stems:
        return []
    threshold = 2 if len(stems) >= 2 else 1
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for index, turn in enumerate(older):
        have = _stem_set(_turn_blob(turn))
        score = sum(stem in have for stem in stems)
        if score >= threshold:
            ranked.append((score, index, turn))
    ranked.sort(key=lambda row: (-row[0], -row[1]))
    selected = ranked[:2]
    return sorted(
        [(index, turn) for _score, index, turn in selected],
        key=lambda row: row[0],
    )


def _fit_dialogue(item: DialogueItem, remaining: int) -> DialogueItem | None:
    if remaining <= 0 or not item.text:
        return None
    if len(item.text) <= remaining:
        return item
    text = item.text[:remaining].rstrip()
    if not text:
        return None
    return replace(item, text=text)


def select_dialogue(
    root: Path,
    prior_run_id: str | None,
    user_text: str,
    *,
    budget: int,
) -> list[DialogueItem]:
    """Select up to eight recent turns plus two relevant older recalls."""
    if budget <= 0 or not (prior_run_id or "").strip():
        return []
    chain = load_chain(Path(root), str(prior_run_id))
    if not chain:
        return []

    recent = chain[-8:]
    older = chain[:-8]
    remaining = budget
    selected_recent: list[DialogueItem] = []
    for reverse_index, turn in enumerate(reversed(recent)):
        chain_index = len(chain) - 1 - reverse_index
        item = DialogueItem(
            turn_id=str(turn.get("run_id") or f"turn-{chain_index + 1}"),
            role="recent",
            text=_dialogue_text(turn, offset=reverse_index),
        )
        fitted = _fit_dialogue(item, remaining)
        if fitted is None:
            break
        selected_recent.append(fitted)
        remaining -= len(fitted.text)
        if len(fitted.text) < len(item.text):
            break
    selected_recent.reverse()

    selected_recalls: list[DialogueItem] = []
    for index, turn in _recall_turns(older, user_text):
        item = DialogueItem(
            turn_id=str(turn.get("run_id") or f"turn-{index + 1}"),
            role="recall",
            text=_dialogue_text(turn),
        )
        fitted = _fit_dialogue(item, remaining)
        if fitted is None:
            break
        selected_recalls.append(fitted)
        remaining -= len(fitted.text)
        if len(fitted.text) < len(item.text):
            break

    return [*selected_recalls, *selected_recent]
