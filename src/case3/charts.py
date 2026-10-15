"""Render LLM HTML charts to PNG via Playwright (offline Chart.js)."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from case3.chart_html import assets_charts_dir, sanitize_chart_html, wrap_chart_page

log = logging.getLogger("case3.charts")

_MAX_PNG = 12 * 1024 * 1024


def max_charts_from_env() -> int:
    try:
        return max(0, int(os.environ.get("CASE3_MAX_CHARTS", "0") or "0"))
    except ValueError:
        return 0


def chart_timeout_s() -> float:
    try:
        return max(3.0, float(os.environ.get("CASE3_CHART_TIMEOUT_S", "15") or "15"))
    except ValueError:
        return 15.0


def _write_page(work_dir: Path, fragment: str) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    vendor = assets_charts_dir() / "chart.umd.min.js"
    if not vendor.is_file():
        raise RuntimeError(f"missing vendored Chart.js: {vendor}")
    shutil.copy2(vendor, work_dir / "chart.umd.min.js")
    page = wrap_chart_page(fragment=fragment)
    index = work_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    return index


def render_chart_png(chart: dict[str, Any], dest_png: Path, *, work_dir: Path) -> None:
    html = sanitize_chart_html(str(chart.get("html") or ""))
    index = _write_page(work_dir, html)
    timeout_ms = int(chart_timeout_s() * 1000)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright not installed — run: pip install playwright && playwright install chromium"
        ) from exc

    dest_png.parent.mkdir(parents=True, exist_ok=True)
    work_dir = work_dir.resolve()
    index = index.resolve()
    allowed = {
        index.resolve(),
        (work_dir / "chart.umd.min.js").resolve(),
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": 1008, "height": 600},
                device_scale_factor=2,
            )

            def _route(route, request):  # noqa: ANN001
                import urllib.parse

                url = request.url
                if url.startswith("data:"):
                    route.continue_()
                    return
                if url.startswith("file:"):
                    path = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path))
                    # Windows file:///C:/... → path may need adjust
                    try:
                        resolved = path.resolve()
                    except OSError:
                        route.abort()
                        return
                    if resolved in allowed:
                        route.continue_()
                    else:
                        route.abort()
                    return
                route.abort()

            context.route("**/*", _route)
            page = context.new_page()
            page.goto(index.as_uri(), wait_until="load", timeout=timeout_ms)
            page.wait_for_function(
                "() => window.__CASE3_CHART_READY === true",
                timeout=timeout_ms,
            )
            mount = page.locator("#mount")
            mount.screenshot(path=str(dest_png), type="png")
            context.close()
        finally:
            browser.close()

    data = dest_png.read_bytes()
    if len(data) > _MAX_PNG:
        dest_png.unlink(missing_ok=True)
        raise RuntimeError(f"chart png too large: {len(data)} bytes")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        dest_png.unlink(missing_ok=True)
        raise RuntimeError("chart screenshot is not PNG")


def generate_all_charts(
    charts: list[dict[str, Any]],
    figures_dir: Path,
    *,
    work_root: Path | None = None,
) -> dict[str, Any]:
    """Render charts into figures_dir/<id>.png. Soft-fail per chart."""
    status: dict[str, Any] = {}
    if max_charts_from_env() <= 0:
        return status
    figures_dir.mkdir(parents=True, exist_ok=True)
    root = work_root or (figures_dir.parent / "chart_work")
    for chart in charts[: max_charts_from_env()]:
        cid = chart["id"]
        dest = figures_dir / f"{cid}.png"
        cdir = root / cid
        try:
            render_chart_png(chart, dest, work_dir=cdir)
            status[cid] = {"ok": True, "path": str(dest), "kind": "chart"}
            log.info("chart ok %s → %s", cid, dest)
        except Exception as exc:  # noqa: BLE001 — soft-fail per chart
            status[cid] = {"ok": False, "error": str(exc)[:400], "kind": "chart"}
            log.warning("chart failed %s: %s", cid, exc)
            if dest.exists():
                dest.unlink()
    return status
