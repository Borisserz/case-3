"""Transcript of one Liber chat. It explains the next line. It is not Source."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_FULL_TURNS = 4
_MAX_HOPS = 48
_LINE = 280


def _clip(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    if limit <= 1:
        return ""
    return text[: limit - 1].rstrip() + "…"


def _one_line(meta: dict[str, Any]) -> str:
    summary = _clip(meta.get("chat_summary") or meta.get("chat_opening"), 120)
    prompt = _clip(meta.get("chat_prompt"), 80)
    if summary:
        return summary
    return prompt


def format_thread(turns: list[dict[str, Any]] | None) -> str:
    """Oldest first. Recent turns stay readable. Older ones shrink to one line."""
    rows = [t for t in (turns or []) if isinstance(t, dict)]
    if not rows:
        return ""
    lines = [
        "Разговор этого чата (не Source).",
        "Числа и факты бери только из документов этого запроса. "
        "Прошлые ответы нужны, чтобы понять, о чём речь.",
    ]
    older = rows[:-_FULL_TURNS] if len(rows) > _FULL_TURNS else []
    recent = rows[-_FULL_TURNS:]
    if older:
        first = _one_line(older[0])
        if first:
            lines.append("Начало: " + _clip(first, 160))
        brief = "; ".join(bit for bit in (_one_line(t) for t in older[1:]) if bit)
        if brief:
            lines.append("Раньше: " + _clip(brief, 400))
    for index, turn in enumerate(recent, start=len(older) + 1):
        prompt = _clip(turn.get("chat_prompt"), _LINE)
        summary = _clip(turn.get("chat_summary") or turn.get("chat_opening"), _LINE)
        mode = _clip(turn.get("output_mode"), 20)
        if prompt:
            lines.append(f"Ход {index}. Запрос: {prompt}")
        if summary:
            tail = f" ({mode})" if mode else ""
            lines.append(f"Ответ{tail}: {summary}")
        for note in turn.get("dialogue") or []:
            if not isinstance(note, dict):
                continue
            user = _clip(note.get("user"), 160)
            agent = _clip(note.get("assistant"), 160)
            if user:
                lines.append(f"Дальше: {user}")
            if agent:
                lines.append(f"Ответ: {agent}")
    for turn in reversed(rows):
        edit = turn.get("last_edit")
        if not isinstance(edit, dict):
            continue
        section = _clip(edit.get("section"), 80)
        if not section:
            continue
        lines.append(f"Последняя правка раздела: {section}. Это не новый факт.")
        break
    return "\n".join(lines)


def chain_limit_say() -> str:
    return (
        f"В этом чате уже {_MAX_HOPS} ходов, дальше контекст не помещается. "
        "Нажми «Новый чат» и продолжи там. Этот чат останется в списке слева."
    )


def chain_limit_payload(root: Path, prior_run_id: str | None) -> dict[str, Any] | None:
    """A new question or build past the chain cap. Edits are decided earlier."""
    rid = (prior_run_id or "").strip()
    if not rid:
        return None
    if len(load_chain(root, rid)) < _MAX_HOPS:
        return None
    return {
        "mode": "chat_revise",
        "status": "ok",
        "run_id": rid,
        "chat": chain_limit_say(),
        "op": "full",
        "surface": "",
        "output_mode": "chat",
    }


def load_chain(root: Path, run_id: str, *, hops: int = _MAX_HOPS) -> list[dict[str, Any]]:
    """Walk prior_run_id back to the start of this chat. Oldest first."""
    out_root = (Path(root) / "runs" / "out").resolve()
    seen: set[str] = set()
    found: list[dict[str, Any]] = []
    current = (run_id or "").strip()
    while current and current not in seen and len(found) < hops:
        seen.add(current)
        meta_path = (out_root / current / "meta.json").resolve()
        if not str(meta_path).startswith(str(out_root)) or not meta_path.is_file():
            break
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            break
        if not isinstance(meta, dict):
            break
        found.append(meta)
        current = str(meta.get("prior_run_id") or "").strip()
    found.reverse()
    return found


def append_dialogue(meta: dict[str, Any], user: str, assistant: str) -> None:
    """Remember an in-place edit on the same run. Cap the list."""
    notes = meta.get("dialogue")
    if not isinstance(notes, list):
        notes = []
    notes.append(
        {
            "user": _clip(user, 300),
            "assistant": _clip(assistant, 300),
        }
    )
    meta["dialogue"] = notes[-12:]


def format_sources(parts: list[tuple[str, str]] | None) -> str:
    """Labeled documents. The model can tell them apart."""
    rows = []
    for name, text in parts or []:
        title = " ".join(str(name or "Документ").split()) or "Документ"
        body = str(text or "").strip()
        if not body:
            continue
        rows.append(f"===== {title} =====\n{body}")
    return "\n\n".join(rows)


_PART = re.compile(r"^===== (.+?) =====\s*$", re.MULTILINE)


def split_sources(text: str | None) -> list[tuple[str, str]]:
    """Inverse of format_sources. A plain file stays one document."""
    raw = (text or "").strip()
    if not raw:
        return []
    marks = list(_PART.finditer(raw))
    if not marks:
        return [("Документ", raw)]
    parts: list[tuple[str, str]] = []
    for index, mark in enumerate(marks):
        start = mark.end()
        end = marks[index + 1].start() if index + 1 < len(marks) else len(raw)
        body = raw[start:end].strip()
        name = " ".join(mark.group(1).split()) or "Документ"
        if body:
            parts.append((name, body))
    return parts[:5]


_ORDINALS = (
    (1, re.compile(r"перв", re.IGNORECASE)),
    (2, re.compile(r"втор", re.IGNORECASE)),
    (3, re.compile(r"трет", re.IGNORECASE)),
    (4, re.compile(r"четверт", re.IGNORECASE)),
    (5, re.compile(r"пят", re.IGNORECASE)),
)
_DOC_WORD = re.compile(r"файл|документ", re.IGNORECASE)
_DOC_NUM = re.compile(r"\b([1-5])\b")


def document_index(message: str | None) -> int:
    """1-based document named in the message. 0 when none is named."""
    raw = (message or "").replace("ё", "е").replace("Ё", "Е")
    if not _DOC_WORD.search(raw):
        return 0
    number = _DOC_NUM.search(raw)
    if number:
        return int(number.group(1))
    for index, pattern in _ORDINALS:
        if pattern.search(raw):
            return index
    return 0


def focus_source(text: str | None, message: str | None) -> str:
    """Keep one labeled document when the message points at it."""
    raw = text or ""
    index = document_index(message)
    parts = split_sources(raw)
    if not index or index > len(parts):
        return raw
    name, body = parts[index - 1]
    return format_sources([(name, body)])


def load_chain_dirs(root: Path, run_id: str, *, hops: int = _MAX_HOPS) -> list[tuple[str, Path, dict[str, Any]]]:
    """Same walk as load_chain, with the run directory kept."""
    out_root = (Path(root) / "runs" / "out").resolve()
    seen: set[str] = set()
    found: list[tuple[str, Path, dict[str, Any]]] = []
    current = (run_id or "").strip()
    while current and current not in seen and len(found) < hops:
        seen.add(current)
        out_dir = (out_root / current).resolve()
        if not str(out_dir).startswith(str(out_root)):
            break
        meta_path = out_dir / "meta.json"
        if not meta_path.is_file():
            break
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            break
        if not isinstance(meta, dict):
            break
        found.append((current, out_dir, meta))
        current = str(meta.get("prior_run_id") or "").strip()
    found.reverse()
    return found


def newest_edit(root: Path, run_id: str) -> dict[str, str]:
    """Latest section or style remembered anywhere in this chat."""
    found: dict[str, str] = {}
    for _run_id, _path, meta in load_chain_dirs(root, run_id):
        raw = meta.get("last_edit")
        if not isinstance(raw, dict):
            continue
        edit = {
            key: str(raw.get(key) or "").strip()
            for key in ("op", "section", "pack", "palette")
            if str(raw.get(key) or "").strip()
        }
        if edit.get("section") or edit.get("op"):
            found = edit
    return found


def _dialogue(meta: dict[str, Any]) -> list[dict[str, str]]:
    notes = meta.get("dialogue")
    if not isinstance(notes, list):
        return []
    out: list[dict[str, str]] = []
    for note in notes:
        if not isinstance(note, dict):
            continue
        out.append(
            {
                "user": _clip(note.get("user"), 300),
                "assistant": _clip(note.get("assistant"), 300),
            }
        )
    return out[-12:]


def _source_file(root: Path, meta: dict[str, Any]) -> str:
    raw = str(meta.get("source") or "").strip()
    if not raw:
        return ""
    path = Path(raw).expanduser().resolve()
    base = (Path(root) / "runs").resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return ""
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return ""


def _copy_source_photos(root: Path, run_id: str, figs: Path) -> None:
    """A chat that never reached figures/ still has usr_*.png next to source.txt."""
    meta_path = Path(root) / "runs" / "out" / run_id / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(meta, dict):
        return
    source = Path(str(meta.get("source") or "")).expanduser()
    if not source.is_absolute():
        return
    base = (Path(root) / "runs").resolve()
    try:
        source.resolve().relative_to(base)
    except ValueError:
        return
    folder = source.parent / "user_photos"
    if not folder.is_dir():
        return
    pngs = sorted(folder.glob("usr_*.png"))
    if not pngs:
        return
    try:
        figs.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    for png in pngs[:5]:
        dest = figs / png.name
        if dest.is_file():
            continue
        try:
            dest.write_bytes(png.read_bytes())
        except OSError:
            continue


def _photo_thumbs(root: Path, run_id: str) -> list[dict[str, str]]:
    rid = (run_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_]+", rid):
        return []
    figs = (Path(root) / "runs" / "out" / rid / "figures").resolve()
    base = (Path(root) / "runs" / "out").resolve()
    try:
        figs.relative_to(base)
    except ValueError:
        return []
    if not figs.is_dir() or not any(figs.glob("usr_*.png")):
        _copy_source_photos(root, rid, figs)
    if not figs.is_dir():
        return []
    thumbs: list[dict[str, str]] = []
    for png in sorted(figs.glob("usr_*.png")):
        if not png.is_file():
            continue
        thumbs.append(
            {"name": png.stem, "url": f"/api/runs/{rid}/figures/{png.name}"}
        )
        if len(thumbs) == 5:
            break
    return thumbs


def memory_view(root: Path, run_id: str) -> dict[str, Any] | None:
    """One chat: turns oldest-first, plus the documents of the latest run."""
    chain = load_chain(root, run_id)
    if not chain:
        return None
    turns: list[dict[str, Any]] = []
    for meta in chain:
        edit = meta.get("last_edit")
        turn_id = str(meta.get("run_id") or "")
        turns.append(
            {
                "run_id": turn_id,
                "chat_prompt": _clip(meta.get("chat_prompt"), 2000),
                "chat_summary": _clip(
                    meta.get("chat_summary") or meta.get("chat_opening"), 2000
                ),
                "chat_opening": _clip(meta.get("chat_opening"), 600),
                "output_mode": _clip(meta.get("output_mode"), 20),
                "dialogue": _dialogue(meta),
                "last_edit": edit if isinstance(edit, dict) else {},
                "photos": _photo_thumbs(root, turn_id),
            }
        )
    source = ""
    for meta in reversed(chain):
        source = _source_file(root, meta)
        if source.strip():
            break
    if len(source) > 500_000:
        source = source[:500_000]
    documents = [{"name": name, "text": text} for name, text in split_sources(source)]
    return {
        "turns": turns,
        "documents": documents,
        "last_edit": newest_edit(root, run_id),
        "artifact_run_id": _artifact_run_id(root, run_id),
    }


def _artifact_run_id(root: Path, run_id: str) -> str:
    """Newest run in this chat that still holds a report or a deck."""
    found = ""
    for rid, path, meta in load_chain_dirs(root, run_id):
        mode = str(meta.get("output_mode") or "")
        slides = str(meta.get("slides_status") or "")
        artifacts = meta.get("artifacts")
        has_deck = mode == "presentation" or slides in {"ok", "running", "error"}
        has_report = mode == "report" or any(path.glob("*.tex")) or (
            isinstance(artifacts, dict) and bool(artifacts)
        )
        if has_deck or has_report:
            found = rid
    return found
