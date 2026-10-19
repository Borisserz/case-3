"""Parse final XeLaTeX into a Liber-friendly chat preview (blocks JSON)."""

from __future__ import annotations

import re
from typing import Any

_BEGIN_DOC = re.compile(r"\\begin\{document\}", re.I)
_END_DOC = re.compile(r"\\end\{document\}", re.I)
_TITLE = re.compile(r"\\title\{([^{}]*)\}")
_SECTION = re.compile(r"\\(sub)*section\*?\{([^{}]*)\}")
_TABLE_ENV = re.compile(
    r"\\begin\{table\}.*?\\end\{table\}",
    re.S,
)
_TABULAR = re.compile(
    r"\\begin\{tabularx\}\{[^}]+\}\{[^}]+\}([\s\S]*?)\\end\{tabularx\}"
    r"|\\begin\{tabular\}\{[^}]+\}([\s\S]*?)\\end\{tabular\}"
)
_CAPTION = re.compile(r"\\caption\{([^{}]*)\}")
_FIGURE_ENV = re.compile(
    r"\\begin\{figure\}.*?\\end\{figure\}",
    re.S,
)
_INCLUDEGRAPHICS = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{(?:figures/)?([a-zA-Z0-9_]+)\.png\}"
)
_LABEL = re.compile(r"\\label\{[^}]*\}")


def _unescape_tex(text: str) -> str:
    t = text or ""
    t = t.replace(r"\%", "%")
    t = t.replace(r"\&", "&")
    t = t.replace(r"\$", "$")
    t = t.replace(r"\#", "#")
    t = t.replace(r"\_", "_")
    t = t.replace(r"\{", "{")
    t = t.replace(r"\}", "}")
    t = t.replace(r"\,", " ")
    t = t.replace(r"\ ", " ")
    t = t.replace("---", "—")
    t = t.replace("--", "–")
    t = re.sub(r"\{\s*,\s*\}", ",", t)  # 7{,}7 → 7,7
    t = re.sub(r"\$([^$]*)\$", r"\1", t)
    t = re.sub(r"\\(?:textbf|textit|emph|texttt)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _body(tex: str) -> str:
    m0 = _BEGIN_DOC.search(tex or "")
    if not m0:
        return tex or ""
    start = m0.end()
    m1 = _END_DOC.search(tex, start)
    end = m1.start() if m1 else len(tex)
    body = tex[start:end]
    body = re.sub(r"\\maketitle\s*", "", body)
    body = re.sub(r"\\tableofcontents\s*", "", body)
    return body


def _split_rows(tabular_body: str) -> list[list[str]]:
    raw = tabular_body or ""
    raw = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)\s*", "", raw)
    chunks = re.split(r"\\\\", raw)
    rows: list[list[str]] = []
    for chunk in chunks:
        s = chunk.strip()
        if not s or "&" not in s and not s:
            continue
        if "&" not in s and not re.search(r"[A-Za-zА-Яа-я0-9]", s):
            continue
        cells = [_unescape_tex(c) for c in s.split("&")]
        if any(cells):
            rows.append(cells)
    return rows


def _parse_table_block(block: str) -> dict[str, Any] | None:
    cap_m = _CAPTION.search(block)
    caption = _unescape_tex(cap_m.group(1)) if cap_m else ""
    tab_m = _TABULAR.search(block)
    if not tab_m:
        return None
    body = tab_m.group(1) if tab_m.group(1) is not None else tab_m.group(2)
    rows = _split_rows(body or "")
    if not rows:
        return None
    headers = rows[0]
    data = rows[1:] if len(rows) > 1 else []
    return {
        "type": "table",
        "caption": caption,
        "headers": headers,
        "rows": data,
    }


def _parse_figure_block(block: str) -> dict[str, Any] | None:
    img = _INCLUDEGRAPHICS.search(block)
    if not img:
        return None
    fid = img.group(1)
    cap_m = _CAPTION.search(block)
    caption = _unescape_tex(cap_m.group(1)) if cap_m else ""
    kind = "chart" if fid.startswith("cht_") else "image"
    return {
        "type": "figure",
        "id": fid,
        "kind": kind,
        "caption": caption,
    }


