"""Post-pandoc: replace cht_* PNG drawings with native Word OOXML charts."""

from __future__ import annotations

import json
import logging
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from pptx.dml.color import RGBColor

from case3.slides_chart_data import (
    NATIVE_CHART_TYPES,
    attach_series_ir,
    normalize_series_ir,
    series_from_figures_json,
)
from case3.slides_pptx_charts import add_native_chart

log = logging.getLogger("case3.docx_charts")

_CHT_IN_DESCR = re.compile(
    r"(?:docx_media/)?figures/(cht_\d+)\.png|(cht_\d+)\.png",
    re.I,
)
_DRAWING = re.compile(r"<w:drawing>.*?</w:drawing>", re.S)
_RID = re.compile(r'Id="(rId\d+)"')
_EMBED = re.compile(r'r:embed="(rId\d+)"')


def _hex_to_rgb(hx: str) -> RGBColor | None:
    h = (hx or "").strip().lstrip("#")
    if len(h) != 6:
        return None
    try:
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return None


def _series_colors(hexes: list[str] | None) -> list[RGBColor]:
    out: list[RGBColor] = []
    for hx in hexes or []:
        rgb = _hex_to_rgb(str(hx))
        if rgb is not None:
            out.append(rgb)
    if not out:
        out = [RGBColor(0x2E, 0x42, 0x08), RGBColor(0x4F, 0x6B, 0x14)]
    return out


def _load_figures(
    *,
    figures: dict[str, Any] | None,
    figures_path: Path | None,
) -> dict[str, Any]:
    if isinstance(figures, dict):
        return figures
    if figures_path and Path(figures_path).is_file():
        try:
            data = json.loads(Path(figures_path).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _chart_series_for_id(figures: dict[str, Any], cid: str) -> dict[str, Any] | None:
    ir = series_from_figures_json(figures, cid)
    if ir:
        return ir
    for ch in figures.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("id") or "") != cid:
            continue
        attach_series_ir(ch)
        return normalize_series_ir(ch.get("series"), default_type=str(ch.get("type") or "bar"))
    return None


def _build_chart_package(
    series_ir: dict[str, Any],
    *,
    series_hexes: list[str] | None,
) -> tuple[bytes, bytes, str]:
    """Return (chart_xml, xlsx_bytes, embedding_filename) via python-pptx."""
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    ok = add_native_chart(
        slide,
        series_ir,
        left=Inches(0.5),
        top=Inches(0.5),
        width=Inches(9),
        height=Inches(5),
        series_colors=_series_colors(series_hexes),
    )
    if not ok:
        raise RuntimeError("add_native_chart failed")

    with tempfile.TemporaryDirectory() as td:
        pptx_path = Path(td) / "c.pptx"
        prs.save(str(pptx_path))
        with zipfile.ZipFile(pptx_path) as zf:
            chart_xml = zf.read("ppt/charts/chart1.xml")
            rels = zf.read("ppt/charts/_rels/chart1.xml.rels").decode("utf-8")
            # Find embedding target
            m = re.search(r'Target="([^"]+)"', rels)
            if not m:
                raise RuntimeError("chart rels missing embedding")
            emb_target = m.group(1).lstrip("/")
            # ppt relative: ../embeddings/Foo.xlsx → ppt/embeddings/Foo.xlsx
            if emb_target.startswith("../"):
                emb_path = "ppt/" + emb_target[3:]
            else:
                emb_path = emb_target
            xlsx = zf.read(emb_path)
            emb_name = Path(emb_path).name
    return chart_xml, xlsx, emb_name


def _next_rid(rels_xml: str) -> int:
    nums = [int(m.group(1)) for m in re.finditer(r'Id="rId(\d+)"', rels_xml)]
    return (max(nums) if nums else 0) + 1


def _chart_drawing_xml(*, rid: str, extent_cx: str, extent_cy: str, doc_pr_id: str) -> str:
    return (
        f"<w:drawing>"
        f"<wp:inline distT=\"0\" distB=\"0\" distL=\"0\" distR=\"0\">"
        f"<wp:extent cx=\"{extent_cx}\" cy=\"{extent_cy}\"/>"
        f"<wp:effectExtent l=\"0\" t=\"0\" r=\"0\" b=\"0\"/>"
        f"<wp:docPr id=\"{doc_pr_id}\" name=\"Chart\"/>"
        f"<wp:cNvGraphicFramePr/>"
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
        f'<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
        f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        f'r:id="{rid}"/>'
        f"</a:graphicData>"
        f"</a:graphic>"
        f"</wp:inline>"
        f"</w:drawing>"
    )


