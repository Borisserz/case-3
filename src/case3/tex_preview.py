"""Parse final XeLaTeX into a Liber-friendly chat preview (blocks JSON)."""

from __future__ import annotations

import html as html_lib
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
_PAGE_BREAK = re.compile(r"\\(?:newpage|clearpage|pagebreak)\b")
_LABEL = re.compile(r"\\label\{[^}]*\}")


def estimate_figure_pdf_pages(tex: str) -> dict[str, int]:
    """Map figure id → 1-based PDF page guess from TeX page breaks.

    Counts ``\\newpage`` / ``\\clearpage`` / ``\\pagebreak`` before each
    ``\\includegraphics``. Same-page figures share a page number.
    """
    body = tex or ""
    m_begin = _BEGIN_DOC.search(body)
    m_end = _END_DOC.search(body)
    if m_begin:
        body = body[m_begin.end() :]
    if m_end:
        # end may still be relative to original; re-search on sliced body
        m_end2 = _END_DOC.search(body)
        if m_end2:
            body = body[: m_end2.start()]

    page = 1
    hints: dict[str, int] = {}
    events: list[tuple[int, str, str]] = []
    for m in _PAGE_BREAK.finditer(body):
        events.append((m.start(), "break", ""))
    for m in _INCLUDEGRAPHICS.finditer(body):
        events.append((m.start(), "fig", m.group(1)))
    events.sort(key=lambda t: t[0])
    for _pos, kind, fid in events:
        if kind == "break":
            page += 1
        elif fid and fid not in hints:
            hints[fid] = page
    return hints
_LIST_ENV = re.compile(
    r"\\begin\{(itemize|enumerate)\}([\s\S]*?)\\end\{\1\}",
    re.I,
)
_ITEM = re.compile(r"\\item\b", re.I)
_INLINE_EMPH = re.compile(
    r"\\(textbf|textit|emph|texttt)\{([^{}]*)\}",
)