def tex_to_preview_blocks(tex: str) -> dict[str, Any]:
    """Extract title + ordered content blocks from a full document."""
    title_m = _TITLE.search(tex or "")
    title = _unescape_tex(title_m.group(1)) if title_m else ""
    body = _body(tex)
    blocks: list[dict[str, Any]] = []

    # Walk by finding next structural token
    pos = 0
    token = re.compile(
        r"(\\section\*?\{[^{}]*\}|"
        r"\\subsection\*?\{[^{}]*\}|"
        r"\\begin\{table\}|"
        r"\\begin\{figure\})",
    )

    while pos < len(body):
        m = token.search(body, pos)
        if not m:
            para = body[pos:].strip()
            if para:
                _flush_paragraphs(para, blocks)
            break

        # prose before token
        if m.start() > pos:
            para = body[pos : m.start()].strip()
            if para:
                _flush_paragraphs(para, blocks)

        tok = m.group(1)
        if tok.startswith(r"\section") or tok.startswith(r"\subsection"):
            sm = _SECTION.match(tok)
            if sm:
                level = 2 if sm.group(1) else 1
                # group(1) is "sub" or None from (sub)* — actually (sub)* means
                # group(1) is last "sub" or None. For \subsection, group(1)='sub'.
                level = 2 if "subsection" in tok else 1
                blocks.append(
                    {
                        "type": "heading",
                        "level": level,
                        "text": _unescape_tex(sm.group(2)),
                    }
                )
            pos = m.end()
            continue

        if tok.startswith(r"\begin{table}"):
            em = re.search(r"\\end\{table\}", body[m.start() :], re.S)
            if not em:
                pos = m.end()
                continue
            end = m.start() + em.end()
            table = _parse_table_block(body[m.start() : end])
            if table:
                blocks.append(table)
            pos = end
            continue

        if tok.startswith(r"\begin{figure}"):
            em = re.search(r"\\end\{figure\}", body[m.start() :], re.S)
            if not em:
                pos = m.end()
                continue
            end = m.start() + em.end()
            fig = _parse_figure_block(body[m.start() : end])
            if fig:
                blocks.append(fig)
            pos = end
            continue

        pos = m.end()

    return {"title": title, "blocks": blocks}


def _flush_paragraphs(chunk: str, blocks: list[dict[str, Any]]) -> None:
    # Drop leftover labels / empty commands
    text = _LABEL.sub("", chunk)
    text = re.sub(r"\\(?:centering|hfill|vfill|noindent)\s*", "", text)
    # Split on blank lines
    for part in re.split(r"\n\s*\n", text):
        cleaned = _unescape_tex(part.replace("\n", " "))
        if len(cleaned) < 2:
            continue
        if cleaned.startswith("%"):
            continue
        blocks.append({"type": "paragraph", "text": cleaned})


def build_report_preview(
    tex: str,
    *,
    run_id: str,
    media_status: dict[str, Any] | None = None,
    figures_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach figure URLs / captions for chat rendering."""
    media = media_status or {}
    fj = figures_json or {}
    cap_by_id: dict[str, str] = {}
    type_by_id: dict[str, str] = {}
    for item in fj.get("charts") or []:
        if isinstance(item, dict) and item.get("id"):
            fid0 = str(item["id"])
            cap = str(item.get("caption") or "").strip()
            if cap:
                cap_by_id[fid0] = cap
            ctype = str(item.get("type") or "").strip()
            if ctype:
                type_by_id[fid0] = ctype
    for item in fj.get("figures") or []:
        if isinstance(item, dict) and item.get("id"):
            cap = str(item.get("caption") or "").strip()
            if cap:
                cap_by_id[str(item["id"])] = cap

    data = tex_to_preview_blocks(tex)
    out_blocks: list[dict[str, Any]] = []
    for b in data["blocks"]:
        if b.get("type") != "figure":
            out_blocks.append(b)
            continue
        fid = str(b.get("id") or "")
        st = media.get(fid) if isinstance(media.get(fid), dict) else {}
        kind = str(st.get("kind") or b.get("kind") or "image")
        if kind == "figure":
            kind = "image"
        caption = str(b.get("caption") or "").strip() or cap_by_id.get(fid, "")
        entry: dict[str, Any] = {
            "type": "figure",
            "id": fid,
            "kind": "chart" if kind == "chart" or fid.startswith("cht_") else "image",
            "caption": caption,
        }
        if fid in type_by_id:
            entry["chartType"] = type_by_id[fid]
        if st.get("ok") and fid:
            entry["url"] = f"/api/runs/{run_id}/figures/{fid}.png"
        out_blocks.append(entry)
    return {"title": data["title"], "blocks": out_blocks}
