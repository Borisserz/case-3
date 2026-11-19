"""In-place chat edits. Same artifacts the rail buttons change."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from case3.chat_act import next_deck_pack, resolve_act
from case3.chat_memory import append_dialogue, load_chain_dirs
from case3.run_meta import update_meta
from case3.run_store import RUN_ID_OK


def _read(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "meta.json"
    if not path.is_file():
        return {}
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return meta if isinstance(meta, dict) else {}


def _flags(meta: dict[str, Any]) -> tuple[bool, bool, bool]:
    mode = str(meta.get("output_mode") or "")
    slides = str(meta.get("slides_status") or "")
    has_deck = mode == "presentation" or slides in {"ok", "running", "error"}
    artifacts = meta.get("artifacts")
    has_report = mode == "report" or (isinstance(artifacts, dict) and bool(artifacts))
    diagrams = meta.get("diagrams")
    has_diagram = mode == "diagram" or (isinstance(diagrams, list) and bool(diagrams))
    return has_deck, has_report, has_diagram


def _note(out_dir: Path, user: str, assistant: str, act: Any) -> None:
    def mut(meta: dict[str, Any]) -> None:
        append_dialogue(meta, user, assistant)
        remembered = _remembered(act, assistant)
        if remembered:
            meta["last_edit"] = remembered

    update_meta(out_dir, mut)


def _remembered(act: Any, say: str) -> dict[str, str] | None:
    import re

    if act.op == "rewrite" and "Переписал" in say:
        section = str(getattr(act, "section", "") or "")
        found = re.search(r"«([^»]+)»", say)
        if found:
            section = found.group(1).strip()
        if section:
            return {"op": "rewrite", "section": section}
    if act.op == "recolor_deck" and "Перекрашиваю" in say:
        return {"op": "recolor_deck", "pack": str(getattr(act, "pack", "") or "")}
    if act.op == "recolor_charts" and "Перекрасил" in say:
        return {"op": "recolor_charts", "palette": str(getattr(act, "palette", "") or "")}
    if act.op == "rename_heading" and "Переименовал" in say:
        section = str(getattr(act, "title", "") or "").strip()
        if section:
            return {"op": "rename_heading", "section": section}
    if act.op in {"undo", "redo"} and ("Отменил" in say or "Вернул" in say):
        return {"op": str(act.op)}
    return None


def _surface(act: Any) -> str:
    op = str(getattr(act, "op", "") or "")
    if op in {"recolor_deck", "delete_slide", "reorder_slide", "add_slide", "slide_text"}:
        return "deck"
    if op == "retitle" and str(getattr(act, "title_on", "") or "") == "deck":
        return "deck"
    if op in {
        "rewrite",
        "recolor_charts",
        "retype_charts",
        "retype_chart",
        "undo",
        "redo",
        "retitle",
        "rename_heading",
    }:
        return "report"
    return ""


def _payload(
    run_id: str,
    say: str,
    op: str,
    *,
    output_mode: str = "chat",
    surface: str = "",
    artifact_run_id: str = "",
    isolate: bool = False,
) -> dict[str, Any]:
    payload = {
        "mode": "chat_revise",
        "status": "ok",
        "run_id": run_id,
        "artifact_run_id": artifact_run_id or run_id,
        "chat": say,
        "op": op,
        "surface": surface,
        "output_mode": output_mode or "chat",
    }
    if isolate:
        payload["isolate"] = True
    return payload


def continue_or_limit(
    text: str,
    prior_run_id: str | None,
    *,
    root: Path,
    bias: str | None = None,
    carried_run_id: str | None = None,
) -> dict[str, Any] | None:
    """Edit in place, or stop a new turn when this chat is already full."""
    revised = try_chat_revise(
        text,
        prior_run_id,
        root=root,
        bias=bias,
        carried_run_id=carried_run_id,
    )
    if revised is not None:
        return revised
    from case3.chat_memory import chain_limit_payload

    return chain_limit_payload(root, prior_run_id)


def _run_dir(root: Path, run_id: str) -> Path | None:
    rid = (run_id or "").strip()
    if not rid or not RUN_ID_OK.match(rid):
        return None
    path = (Path(root) / "runs" / "out" / rid).resolve()
    base = (Path(root) / "runs" / "out").resolve()
    if not str(path).startswith(str(base)) or not (path / "meta.json").is_file():
        return None
    return path


def try_chat_revise(
    text: str,
    prior_run_id: str | None,
    *,
    root: Path,
    bias: str | None = None,
    carried_run_id: str | None = None,
) -> dict[str, Any] | None:
    """Return a chat response when the message edits the current artifact.

    None means the normal pipeline should run (talk or a new build).
    """
    rid = (prior_run_id or "").strip()
    rows = load_chain_dirs(root, rid) if rid and RUN_ID_OK.match(rid) else []
    carried_id = (carried_run_id or "").strip()
    if rows and not carried_id:
        carried_id = str(rows[-1][2].get("carried_run_id") or "").strip()
    carried_path = _run_dir(root, carried_id)
    if carried_path and any(run_id == carried_id for run_id, _path, _row in rows):
        carried_path = None
        carried_id = ""
    if not rows and carried_path is None:
        return None
    has_deck = has_report = has_diagram = False
    edit: dict[str, Any] = {}
    for _run_id, path, row in rows:
        deck, report, diagram = _flags(row)
        has_deck = has_deck or deck
        has_report = has_report or report or any(path.glob("*.tex"))
        has_diagram = has_diagram or diagram
        raw_edit = row.get("last_edit")
        if isinstance(raw_edit, dict) and (raw_edit.get("section") or raw_edit.get("op")):
            edit = raw_edit
    carried_meta: dict[str, Any] = _read(carried_path) if carried_path else {}
    if carried_path is not None:
        deck, report, diagram = _flags(carried_meta)
        has_deck = has_deck or deck
        has_report = has_report or report or any(carried_path.glob("*.tex"))
        has_diagram = has_diagram or diagram
        raw_edit = carried_meta.get("last_edit")
        if (
            not edit
            and isinstance(raw_edit, dict)
            and (raw_edit.get("section") or raw_edit.get("op"))
        ):
            edit = raw_edit
    if rows:
        head_id, head_dir, head_meta = rows[-1]
    else:
        head_id, head_dir, head_meta = carried_id, carried_path, carried_meta
    isolate = not rows
    act = resolve_act(
        text,
        bias=bias,
        has_deck=has_deck,
        has_report=has_report,
        has_diagram=has_diagram,
        last_section=str(edit.get("section") or ""),
        last_op=str(edit.get("op") or ""),
    )
    if act.kind != "revise":
        return None

    work_id, work_dir = head_id, head_dir
    if act.op in {"undo", "redo", "rewrite", "recolor_charts", "rename_heading"}:
        for run_id, path, _row in reversed(rows):
            if any(path.glob("*.tex")):
                work_id, work_dir = run_id, path
                break
    elif act.op in {"recolor_deck", "delete_slide", "reorder_slide", "add_slide", "slide_text"}:
        for run_id, path, row in reversed(rows):
            if _flags(row)[0]:
                work_id, work_dir = run_id, path
                break
    elif act.op in {"retype_charts", "retype_chart"}:
        for run_id, path, row in reversed(rows):
            planned = row.get("charts_planned")
            if (path / "figures.json").is_file() or (isinstance(planned, list) and planned):
                work_id, work_dir = run_id, path
                break
    elif act.op == "retitle":
        if act.title_on == "deck":
            for run_id, path, row in reversed(rows):
                if _flags(row)[0]:
                    work_id, work_dir = run_id, path
                    break
        else:
            for run_id, path, _row in reversed(rows):
                if any(path.glob("*.tex")):
                    work_id, work_dir = run_id, path
                    break
            else:
                for run_id, path, row in reversed(rows):
                    if _flags(row)[0]:
                        work_id, work_dir = run_id, path
                        break
    if carried_path is not None and work_id != carried_id:
        tex_ops = {"undo", "redo", "rewrite", "recolor_charts", "rename_heading"}
        deck_ops = {"recolor_deck", "delete_slide", "reorder_slide", "add_slide", "slide_text"}
        if act.op in tex_ops and not any(work_dir.glob("*.tex")) and any(carried_path.glob("*.tex")):
            work_id, work_dir = carried_id, carried_path
        elif act.op in deck_ops and not _flags(_read(work_dir))[0] and _flags(carried_meta)[0]:
            work_id, work_dir = carried_id, carried_path
        elif act.op in {"retype_charts", "retype_chart"}:
            planned = _read(work_dir).get("charts_planned")
            has_here = (work_dir / "figures.json").is_file() or (
                isinstance(planned, list) and bool(planned)
            )
            planned_carried = carried_meta.get("charts_planned")
            has_carried = (carried_path / "figures.json").is_file() or (
                isinstance(planned_carried, list) and bool(planned_carried)
            )
            if not has_here and has_carried:
                work_id, work_dir = carried_id, carried_path
    work_meta = _read(work_dir) or head_meta

    say = act.say
    if act.op == "undo":
        say = _history(work_dir, undo=True) or say
    elif act.op == "redo":
        say = _history(work_dir, undo=False) or say
    elif act.op == "recolor_deck":
        pack = act.pack or next_deck_pack(str(work_meta.get("slides_theme_pack") or ""))
        say = _recolor_deck(work_id, work_dir, pack) or say
    elif act.op == "recolor_charts" and act.palette:
        say = _recolor_charts(work_dir, act.palette) or say
    elif act.op == "rewrite":
        say = _rewrite(work_dir, text, act) or say
    elif act.op == "delete_slide" and act.slide:
        say = _delete_slide(work_id, work_dir, act.slide) or say
    elif act.op == "reorder_slide" and act.slide and act.slide_to:
        say = _reorder_slide(work_id, work_dir, act.slide, act.slide_to) or say
    elif act.op == "retype_charts" and act.chart:
        say = _retype_charts(work_dir, act.chart) or say
    elif act.op == "retype_chart" and act.chart and act.chart_at:
        say = _retype_one(work_dir, act.chart, act.chart_at) or say
    elif act.op == "rename_heading" and act.section and act.title:
        say = _rename_heading(work_dir, act.section, act.title) or say
    elif act.op == "slide_text" and act.slide and act.title:
        say = _slide_text(work_id, work_dir, act.slide, act.title) or say
    elif act.op == "add_slide" and act.title:
        say = _add_slide(work_id, work_dir, act.title) or say
    elif act.op == "retitle" and act.title:
        if act.title_on == "deck":
            say = _retitle_slide(work_id, work_dir, act.title, act.slide or 1) or say
        else:
            say = _retitle(work_id, work_dir, act.title) or say
    elif act.op == "ask":
        say = _with_headings(say, work_dir)

    chain_ids = {run_id for run_id, _path, _row in rows}
    if work_id in chain_ids and work_dir.is_dir():
        _note(work_dir, text, say, act)
    if (
        rows
        and head_id in chain_ids
        and head_dir != work_dir
        and head_dir.is_dir()
    ):
        _note(head_dir, text, say, act)
    return _payload(
        head_id,
        say,
        act.op,
        output_mode=str(head_meta.get("output_mode") or "chat"),
        surface=_surface(act),
        artifact_run_id=work_id,
        isolate=isolate,
    )


def _with_headings(say: str, out_dir: Path) -> str:
    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        return say
    try:
        titles = _heading_titles(texs[0].read_text(encoding="utf-8"))
    except OSError:
        return say
    if not titles:
        return say
    shown = ", ".join(titles[:8])
    if shown in say:
        return say
    return f"{say} Сейчас в отчёте: {shown}."


def _delete_slide(run_id: str, out_dir: Path, index: int) -> str:
    from fastapi import HTTPException

    from case3.api_slides import _enqueue_deck_rebuild, _load_deck_for_patch
    from case3.slides_ir import DeckIrError
    from case3.slides_patch import apply_deck_structure

    try:
        base, ir_path = _load_deck_for_patch(run_id, out_dir)
    except HTTPException as exc:
        return str(exc.detail)
    slides = base.get("slides") if isinstance(base, dict) else None
    if not isinstance(slides, list) or not slides:
        return "В этой презентации нет слайдов."
    if index < 1 or index > len(slides):
        return f"Слайда {index} нет. Сейчас их {len(slides)}."
    slide_id = str((slides[index - 1] or {}).get("id") or "")
    try:
        patched = apply_deck_structure(base, {"op": "delete", "id": slide_id})
    except DeckIrError as exc:
        return str(exc)
    _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        patched,
        undo_kind="slides_structure",
        undo_target=slide_id or "*",
    )
    return f"Убираю слайд {index}. Остальные соберутся заново."


def _reorder_slide(run_id: str, out_dir: Path, source: int, dest: int) -> str:
    from fastapi import HTTPException

    from case3.api_slides import _enqueue_deck_rebuild, _load_deck_for_patch
    from case3.slides_ir import DeckIrError
    from case3.slides_patch import apply_deck_structure

    try:
        base, ir_path = _load_deck_for_patch(run_id, out_dir)
    except HTTPException as exc:
        return str(exc.detail)
    slides = base.get("slides") if isinstance(base, dict) else None
    if not isinstance(slides, list) or len(slides) < 2:
        return "Переставлять нечего: в презентации меньше двух слайдов."
    if source < 1 or source > len(slides) or dest < 1 or dest > len(slides):
        return f"Такого места нет. Слайдов сейчас {len(slides)}."
    if source == dest:
        return f"Слайд {source} уже на этом месте."
    ids = [str((slide or {}).get("id") or "") for slide in slides]
    moved = ids.pop(source - 1)
    ids.insert(dest - 1, moved)
    try:
        patched = apply_deck_structure(base, {"op": "reorder", "order": ids})
    except DeckIrError as exc:
        return str(exc)
    _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        patched,
        undo_kind="slides_structure",
        undo_target=moved or "*",
    )
    return f"Переставляю слайд {source} на место {dest}."


def _rename_heading(out_dir: Path, old: str, new: str) -> str:
    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        return "Отчёта в этом чате ещё нет, переименовать нечего."
    try:
        titles = _heading_titles(texs[0].read_text(encoding="utf-8"))
    except OSError:
        return "Не смог прочитать разделы отчёта."
    want = old.casefold()
    hits = [
        index
        for index, title in enumerate(titles, start=1)
        if want in title.casefold() or title.casefold() in want
    ]
    if len(hits) != 1:
        shown = ", ".join(titles[:8])
        if shown:
            return f"Какой раздел переименовать? Сейчас в отчёте: {shown}."
        return "Такого раздела нет."
    from case3.heading_edit import HeadingEditError, edit_heading_in_run

    try:
        edit_heading_in_run(out_dir, hits[0], text=new, formats={"pdf", "docx"})
    except HeadingEditError as exc:
        return str(exc)
    return f"Переименовал раздел «{titles[hits[0] - 1]}» в «{new}». Текст тот же."


def _slide_text(run_id: str, out_dir: Path, index: int, text: str) -> str:
    from fastapi import HTTPException

    from case3.api_slides import _enqueue_deck_rebuild, _load_deck_for_patch
    from case3.slides_ir import DeckIrError
    from case3.slides_patch import apply_deck_text_patch

    try:
        base, ir_path = _load_deck_for_patch(run_id, out_dir)
    except HTTPException as exc:
        return str(exc.detail)
    slides = base.get("slides") if isinstance(base, dict) else None
    if not isinstance(slides, list) or not slides:
        return "В этой презентации нет слайдов."
    if index < 1 or index > len(slides):
        return f"Слайда {index} нет. Сейчас их {len(slides)}."
    slide_id = str((slides[index - 1] or {}).get("id") or "")
    try:
        patched = apply_deck_text_patch(
            base, {"slides": [{"id": slide_id, "title": text}]}
        )
    except DeckIrError as exc:
        return str(exc)
    _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        patched,
        undo_kind="slides_patch",
        undo_target=slide_id or "*",
    )
    return f"Меняю заголовок слайда {index}. Новых чисел нет."


def _add_slide(run_id: str, out_dir: Path, title: str) -> str:
    from fastapi import HTTPException

    from case3.api_slides import _enqueue_deck_rebuild, _load_deck_for_patch
    from case3.slides_patch import _fresh_slide_id

    try:
        base, ir_path = _load_deck_for_patch(run_id, out_dir)
    except HTTPException as exc:
        return str(exc.detail)
    slides = base.get("slides") if isinstance(base, dict) else None
    if not isinstance(slides, list) or not slides:
        return "В этой презентации нет слайдов."
    if len(slides) >= 24:
        return "В презентации уже 24 слайда."
    topic = " ".join(title.split())[:120]
    new_id = _fresh_slide_id({str(slide.get("id") or "") for slide in slides if isinstance(slide, dict)})
    slides.append(
        {
            "id": new_id,
            "layout": "bullets",
            "title": topic,
            "bullets": [topic],
        }
    )
    base["slides"] = slides
    _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        base,
        undo_kind="slides_structure",
        undo_target=new_id,
    )
    return f"Добавляю слайд «{topic}». Новых чисел нет."


def _retype_one(out_dir: Path, chart_type: str, index: int) -> str:
    from case3.chart_edit import ChartEditError, edit_chart_in_run
    from case3.chat_act import CHART_SAY

    label = CHART_SAY.get(chart_type, chart_type)
    ids = _chart_ids(out_dir)
    if not ids:
        return "Графиков в этом материале нет."
    if index < 1 or index > len(ids):
        return f"Графика {index} нет. Сейчас их {len(ids)}."
    formats = {"pdf", "docx"} if any(out_dir.glob("*.tex")) else set()
    try:
        edit_chart_in_run(out_dir, ids[index - 1], chart_type=chart_type, formats=formats)
    except ChartEditError as exc:
        return str(exc)
    return f"Меняю график {index} на {label}. Числа те же."


def _retype_charts(out_dir: Path, chart_type: str) -> str:
    from case3.chart_edit import ChartEditError, edit_chart_in_run
    from case3.chat_act import CHART_SAY

    label = CHART_SAY.get(chart_type, chart_type)
    ids = _chart_ids(out_dir)
    if not ids:
        return "Графиков в этом материале нет."
    formats = {"pdf", "docx"} if any(out_dir.glob("*.tex")) else set()
    for chart_id in ids:
        try:
            edit_chart_in_run(
                out_dir,
                chart_id,
                chart_type=chart_type,
                formats=formats,
            )
        except ChartEditError as exc:
            return str(exc)
    return f"Меняю графики на {label}. Числа те же."


def _chart_ids(out_dir: Path) -> list[str]:
    meta = _read(out_dir)
    planned = meta.get("charts_planned")
    if isinstance(planned, list):
        ids = [str(item).strip() for item in planned if str(item).strip()]
        if ids:
            return ids
    path = out_dir / "figures.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    charts = payload.get("charts") if isinstance(payload, dict) else None
    if not isinstance(charts, list):
        return []
    return [
        str(chart.get("id")).strip()
        for chart in charts
        if isinstance(chart, dict) and str(chart.get("id") or "").strip()
    ]


def _retitle(run_id: str, out_dir: Path, title: str) -> str:
    if any(out_dir.glob("*.tex")):
        from case3.heading_edit import HeadingEditError, edit_title_in_run

        try:
            edit_title_in_run(out_dir, text=title, formats={"pdf", "docx"})
        except HeadingEditError as exc:
            return str(exc)
        return f"Заголовок отчёта теперь «{title}»."
    return _retitle_slide(run_id, out_dir, title)


def _retitle_slide(run_id: str, out_dir: Path, title: str, index: int = 1) -> str:
    from fastapi import HTTPException

    from case3.api_slides import _enqueue_deck_rebuild, _load_deck_for_patch

    try:
        base, ir_path = _load_deck_for_patch(run_id, out_dir)
    except HTTPException as exc:
        return str(exc.detail)
    slides = base.get("slides") if isinstance(base, dict) else None
    if not isinstance(slides, list) or not slides:
        return "В этой презентации нет слайда, чей заголовок менять."
    place = index if index else 1
    if place < 1 or place > len(slides) or not isinstance(slides[place - 1], dict):
        return f"Слайда {place} нет. Сейчас их {len(slides)}."
    slides[place - 1]["title"] = title
    _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        base,
        undo_kind="slides",
        undo_target=str(slides[place - 1].get("id") or "*"),
    )
    which = "первого слайда" if place == 1 else f"слайда {place}"
    return f"Заголовок {which} теперь «{title}»."


def _history(out_dir: Path, *, undo: bool) -> str:
    from case3.run_undo import UndoError, apply_redo, apply_undo

    try:
        (apply_undo if undo else apply_redo)(out_dir, rebuild=False)
    except UndoError as exc:
        return str(exc)
    return "Отменил последнюю правку." if undo else "Вернул последнюю правку."


def _recolor_deck(run_id: str, out_dir: Path, pack: str) -> str:
    from case3.api_slides import _kick_slides_thread, try_claim_slides_start
    from case3.chat_act import PACK_LABELS

    logs = out_dir.parent.parent / "logs" / run_id
    claimed, _meta = try_claim_slides_start(
        run_id,
        out_dir=out_dir,
        logs_dir=logs if logs.is_dir() else None,
        theme_pack=pack,
        kick_source="chat",
    )
    label = PACK_LABELS.get(pack, pack)
    if not claimed:
        return f"Презентация уже собирается. Стиль {label} применю, когда она освободится."
    _kick_slides_thread(run_id)
    return f"Перекрашиваю презентацию в {label}. Текст слайдов тот же."


def _rewrite(out_dir: Path, text: str, act: Any) -> str:
    from case3.chat_act import parse_rewrite, section_target
    from case3.chat_turn import draft_section
    from case3.paragraph_edit import ParagraphEditError, edit_paragraph_in_run

    parsed = parse_rewrite(text)
    texs = sorted(out_dir.glob("*.tex"))
    titles = _heading_titles(texs[0].read_text(encoding="utf-8")) if texs else []
    if parsed:
        name, body = parsed
    else:
        name = str(getattr(act, "section", "") or "") or section_target(text)
        body = ""
        if not name and str(getattr(act, "brief", "") or "") == "prettier":
            name = _intro_title(titles)
    if not name:
        if titles:
            shown = ", ".join(titles[:8])
            return f"Какой раздел переделать? Сейчас в отчёте: {shown}."
        return "Какой раздел переделать? Напиши название, например «переделай введение»."
    if not texs:
        return "В этом чате нет текста отчёта, раздел править негде."
    tex = texs[0].read_text(encoding="utf-8")
    index = _paragraph_after(tex, name)
    if index is None:
        shown = ", ".join(titles[:8]) if titles else "разделов не вижу"
        return f"Раздела «{name}» нет. Есть: {shown}."
    if not parsed:
        body = draft_section(
            section=name,
            current=_paragraph_text(tex, index),
            source=_source_text(out_dir),
            brief=str(getattr(act, "brief", "") or "prettier"),
        )
        if not body:
            return (
                f"Не переписал «{name}»: черновик вышел пустым "
                "или добавил число, которого нет в документах."
            )
    try:
        edit_paragraph_in_run(out_dir, index, text=body, formats={"pdf", "docx"})
    except ParagraphEditError as exc:
        return str(exc)
    if parsed:
        return f"Переписал раздел «{name}» в текущем отчёте."
    return f"Переписал раздел «{name}» по документам. Новых чисел нет."


def _intro_title(titles: list[str]) -> str:
    for title in titles:
        if "введен" in title.casefold():
            return title
    return titles[0] if titles else ""


def _paragraph_text(tex: str, index: int) -> str:
    from case3.tex_preview import find_paragraph_spans

    spans = find_paragraph_spans(tex)
    if index < 1 or index > len(spans):
        return ""
    start, end = spans[index - 1]
    return tex[start:end].strip()


def _source_text(out_dir: Path) -> str:
    meta = _read(out_dir)
    raw = str(meta.get("source") or "")
    path = Path(raw) if raw else out_dir / "source.txt"
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return ""


def _heading_titles(tex: str) -> list[str]:
    import re

    from case3.tex_preview import find_heading_spans

    titles: list[str] = []
    for start, end in find_heading_spans(tex):
        match = re.search(r"\{([^{}]*)\}", tex[start:end])
        if match and match.group(1).strip():
            titles.append(match.group(1).strip())
    return titles


def _paragraph_after(tex: str, name: str) -> int | None:
    from case3.tex_preview import find_heading_spans, find_paragraph_spans

    titles = _heading_titles(tex)
    want = name.casefold()
    hits = [i for i, title in enumerate(titles) if want in title.casefold() or title.casefold() in want]
    if len(hits) != 1:
        return None
    headings = find_heading_spans(tex)
    start = headings[hits[0]][1]
    end = headings[hits[0] + 1][0] if hits[0] + 1 < len(headings) else len(tex)
    for index, (p0, _p1) in enumerate(find_paragraph_spans(tex), start=1):
        if start <= p0 < end:
            return index
    return None


def _recolor_charts(out_dir: Path, palette: str) -> str:
    from case3.chart_edit import ChartEditError, recolor_all_charts_in_run
    from case3.chat_act import PALETTE_LABELS

    label = PALETTE_LABELS.get(palette, palette)
    try:
        recolor_all_charts_in_run(out_dir, palette, formats=set())
    except ChartEditError as exc:
        return str(exc)
    return f"Перекрасил графики в {label}."