def _plain_unescape(text: str) -> str:
    """Strip TeX to plain text (no HTML)."""
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
    t = re.sub(r"\{\s*,\s*\}", ",", t)
    t = re.sub(r"\$([^$]*)\$", r"\1", t)
    t = re.sub(r"\\(?:textbf|textit|emph|texttt)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _unescape_tex(text: str) -> str:
    """Back-compat alias used by tables/captions — plain text."""
    return _plain_unescape(text)


def _inline_to_html(tex_fragment: str) -> str:
    """Convert a TeX prose fragment to safe HTML with strong/em/code."""
    t = tex_fragment or ""
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
    t = re.sub(r"\{\s*,\s*\}", ",", t)
    t = re.sub(r"\$([^$]*)\$", r"\1", t)

    # Protect emphasis spans, escape the rest, then restore tags.
    slots: list[tuple[str, str]] = []

    def _stash(m: re.Match[str]) -> str:
        cmd, inner = m.group(1), m.group(2)
        plain = _plain_unescape(inner)
        esc = html_lib.escape(plain)
        if cmd == "textbf":
            tag = f"<strong>{esc}</strong>"
        elif cmd in ("textit", "emph"):
            tag = f"<em>{esc}</em>"
        else:
            tag = f"<code>{esc}</code>"
        key = f"@@H{len(slots)}@@"
        slots.append((key, tag))
        return key

    t = _INLINE_EMPH.sub(_stash, t)
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    out = html_lib.escape(t)
    for key, tag in slots:
        out = out.replace(key, tag)
    return out


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
        cells = []
        # Split on bare & only — keep \& inside a cell
        for c in re.split(r"(?<!\\)&", s):
            plain = _plain_unescape(c).strip()
            # Liber table edit: empty cells serialize as TeX ~
            if plain == "~":
                plain = ""
            cells.append(plain)
        if any(cells):
            rows.append(cells)
    return rows


def _parse_table_block(block: str) -> dict[str, Any] | None:
    cap_m = _CAPTION.search(block)
    caption = _plain_unescape(cap_m.group(1)) if cap_m else ""
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
    caption = _plain_unescape(cap_m.group(1)) if cap_m else ""
    kind = "chart" if fid.startswith("cht_") else "image"
    return {
        "type": "figure",
        "id": fid,
        "kind": kind,
        "caption": caption,
    }


def _parse_list_block(env: str, inner: str) -> dict[str, Any] | None:
    parts = _ITEM.split(inner or "")
    items: list[dict[str, str]] = []
    for part in parts[1:]:  # before first \item is junk
        raw = part.strip()
        if not raw:
            continue
        # Stop at nested begin if any leaked
        raw = re.split(r"\\begin\{", raw, maxsplit=1)[0]
        text = _plain_unescape(raw.replace("\n", " "))
        if len(text) < 1:
            continue
        items.append({"text": text, "html": _inline_to_html(raw.replace("\n", " "))})
    if not items:
        return None
    return {
        "type": "list",
        "ordered": env.lower() == "enumerate",
        "items": items,
    }


def tex_to_preview_blocks(tex: str) -> dict[str, Any]:
    """Extract title + ordered content blocks from a full document."""
    title_m = _TITLE.search(tex or "")
    title = _plain_unescape(title_m.group(1)) if title_m else ""
    body = _body(tex)
    blocks: list[dict[str, Any]] = []

    # Walk by finding next structural token
    pos = 0
    token = re.compile(
        r"(\\section\*?\{[^{}]*\}|"
        r"\\subsection\*?\{[^{}]*\}|"
        r"\\begin\{table\}|"
        r"\\begin\{figure\}|"
        r"\\begin\{itemize\}|"
        r"\\begin\{enumerate\})",
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
                level = 2 if "subsection" in tok else 1
                blocks.append(
                    {
                        "type": "heading",
                        "level": level,
                        "text": _plain_unescape(sm.group(2)),
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

        if tok.startswith(r"\begin{itemize}") or tok.startswith(r"\begin{enumerate}"):
            env = "itemize" if "itemize" in tok else "enumerate"
            em = re.search(rf"\\end\{{{env}\}}", body[m.start() :], re.S | re.I)
            if not em:
                pos = m.end()
                continue
            end = m.start() + em.end()
            block = body[m.start() : end]
            lm = _LIST_ENV.search(block)
            if lm:
                lst = _parse_list_block(lm.group(1), lm.group(2))
                if lst:
                    blocks.append(lst)
            pos = end
            continue

        pos = m.end()

    return {"title": title, "blocks": blocks}


def _flush_paragraphs(chunk: str, blocks: list[dict[str, Any]]) -> None:
    # Drop leftover labels / empty commands
    text = _LABEL.sub("", chunk)
    text = re.sub(r"\\(?:centering|hfill|vfill|noindent)\s*", "", text)
    # Strip list envs if any leaked into prose (safety)
    text = _LIST_ENV.sub("", text)
    # Split on blank lines
    for part in re.split(r"\n\s*\n", text):
        raw = part.replace("\n", " ")
        cleaned = _plain_unescape(raw)
        if len(cleaned) < 2:
            continue
        if cleaned.startswith("%"):
            continue
        html = _inline_to_html(raw)
        blocks.append({"type": "paragraph", "text": cleaned, "html": html})


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
    palette_by_id: dict[str, str] = {}
    for item in fj.get("charts") or []:
        if isinstance(item, dict) and item.get("id"):
            fid0 = str(item["id"])
            cap = str(item.get("caption") or "").strip()
            if cap:
                cap_by_id[fid0] = cap
            ctype = str(item.get("type") or "").strip()
            if ctype:
                type_by_id[fid0] = ctype
            pal = str(item.get("palette") or "").strip()
            if pal:
                palette_by_id[fid0] = pal
    for item in fj.get("figures") or []:
        if isinstance(item, dict) and item.get("id"):
            cap = str(item.get("caption") or "").strip()
            if cap:
                cap_by_id[str(item["id"])] = cap

    data = tex_to_preview_blocks(tex)
    page_hints = estimate_figure_pdf_pages(tex)
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
        if fid in page_hints:
            entry["pdfPage"] = page_hints[fid]
        if fid in type_by_id:
            entry["chartType"] = type_by_id[fid]
        if fid in palette_by_id:
            entry["palette"] = palette_by_id[fid]
        # Optional Mary-style card meta from charts[] (Source-derived only).
        for item in fj.get("charts") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("id") or "") != fid:
                continue
            insight = str(item.get("insight") or "").strip()
            if insight:
                entry["insight"] = insight
            hl = item.get("highlights")
            if isinstance(hl, list) and hl:
                entry["highlights"] = hl
            if not entry.get("palette"):
                pal = str(item.get("palette") or "").strip()
                if pal:
                    entry["palette"] = pal
            break
        if st.get("ok") and fid:
            entry["url"] = f"/api/runs/{run_id}/figures/{fid}.png"
        out_blocks.append(entry)
    return {"title": data["title"], "blocks": out_blocks}
