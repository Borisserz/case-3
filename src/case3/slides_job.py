"""On-demand Liber deck job: LLM IR → PNG capture → image PPTX + deck PDF."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

from case3.chart_html import sanitize_chart_html
from case3.chart_style import (
    apply_hex_series_to_html,
    apply_pack_category_colors_to_html,
    normalize_palette_id,
)
from case3.charts import render_chart_png
from case3.deck_theme import normalize_pack_id, resolve_deck_theme
from case3.llm_client import LLMClient, LLMConfig, LLMConfigError, LLMError
from case3.run_cancel import RunCancelled, raise_if_cancelled
from case3.run_events import EVENTS
from case3.slides_beat_planner import (
    format_beat_overlay,
    maybe_apply_pack_hint,
    plan_beats,
)
from case3.slides_chart_data import (
    attach_series_ir_to_charts,
    ensure_deck_charts,
    series_from_figures_json,
    series_map_from_figures,
)
from case3.slides_lo import write_deck_pdf
from case3.slides_pptx_native import build_native_pptx
from case3.slides_ir import DeckIrError, parse_deck_ir, scrub_invented_numbers
from case3.slides_media import (
    collect_run_media,
    ensure_diagram_pngs,
    load_figures_json,
    numbers_from_media_json,
)
from case3.slides_render import render_deck_pngs

log = logging.getLogger("case3.slides_job")

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)
_META_WRITE = Callable[[dict[str, Any]], None]


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    cand = here.parents[2]
    if (cand / "Dockerfile").is_file() or (cand / "prompt").is_dir():
        return cand
    return Path.cwd()


def _ids_block(ids: list[str], *, empty: str) -> str:
    return ", ".join(ids) if ids else empty


def _media_catalog_block(out_dir: Path) -> str:
    """Human catalog so LLM titles match real chart/figure/diagram captions."""
    fj = load_figures_json(out_dir)
    lines: list[str] = []
    for ch in fj.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        cid = str(ch.get("id") or "").strip()
        if not cid:
            continue
        cap = str(ch.get("caption") or "").strip() or "(no caption)"
        ctype = str(ch.get("type") or "").strip()
        lines.append(f"- chart {cid} [{ctype}]: {cap}")
    for fig in fj.get("figures") or []:
        if not isinstance(fig, dict):
            continue
        fid = str(fig.get("id") or "").strip()
        if not fid:
            continue
        cap = str(fig.get("caption") or "").strip() or "(no caption)"
        lines.append(f"- figure {fid}: {cap}")
    for dia in fj.get("diagrams") or []:
        if not isinstance(dia, dict):
            continue
        did = str(dia.get("id") or "").strip()
        if not did:
            continue
        title = str(dia.get("title") or dia.get("caption") or "").strip() or "(no title)"
        dtype = str(dia.get("type") or "").strip()
        lines.append(f"- diagram {did} [{dtype}]: {title}")
    return "\n".join(lines) if lines else "(no media catalog)"


def _theme_overlay(theme_pack: str | None) -> str:
    """Optional visual/tone overlay from prompt/themes/slides_{pack}.md."""
    from case3.deck_theme import normalize_pack_id

    pack = normalize_pack_id(theme_pack)
    path = _repo_root() / "prompt" / "themes" / f"slides_{pack}.md"
    if not path.is_file():
        path = _repo_root() / "prompt" / "themes" / "slides_atelier.md"
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def load_slides_system_prompt(
    *,
    palette: str,
    chart_ids: list[str],
    figure_ids: list[str],
    diagram_ids: list[str],
    intent: str,
    source: str,
    media_catalog: str = "",
    theme_pack: str | None = None,
    structure_id: str | None = None,
    beat_overlay: str | None = None,
) -> str:
    from case3.deck_structure import structure_overlay

    path = _repo_root() / "prompt" / "system_slides.md"
    text = path.read_text(encoding="utf-8")
    overlay = _theme_overlay(theme_pack)
    struct = (beat_overlay or "").strip() or structure_overlay(structure_id)
    return (
        text.replace("{{PALETTE}}", palette)
        .replace("{{THEME_OVERLAY}}", overlay)
        .replace("{{STRUCTURE_OVERLAY}}", struct)
        .replace(
            "{{CHART_IDS}}",
            _ids_block(chart_ids, empty="(none — do not use chart_hero / chart_split)"),
        )
        .replace(
            "{{FIGURE_IDS}}",
            _ids_block(figure_ids, empty="(none — no photos)"),
        )
        .replace(
            "{{DIAGRAM_IDS}}",
            _ids_block(diagram_ids, empty="(none — no diagrams)"),
        )
        .replace("{{MEDIA_CATALOG}}", media_catalog or "(no media catalog)")
        .replace("{{INTENT}}", intent or "")
        .replace("{{SOURCE}}", source or "")
    )


def _repair_json_text(blob: str) -> str:
    """Best-effort fixes for common LLM JSON slips."""
    s = blob
    # Trailing commas before } or ]
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    # Smart quotes → plain
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return s


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    # Find outermost {…}
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise DeckIrError("LLM response has no JSON object")
    blob = text[start : end + 1]
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        try:
            data = json.loads(_repair_json_text(blob))
        except json.JSONDecodeError as exc:
            raise DeckIrError(f"invalid JSON from LLM: {exc}") from exc
    if not isinstance(data, dict):
        raise DeckIrError("deck IR root must be object")
    return data


def _read_meta(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "meta.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _write_meta(out_dir: Path, meta: dict[str, Any], logs_dir: Path | None = None) -> None:
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    (out_dir / "meta.json").write_text(payload, encoding="utf-8")
    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "meta.json").write_text(payload, encoding="utf-8")


def _set_slides(
    out_dir: Path,
    meta: dict[str, Any],
    *,
    status: str,
    stage: str,
    error: str | None = None,
    logs_dir: Path | None = None,
) -> None:
    if status == "running":
        raise_if_cancelled(out_dir)
    meta["slides_status"] = status
    meta["slides_stage"] = stage
    if error is not None:
        meta["slides_error"] = error
    elif "slides_error" in meta and status == "ok":
        meta["slides_error"] = None
    _write_meta(out_dir, meta, logs_dir)
    run_id = str(meta.get("run_id") or out_dir.name)
    if status == "running":
        EVENTS.publish_stage(run_id, stage, scope="slides")
        EVENTS.scan_artifacts(run_id, out_dir)
    elif status == "ok":
        EVENTS.scan_artifacts(run_id, out_dir)
        EVENTS.publish_stage(run_id, "ok", scope="slides")
        EVENTS.publish_terminal(
            run_id, "ok", recap=EVENTS.success_recap(run_id)
        )
    elif status == "error":
        EVENTS.publish_stage(run_id, "error", detail=error, scope="slides")
        EVENTS.publish_terminal(run_id, "error", error=error)
    elif status == "cancelled":
        EVENTS.publish_stage(run_id, "cancelled", scope="slides")
        EVENTS.publish_terminal(run_id, "cancelled")


def _load_source_and_intent(out_dir: Path, meta: dict[str, Any]) -> tuple[str, str]:
    intent = str(meta.get("intent") or "")
    source = ""
    src_meta = meta.get("source")
    if isinstance(src_meta, str) and src_meta.strip():
        p = Path(src_meta)
        if p.is_file():
            source = p.read_text(encoding="utf-8")
    if not source:
        for cand in out_dir.glob("*.txt"):
            if cand.name.endswith(".raw_model.txt"):
                continue
            source = cand.read_text(encoding="utf-8")
            break
    if not source.strip():
        # Last resort: copy from uploads path pattern in meta
        raise RuntimeError("Source text not found for slides job")
    return source, intent


def _chart_ids_and_pngs(out_dir: Path, meta: dict[str, Any]) -> tuple[list[str], dict[str, Path]]:
    planned = [str(x) for x in (meta.get("charts_planned") or []) if x]
    figs = out_dir / "figures"
    by_id: dict[str, Path] = {}
    for cid in planned:
        png = figs / f"{cid}.png"
        if png.is_file():
            by_id[cid] = png
    # Also scan figures.json charts list
    fj = out_dir / "figures.json"
    if fj.is_file():
        try:
            data = json.loads(fj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        for ch in data.get("charts") or []:
            if not isinstance(ch, dict):
                continue
            cid = str(ch.get("id") or "")
            if not cid:
                continue
            if cid not in planned:
                planned.append(cid)
            png = figs / f"{cid}.png"
            if png.is_file():
                by_id[cid] = png
    return planned, by_id


def _stem_from_out(out_dir: Path, meta: dict[str, Any]) -> str:
    for art in sorted(out_dir.glob("*.pdf")):
        name = art.name
        if name.endswith("_deck.pdf"):
            continue
        return art.stem
    for art in sorted(out_dir.glob("*.tex")):
        return art.stem
    return str(meta.get("run_id") or out_dir.name)


def run_slides_job(
    run_id: str,
    *,
    root: Path | None = None,
    llm: LLMClient | None = None,
    skip_llm_ir: dict[str, Any] | None = None,
) -> None:
    """Generate deck artifacts under ``runs/out/{run_id}/``. Soft-fail into slides_* meta."""
    root = Path(root) if root is not None else _repo_root()
    out_dir = (root / "runs" / "out" / run_id).resolve()
    logs_dir = root / "runs" / "logs" / run_id
    if not out_dir.is_dir() or not (out_dir / "meta.json").is_file():
        raise FileNotFoundError(f"run out missing: {out_dir}")

    meta = _read_meta(out_dir)
    if meta.get("status") != "ok":
        raise RuntimeError("report run is not ok")

    _set_slides(out_dir, meta, status="running", stage="queued", logs_dir=logs_dir)
    try:
        source, intent = _load_source_and_intent(out_dir, meta)
        (
            chart_ids,
            figure_ids,
            diagram_ids,
            png_by_id,
            diagram_specs,
        ) = collect_run_media(out_dir, meta)
        palette = normalize_palette_id(str(meta.get("chart_palette") or "atelier"))
        if palette == "auto":
            palette = "atelier"
        from case3.chart_style import palette_from_intent

        parsed = palette_from_intent(intent)
        if parsed and parsed != "auto":
            palette = parsed

        # Deck theme (Julius parity) — does not mutate report chart_palette.
        style_meta = meta.get("slides_style") if isinstance(meta.get("slides_style"), dict) else {}
        theme_pack_raw = str(
            style_meta.get("theme_pack")
            or meta.get("slides_theme_pack")
            or "atelier"
        )
        style_settings = style_meta.get("style_settings")
        if not isinstance(style_settings, dict):
            style_settings = None
        structure_id = str(
            style_meta.get("structure_id")
            or meta.get("slides_structure_id")
            or ""
        ).strip() or None
        # Freeform: infer beat plan (+ pack hint). Structured: plan from template arc.
        beat_plan = plan_beats(
            source=source,
            intent=intent,
            chart_ids=chart_ids,
            figure_ids=figure_ids,
            diagram_ids=diagram_ids,
            structure_id=structure_id,
        )
        # Pack is "explicit" when UI chose a non-default pack, custom hex, or flag.
        chosen = normalize_pack_id(theme_pack_raw)
        pack_explicit = bool(
            meta.get("slides_pack_explicit")
            or style_meta.get("pack_explicit")
            or style_settings
            or (style_meta.get("theme_pack") and chosen != "atelier")
        )
        theme_pack = maybe_apply_pack_hint(
            structure_id=structure_id,
            current_pack=theme_pack_raw,
            plan=beat_plan,
            pack_explicit=pack_explicit,
        )
        theme_tokens = resolve_deck_theme(theme_pack, style_settings=style_settings)
        beat_overlay = format_beat_overlay(beat_plan)
        meta["slides_beat"] = {
            "mode": beat_plan.mode,
            "pack_hint": beat_plan.pack_hint,
            "pack_applied": theme_tokens.pack_id,
            "from_structure": beat_plan.from_structure,
            "beats": list(beat_plan.beats),
            "rationale": beat_plan.rationale,
        }

        allowed_media = frozenset(chart_ids + figure_ids + diagram_ids)
        allowed_numbers = numbers_from_media_json(load_figures_json(out_dir))

        _set_slides(out_dir, meta, status="running", stage="llm", logs_dir=logs_dir)
        if skip_llm_ir is not None:
            raw_ir = skip_llm_ir
            deck = parse_deck_ir(
                raw_ir,
                source=source,
                allowed_media_ids=allowed_media,
                allowed_number_strings=allowed_numbers,
            )
        else:
            system = load_slides_system_prompt(
                palette=palette,
                chart_ids=chart_ids,
                figure_ids=figure_ids,
                diagram_ids=diagram_ids,
                intent=intent,
                source=source,
                media_catalog=_media_catalog_block(out_dir),
                theme_pack=theme_tokens.pack_id,
                structure_id=structure_id,
                beat_overlay=beat_overlay,
            )
            allowed_preview = ", ".join(sorted(allowed_numbers)[:60]) or "(none from charts)"
            user = (
                "Build the executive deck JSON now. "
                "Follow the BEAT PLAN / STRUCTURE overlay skeleton (layouts in order). "
                "Prefer 10–12 slides when Source is rich; keep ≥5 distinct layouts when ≥8 slides. "
                "Use available chart/figure/diagram ids only. "
                "Numbers only from Source or this allowed token list "
                f"(chart captions/HTML): {allowed_preview}. "
                "Do not invent decimals. "
                "Return only the JSON object."
            )
            client = llm or LLMClient(LLMConfig.from_env())

            def _parse_or_scrub(raw_ir: dict[str, Any]) -> dict[str, Any]:
                try:
                    return parse_deck_ir(
                        raw_ir,
                        source=source,
                        allowed_media_ids=allowed_media,
                        allowed_number_strings=allowed_numbers,
                    )
                except DeckIrError as err:
                    # Always scrub digits first — also demotes broken tables/KPIs.
                    healed = scrub_invented_numbers(
                        raw_ir,
                        source=source,
                        allowed_number_strings=allowed_numbers,
                    )
                    try:
                        deck_h = parse_deck_ir(
                            healed,
                            source=source,
                            allowed_media_ids=allowed_media,
                            allowed_number_strings=allowed_numbers,
                        )
                    except DeckIrError:
                        raise err from None
                    meta["slides_number_scrub"] = True
                    log.warning("deck IR reject healed by scrub: %s", err)
                    return deck_h

            def _cancel() -> None:
                raise_if_cancelled(out_dir)

            raw_text = client.complete(
                system=system,
                user_text=user,
                reasoning="off",
                cancel_check=_cancel,
            )
            try:
                raw_ir = _extract_json_object(raw_text)
                deck = _parse_or_scrub(raw_ir)
            except DeckIrError as first_err:
                log.warning("deck IR rejected, retrying once: %s", first_err)
                _set_slides(
                    out_dir,
                    meta,
                    status="running",
                    stage="llm_retry",
                    logs_dir=logs_dir,
                )
                retry_user = (
                    f"Previous JSON was rejected: {first_err}. "
                    "Fix and return ONLY a valid deck JSON object (no markdown). "
                    "Follow the BEAT PLAN skeleton layouts; "
                    "≥5 distinct layouts when ≥8 slides; "
                    "at most 2 consecutive scorecard/kpi_row; "
                    "Use available media ids; "
                    f"ONLY these number tokens (or Source): {allowed_preview}; "
                    "bullets ≤90 chars; title first, closing last. "
                    "Do not invent averages or deltas."
                )
                raw_text = client.complete(
                    system=system,
                    user_text=retry_user,
                    reasoning="off",
                    cancel_check=_cancel,
                )
                raw_ir = _extract_json_object(raw_text)
                deck = _parse_or_scrub(raw_ir)
        # Freeze theme into IR (overwrite any LLM paint fields).
        deck["theme_id"] = theme_tokens.pack_id
        deck["style"] = theme_tokens.as_dict()
        deck["palette"] = palette

        # Every native-eligible cht_* must appear in the deck (inject missing).
        fj_early = load_figures_json(out_dir)
        attach_series_ir_to_charts(fj_early.get("charts") if isinstance(fj_early, dict) else None)
        series_all = series_map_from_figures(fj_early if isinstance(fj_early, dict) else {})
        injected = ensure_deck_charts(deck, series_all)
        if injected:
            meta["slides_chart_injected"] = injected
            log.info("slides: injected chart_hero for %s", injected)
            fj_path = out_dir / "figures.json"
            if fj_path.is_file() and isinstance(fj_early, dict):
                fj_path.write_text(
                    json.dumps(fj_early, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

        _materialize_deck_artifacts(
            out_dir,
            meta,
            deck=deck,
            palette=palette,
            chart_ids=chart_ids,
            png_by_id=png_by_id,
            diagram_specs=diagram_specs,
            logs_dir=logs_dir,
        )
        log.info(
            "slides ok run_id=%s slides=%s",
            run_id,
            (meta.get("slides_artifacts") or {}).get("png_count"),
        )
    except RunCancelled:
        log.info("slides cancelled run_id=%s", run_id)
        meta = _read_meta(out_dir)
        _set_slides(
            out_dir,
            meta,
            status="cancelled",
            stage="cancelled",
            error="Остановлено",
            logs_dir=logs_dir,
        )
    except (DeckIrError, LLMError, LLMConfigError, OSError, RuntimeError, ValueError) as exc:
        log.exception("slides failed run_id=%s", run_id)
        meta = _read_meta(out_dir)
        _set_slides(
            out_dir,
            meta,
            status="error",
            stage="error",
            error=str(exc),
            logs_dir=logs_dir,
        )


def _chart_ids_in_deck(deck: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for s in deck.get("slides") or []:
        if not isinstance(s, dict):
            continue
        for key in ("chart_id", "media_id"):
            mid = str(s.get(key) or "").strip()
            if mid.startswith("cht_"):
                out.add(mid)
    return out


def _recolor_deck_charts(
    out_dir: Path,
    deck: dict[str, Any],
    *,
    slides_dir: Path,
) -> dict[str, Path]:
    """Re-render deck-referenced charts with pack ``chart_series`` colors.

    Report figures/ stay untouched; deck copies live under ``slides/charts/``.
    """
    style = deck.get("style") if isinstance(deck.get("style"), dict) else {}
    series = [
        str(x)
        for x in (style.get("chart_series") or [])
        if str(x).strip()
    ]
    if not series:
        return {}
    colors = style.get("colors") if isinstance(style.get("colors"), dict) else {}
    muted = str(colors.get("muted") or "") or None
    motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
    pack = str(style.get("pack_id") or deck.get("theme_id") or "")
    dark = pack in ("signal", "ink", "voltage", "botanical") or str(
        motif.get("atmosphere") or ""
    ) == "dark"
    foil = str(colors.get("foil") or colors.get("accent") or series[0])
    ink = str(colors.get("ink") or ("#F7F5F0" if dark else "#14161A"))
    bg = str(colors.get("paper") or colors.get("sheet") or ("#161618" if dark else "#FFFCF7"))
    # Soft area/grid from first series
    fr, fg, fb = (
        int(foil.lstrip("#")[0:2], 16),
        int(foil.lstrip("#")[2:4], 16),
        int(foil.lstrip("#")[4:6], 16),
    )
    area = f"rgba({fr},{fg},{fb},0.28)"
    grid = (
        "rgba(255,255,255,0.10)" if dark else f"rgba({fr},{fg},{fb},0.12)"
    )

    needed = _chart_ids_in_deck(deck)
    if not needed:
        return {}
    fj = load_figures_json(out_dir)
    html_by_id: dict[str, str] = {}
    type_by_id: dict[str, str] = {}
    for ch in fj.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        cid = str(ch.get("id") or "").strip()
        if cid in needed and str(ch.get("html") or "").strip():
            html_by_id[cid] = str(ch.get("html") or "")
            type_by_id[cid] = str(ch.get("type") or "").strip().lower()

    dest_dir = slides_dir / "charts"
    dest_dir.mkdir(parents=True, exist_ok=True)
    work_root = slides_dir / "chart_work"
    work_root.mkdir(parents=True, exist_ok=True)
    out_map: dict[str, Path] = {}
    for cid, html in html_by_id.items():
        try:
            remapped = apply_hex_series_to_html(
                sanitize_chart_html(html),
                series,
                muted=muted,
                area=area,
                grid=grid,
            )
            # Twin ≈ native: per-category pack colors on single-series bar/donut.
            remapped = apply_pack_category_colors_to_html(
                remapped,
                series,
                chart_type=type_by_id.get(cid) or None,
            )
            if dark:
                remapped = (
                    f"<style>html,body,#mount{{background:{bg}!important;"
                    f"color:{ink}!important}}</style>"
                    + remapped
                )
            dest = dest_dir / f"{cid}.png"
            render_chart_png(
                {"html": remapped},
                dest,
                work_dir=work_root / cid,
            )
            if dest.is_file():
                out_map[cid] = dest
                log.info("deck chart recolor ok %s → %s", cid, dest.name)
        except (OSError, RuntimeError, ValueError) as exc:
            log.warning("deck chart recolor skipped %s: %s", cid, exc)
    return out_map


def _materialize_deck_artifacts(
    out_dir: Path,
    meta: dict[str, Any],
    *,
    deck: dict[str, Any],
    palette: str,
    chart_ids: list[str],
    png_by_id: dict[str, Path],
    diagram_specs: dict[str, dict[str, str]] | None,
    logs_dir: Path | None,
) -> None:
    """Write deck.json + PNG twin + native PPTX + deck PDF."""
    slides_dir = out_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    (slides_dir / "deck.json").write_text(
        json.dumps(deck, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    needed_dias: set[str] = set()
    for s in deck.get("slides") or []:
        if not isinstance(s, dict):
            continue
        if s.get("layout") in ("media_hero", "media_split"):
            mid = str(s.get("media_id") or "")
            if mid.startswith("dia_"):
                needed_dias.add(mid)

    _set_slides(out_dir, meta, status="running", stage="diagrams", logs_dir=logs_dir)
    media_map = dict(png_by_id)
    if needed_dias:
        dia_pngs = ensure_diagram_pngs(
            diagram_specs or {},
            dest_dir=slides_dir / "diagrams",
            palette=palette,
            needed_ids=needed_dias,
        )
        media_map.update(dia_pngs)

    _set_slides(out_dir, meta, status="running", stage="charts", logs_dir=logs_dir)
    try:
        media_map.update(_recolor_deck_charts(out_dir, deck, slides_dir=slides_dir))
    except (OSError, RuntimeError, ValueError) as exc:
        log.warning("deck chart recolor batch failed: %s", exc)

    _set_slides(out_dir, meta, status="running", stage="render", logs_dir=logs_dir)
    raise_if_cancelled(out_dir)
    work_root = slides_dir / "work"
    pngs = render_deck_pngs(
        deck,
        work_root=work_root,
        out_dir=slides_dir,
        media_png_by_id=media_map,
    )
    if not pngs:
        raise RuntimeError("no slide PNGs produced")

    _set_slides(out_dir, meta, status="running", stage="pptx", logs_dir=logs_dir)
    raise_if_cancelled(out_dir)
    stem = _stem_from_out(out_dir, meta)
    pptx_path = out_dir / f"{stem}_slides.pptx"
    pdf_path = out_dir / f"{stem}_deck.pdf"
    tmp_pptx = out_dir / f".{stem}_slides.pptx.tmp"
    tmp_pdf = out_dir / f".{stem}_deck.pdf.tmp"
    fj = load_figures_json(out_dir)
    if isinstance(fj, dict):
        attach_series_ir_to_charts(fj.get("charts"))
        # Keep figures.json series in sync for Liber re-exports / edits.
        fj_path = out_dir / "figures.json"
        try:
            fj_path.write_text(
                json.dumps(fj, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass
    # Every cht_* referenced by the deck must resolve series when possible.
    needed = set(chart_ids) | _chart_ids_in_deck(deck)
    chart_series: dict[str, dict[str, Any]] = {}
    for cid in sorted(needed):
        ir = series_from_figures_json(fj if isinstance(fj, dict) else {}, cid)
        if ir:
            chart_series[cid] = ir
    # Also pull any leftover eligible charts (ensure path / multi-ref).
    for cid, ir in series_map_from_figures(
        fj if isinstance(fj, dict) else {}
    ).items():
        chart_series.setdefault(cid, ir)
    # Drop series not on deck slides — avoid unused chart parts; keep only needed.
    chart_series = {cid: ir for cid, ir in chart_series.items() if cid in needed}
    missing = sorted(needed - set(chart_series))
    if missing:
        log.warning(
            "native chart series missing for %s — those slides fall back to PNG",
            missing,
        )
    build_native_pptx(
        deck,
        tmp_pptx,
        media_by_id=media_map,
        chart_series_by_id=chart_series,
    )
    meta["slides_native_charts"] = sorted(chart_series.keys())

    raise_if_cancelled(out_dir)
    # Julius path: LO-convert native PPTX → PDF; PNG stitch if soffice missing.
    _, pdf_mode = write_deck_pdf(tmp_pptx, pngs, tmp_pdf)
    tmp_pptx.replace(pptx_path)
    tmp_pdf.replace(pdf_path)

    meta["slides_artifacts"] = {
        "pptx": pptx_path.name,
        "deck_pdf": pdf_path.name,
        "deck_pdf_mode": pdf_mode,
        "ir": "slides/deck.json",
        "png_count": len(pngs),
    }
    _set_slides(out_dir, meta, status="ok", stage="ok", logs_dir=logs_dir)


def rebuild_slides_from_deck(
    run_id: str,
    deck: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Re-render PPTX + twin PNGs/PDF from an already-validated deck IR (no LLM)."""
    root = Path(root) if root is not None else _repo_root()
    out_dir = (root / "runs" / "out" / run_id).resolve()
    logs_dir = root / "runs" / "logs" / run_id
    meta = _read_meta(out_dir)
    if meta.get("status") != "ok":
        raise RuntimeError("report run is not ok")
    (
        chart_ids,
        _figure_ids,
        _diagram_ids,
        png_by_id,
        diagram_specs,
    ) = collect_run_media(out_dir, meta)
    palette = normalize_palette_id(str(meta.get("chart_palette") or "atelier"))
    if palette == "auto":
        palette = "atelier"
    # Keep frozen style from deck if present.
    if not isinstance(deck.get("style"), dict):
        style_meta = meta.get("slides_style") if isinstance(meta.get("slides_style"), dict) else {}
        theme_tokens = resolve_deck_theme(
            str(style_meta.get("theme_pack") or "atelier"),
            style_settings=style_meta.get("style_settings")
            if isinstance(style_meta.get("style_settings"), dict)
            else None,
        )
        deck = dict(deck)
        deck["theme_id"] = theme_tokens.pack_id
        deck["style"] = theme_tokens.as_dict()
    try:
        _materialize_deck_artifacts(
            out_dir,
            meta,
            deck=deck,
            palette=palette,
            chart_ids=chart_ids,
            png_by_id=png_by_id,
            diagram_specs=diagram_specs,
            logs_dir=logs_dir,
        )
    except RunCancelled:
        meta = _read_meta(out_dir)
        _set_slides(
            out_dir,
            meta,
            status="cancelled",
            stage="cancelled",
            error="Остановлено",
            logs_dir=logs_dir,
        )
        raise
    return _read_meta(out_dir)