def _extract_extent(drawing: str) -> tuple[str, str]:
    m = re.search(r'<wp:extent\s+cx="(\d+)"\s+cy="(\d+)"', drawing)
    if m:
        return m.group(1), m.group(2)
    return "5486400", "3200400"


def _extract_docpr_id(drawing: str) -> str:
    m = re.search(r'<wp:docPr[^>]*\bid="(\d+)"', drawing)
    return m.group(1) if m else "100"


def _match_cht_id(drawing: str) -> str | None:
    for m in _CHT_IN_DESCR.finditer(drawing):
        return m.group(1) or m.group(2)
    return None


def _suppress_chart_title(chart_xml: bytes) -> bytes:
    """Hide OOXML auto-title so pandoc caption is the only title (no duplicate)."""
    text = chart_xml.decode("utf-8")
    text = re.sub(
        r"<c:autoTitleDeleted\b[^/]*/>",
        '<c:autoTitleDeleted val="1"/>',
        text,
        count=1,
    )
    text = re.sub(r"<c:title>.*?</c:title>", "", text, count=1, flags=re.S)
    return text.encode("utf-8")


def _rels_target_for_rid(rels_xml: str, rid: str) -> str | None:
    m = re.search(
        rf'<Relationship\b[^>]*\bId="{re.escape(rid)}"[^>]*\bTarget="([^"]+)"',
        rels_xml,
    )
    if m:
        return m.group(1)
    m = re.search(
        rf'<Relationship\b[^>]*\bTarget="([^"]+)"[^>]*\bId="{re.escape(rid)}"',
        rels_xml,
    )
    return m.group(1) if m else None


def _drop_relationship(rels_xml: str, rid: str) -> str:
    return re.sub(
        rf'<Relationship\b[^>]*\bId="{re.escape(rid)}"[^>]*/>',
        "",
        rels_xml,
        count=1,
    )


