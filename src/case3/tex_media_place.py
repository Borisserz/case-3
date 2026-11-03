"""Scatter trailing gallery dumps (Визуализация / Иллюстрации) into prose sections."""

from __future__ import annotations

import re
from typing import Any

_GALLERY_SECTION = re.compile(
    r"\\section\*?\{("
    r"Визуализация[^}]*|Иллюстрации[^}]*|Графики[^}]*|Рисунки[^}]*|"
    r"Figures?[^}]*|Charts?[^}]*|Visuali[sz]ation[^}]*"
    r")\}",
    re.I,
)
_SECTION_OPEN = re.compile(
    r"\\((?:sub)*section)\*?\{([^{}]*)\}"
)
_SLOT = re.compile(
    r"(?m)^[ \t]*%CASE3_(FIG|CHART):([a-z][a-z0-9_]{0,31})%[^\n]*\r?\n?"
)
_TOKEN = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{3,}")


def _tokens(text: str) -> set[str]:
    raw = {t.lower() for t in _TOKEN.findall(text or "")}
    # Light stem: keep prefixes so «промышленности» ↔ «Промышленность».
    out: set[str] = set(raw)
    for t in raw:
        if len(t) >= 6:
            out.add(t[:6])
        if len(t) >= 8:
            out.add(t[:8])
    return out


def _score(hint: str, section_title: str, section_body: str) -> float:
    ht = _tokens(hint)
    if not ht:
        return 0.0
    st = _tokens(section_title) | _tokens(section_body[:600])
    if not st:
        return 0.0
    overlap = ht & st
    # Title matches weigh more than body prose.
    title_hit = len(ht & _tokens(section_title))
    return (len(overlap) + 2.0 * title_hit) / max(len(ht), 1)


def redistribute_gallery_slots(
    tex: str,
    *,
    figures: list[dict[str, Any]] | None = None,
    charts: list[dict[str, Any]] | None = None,
) -> str:
    """Move slots out of trailing gallery sections into matching prose sections.

    Win desk 081536: model wrote full prose with 0 slots, then dumped all
    ``%CASE3_*`` under ``\\section{Визуализация данных}`` / ``Иллюстрации``.
    """
    if not tex or not _GALLERY_SECTION.search(tex):
        return tex

    mdoc = re.search(
        r"(\\begin\{document\})([\s\S]*?)(\\end\{document\})",
        tex,
    )
    if not mdoc:
        return tex
    begin, body, end = mdoc.group(1), mdoc.group(2), mdoc.group(3)

    # First gallery section → cut point (keep only prose before it).
    gm = _GALLERY_SECTION.search(body)
    if not gm:
        return tex
    prose = body[: gm.start()]
    gallery = body[gm.start() :]

    slots: list[tuple[str, str, str]] = []  # kind, id, hint
    # Prefer subsection title immediately above each slot as hint.
    gal_lines = gallery.splitlines(keepends=True)
    last_sub = ""
    for ln in gal_lines:
        sm = re.match(r"\\subsection\*?\{([^{}]*)\}", ln.strip())
        if sm:
            last_sub = sm.group(1)
            continue
        sm2 = _SLOT.match(ln)
        if sm2:
            kind, mid = sm2.group(1).upper(), sm2.group(2)
            slots.append((kind, mid, last_sub))

    if not slots:
        # Gallery without slots — leave alone (might be real content).
        return tex

    cap_by_id: dict[str, str] = {}
    for f in figures or []:
        if isinstance(f, dict) and f.get("id"):
            cap_by_id[str(f["id"])] = str(f.get("caption") or "")
    for c in charts or []:
        if isinstance(c, dict) and c.get("id"):
            cap_by_id[str(c["id"])] = str(c.get("caption") or "")

    # Split prose into section chunks (keep preamble bits before first section).
    parts: list[dict[str, str]] = []
    idx = 0
    for m in _SECTION_OPEN.finditer(prose):
        if m.start() > idx:
            if not parts:
                parts.append(
                    {"title": "", "cmd": "", "body": prose[idx : m.start()]}
                )
            else:
                parts[-1]["body"] += prose[idx : m.start()]
        parts.append(
            {
                "title": m.group(2),
                "cmd": m.group(0),
                "body": "",
            }
        )
        idx = m.end()
    if not parts:
        parts.append({"title": "", "cmd": "", "body": prose})
    else:
        parts[-1]["body"] += prose[idx:]

    content_idxs = [i for i, p in enumerate(parts) if p["title"]]
    if not content_idxs:
        # Nowhere to put — append before end as last resort (no gallery wrapper).
        inject = "".join(
            f"%CASE3_{k}:{i}%\n" for k, i, _ in slots
        )
        new_body = prose.rstrip() + "\n\n" + inject + "\n"
        return tex[: mdoc.start()] + begin + new_body + end + tex[mdoc.end() :]

    used: set[int] = set()
    placements: list[tuple[int, str, str]] = []  # part_idx, kind, id
    for kind, mid, hint in slots:
        caption = cap_by_id.get(mid, "")
        score_hint = f"{hint} {caption}".strip()
        best_i = content_idxs[0]
        best_s = -1.0
        for i in content_idxs:
            if i in used and len(content_idxs) > 1:
                # soft prefer unused, but still allow if score much higher
                pass
            s = _score(score_hint, parts[i]["title"], parts[i]["body"])
            if i in used:
                s -= 0.15
            if s > best_s:
                best_s = s
                best_i = i
        used.add(best_i)
        placements.append((best_i, kind, mid))

    # Insert after first paragraph of each target (blank-line separated).
    by_part: dict[int, list[str]] = {}
    for i, kind, mid in placements:
        by_part.setdefault(i, []).append(f"%CASE3_{kind}:{mid}%")

    for i, lines in by_part.items():
        body = parts[i]["body"]
        # After first blank line following some text, else at end of chunk.
        insert_at = None
        seen_text = False
        acc = 0
        for ln in body.splitlines(keepends=True):
            acc += len(ln)
            if ln.strip():
                seen_text = True
            elif seen_text:
                insert_at = acc
                break
        block = "\n" + "\n".join(lines) + "\n\n"
        if insert_at is None:
            parts[i]["body"] = body.rstrip() + "\n" + block
        else:
            parts[i]["body"] = body[:insert_at] + block + body[insert_at:]

    new_prose = []
    for p in parts:
        if p["cmd"]:
            new_prose.append(p["cmd"] + "\n")
        new_prose.append(p["body"])
    new_body = "".join(new_prose)
    if not new_body.endswith("\n"):
        new_body += "\n"
    return tex[: mdoc.start()] + begin + new_body + end + tex[mdoc.end() :]