def replace_docx_native_charts(
    docx_path: Path | str,
    *,
    figures: dict[str, Any] | None = None,
    figures_path: Path | str | None = None,
    series_hexes: list[str] | None = None,
) -> list[str]:
    """Replace eligible cht_* picture drawings with native charts. Return replaced ids."""
    path = Path(docx_path)
    fj = _load_figures(
        figures=figures,
        figures_path=Path(figures_path) if figures_path else None,
    )
    # Ensure series IR present
    for ch in fj.get("charts") or []:
        if isinstance(ch, dict):
            attach_series_ir(ch)

    with zipfile.ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        if "word/document.xml" not in names or "word/_rels/document.xml.rels" not in names:
            return []
        document = zf.read("word/document.xml").decode("utf-8")
        rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
        content_types = zf.read("[Content_Types].xml").decode("utf-8")
        other_files = {
            n: zf.read(n)
            for n in names
            if n
            not in (
                "word/document.xml",
                "word/_rels/document.xml.rels",
                "[Content_Types].xml",
            )
        }

    drawings = list(_DRAWING.finditer(document))
    if not drawings:
        return []

    replaced: list[str] = []
    new_parts: dict[str, bytes] = {}
    drop_media: set[str] = set()
    rid_n = _next_rid(rels)
    chart_n = 1
    # Existing chart overrides count
    while f"word/charts/chart{chart_n}.xml" in names or f"word/charts/chart{chart_n}.xml" in new_parts:
        chart_n += 1

    # Process from end so string offsets stay valid
    for match in reversed(drawings):
        drawing = match.group(0)
        cid = _match_cht_id(drawing)
        if not cid:
            continue
        series_ir = _chart_series_for_id(fj, cid)
        if not series_ir:
            continue
        ctype = str(series_ir.get("type") or "").lower()
        if ctype not in NATIVE_CHART_TYPES:
            continue
        try:
            chart_xml, xlsx, emb_name = _build_chart_package(
                series_ir, series_hexes=series_hexes
            )
            chart_xml = _suppress_chart_title(chart_xml)
        except Exception as exc:  # noqa: BLE001
            log.warning("docx native chart build failed %s: %s", cid, exc)
            continue

        # Drop old PNG relationship + media part for this drawing.
        emb = _EMBED.search(drawing)
        if emb:
            old_rid = emb.group(1)
            target = _rels_target_for_rid(rels, old_rid)
            rels = _drop_relationship(rels, old_rid)
            if target:
                media_part = (
                    target
                    if target.startswith("word/")
                    else f"word/{target.lstrip('./')}"
                )
                drop_media.add(media_part)
                # Also common form word/media/...
                if not media_part.startswith("word/"):
                    drop_media.add(f"word/{media_part}")

        chart_part = f"word/charts/chart{chart_n}.xml"
        emb_part = f"word/embeddings/Liber_{cid}_{emb_name}"
        rels_part = f"word/charts/_rels/chart{chart_n}.xml.rels"
        chart_rid = f"rId{rid_n}"
        rid_n += 1

        # Chart → embedding rel (Word path)
        emb_rel = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/package" '
            f'Target="../embeddings/{Path(emb_part).name}"/>'
            "</Relationships>"
        )
        new_parts[chart_part] = chart_xml
        new_parts[emb_part] = xlsx
        new_parts[rels_part] = emb_rel.encode("utf-8")

        # document → chart relationship
        rels = rels.replace(
            "</Relationships>",
            f'<Relationship Id="{chart_rid}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" '
            f'Target="charts/chart{chart_n}.xml"/>'
            "</Relationships>",
            1,
        )

        # Content types
        if 'Extension="xlsx"' not in content_types:
            # Insert Default for xlsx after <Types ...>
            content_types = re.sub(
                r"(<Types[^>]*>)",
                r'\1<Default Extension="xlsx" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>',
                content_types,
                count=1,
            )
        override = (
            f'<Override PartName="/{chart_part}" '
            f'ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
        )
        if override not in content_types:
            content_types = content_types.replace(
                "</Types>",
                override + "</Types>",
                1,
            )

        cx, cy = _extract_extent(drawing)
        doc_pr_id = _extract_docpr_id(drawing)
        new_drawing = _chart_drawing_xml(
            rid=chart_rid, extent_cx=cx, extent_cy=cy, doc_pr_id=doc_pr_id
        )
        document = document[: match.start()] + new_drawing + document[match.end() :]
        replaced.append(cid)
        chart_n += 1
        log.info("docx native chart %s → %s", cid, chart_part)

    if not replaced:
        return []

    # Rewrite zip (omit dropped media)
    out_buf_files = {
        n: data for n, data in other_files.items() if n not in drop_media
    }
    for media_part in drop_media:
        if media_part in out_buf_files:
            del out_buf_files[media_part]
        log.info("docx dropped replaced PNG %s", media_part)
    out_buf_files["word/document.xml"] = document.encode("utf-8")
    out_buf_files["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    out_buf_files["[Content_Types].xml"] = content_types.encode("utf-8")
    out_buf_files.update(new_parts)

    tmp = path.with_suffix(path.suffix + ".native.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(out_buf_files.items()):
            zf.writestr(name, data)
    tmp.replace(path)
    return list(reversed(replaced))  # chronological order


def try_replace_docx_native_charts(
    docx_path: Path | str,
    *,
    figures: dict[str, Any] | None = None,
    figures_path: Path | str | None = None,
    series_hexes: list[str] | None = None,
) -> list[str]:
    """Best-effort; never raise into render."""
    try:
        return replace_docx_native_charts(
            docx_path,
            figures=figures,
            figures_path=figures_path,
            series_hexes=series_hexes,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("docx native charts skipped: %s", exc)
        return []


def palette_hexes_for_report(palette_id: str | None) -> list[str]:
    """Report palette → hex ladder for native charts."""
    from case3.chart_style import _PALETTES, normalize_palette_id

    pid = normalize_palette_id(palette_id or "atelier")
    if pid in _PALETTES:
        p = _PALETTES[pid]
        return [str(p["primary"]), *[str(a) for a in p["accents"]]]
    return ["#2E4208", "#4F6B14", "#7A9A28", "#B8D45A", "#D5DEC0"]
