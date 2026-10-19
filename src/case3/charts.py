"""Render LLM HTML charts to PNG via Playwright (offline Chart.js)."""

from __future__ import annotations

import concurrent.futures
import logging
import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Any, Callable, TypeVar

from case3.chart_html import assets_charts_dir, sanitize_chart_html, wrap_chart_page

log = logging.getLogger("case3.charts")

_T = TypeVar("_T")


def _run_sync_playwright(fn: Callable[[], _T]) -> _T:
    """Always run Playwright Sync API in a fresh OS thread.

    FastAPI/uvicorn may call us under a running asyncio loop (or from
    ``asyncio.to_thread`` on a worker that still confuses Playwright on
    Windows). A dedicated thread has no running loop → Sync API is safe.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(fn).result()

_MAX_PNG = 12 * 1024 * 1024
# Single env knob for chart budget (used by generate / parse / pipeline / render).
ENV_MAX_CHARTS = "CASE3_MAX_CHARTS"


def max_charts_from_env() -> int:
    """Only CASE3_MAX_CHARTS controls how many charts may appear."""
    try:
        return max(0, int(os.environ.get(ENV_MAX_CHARTS, "0") or "0"))
    except ValueError:
        return 0


def chart_timeout_s() -> float:
    try:
        return max(3.0, float(os.environ.get("CASE3_CHART_TIMEOUT_S", "15") or "15"))
    except ValueError:
        return 15.0


def file_url_to_path(url: str) -> Path:
    """Convert file:// URL to a filesystem Path (Windows Chromium-safe)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "file":
        raise ValueError(f"not a file URL: {url!r}")
    raw = urllib.parse.unquote(parsed.path or "")
    # Windows: urlparse gives /C:/Users/... or /C|/Users/...
    if len(raw) >= 3 and raw[0] == "/" and raw[2] in ":|":
        raw = raw[1:]
        if raw[1] == "|":
            raw = raw[0] + ":" + raw[2:]
    # UNC: file://server/share → netloc set
    if parsed.netloc and parsed.netloc not in ("", "localhost"):
        raw = f"//{parsed.netloc}{raw}"
    return Path(raw)


def paths_equal(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(
            os.path.normpath(str(b))
        )


def _write_frame(work_dir: Path) -> Path:
    """Write empty frame (fragment injected via DOM to avoid #mount breakout)."""
    work_dir.mkdir(parents=True, exist_ok=True)
    vendor = assets_charts_dir() / "chart.umd.min.js"
    if not vendor.is_file():
        raise RuntimeError(f"missing vendored Chart.js: {vendor}")
    shutil.copy2(vendor, work_dir / "chart.umd.min.js")
    page = wrap_chart_page(fragment="")  # mount left empty
    index = work_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    return index


def _assert_chart_visible(page) -> None:  # noqa: ANN001
    """Reject blank / empty charts before accepting PNG."""
    stats = page.evaluate(
        """() => {
          const mount = document.getElementById('mount');
          if (!mount) return {ok: false, reason: 'no mount'};
          const canvas = mount.querySelector('canvas');
          if (canvas && canvas.width > 0 && canvas.height > 0) {
            const ctx = canvas.getContext('2d');
            const {width, height} = canvas;
            const data = ctx.getImageData(0, 0, width, height).data;
            let painted = 0;
            for (let i = 0; i < data.length; i += 16) {
              const a = data[i+3];
              if (a < 8) continue;  // ignore fully transparent
              if (data[i] < 250 || data[i+1] < 250 || data[i+2] < 250) painted++;
            }
            return {ok: painted >= 40, reason: 'canvas painted=' + painted, painted};
          }
          const text = (mount.innerText || '').trim();
          if (text.length >= 1) return {ok: true, reason: 'kpi/text'};
          return {ok: false, reason: 'empty mount'};
        }"""
    )
    if not stats or not stats.get("ok"):
        raise RuntimeError(f"blank chart screenshot: {stats}")


def render_chart_png(chart: dict[str, Any], dest_png: Path, *, work_dir: Path) -> None:
    html = sanitize_chart_html(str(chart.get("html") or ""))
    index = _write_frame(work_dir)
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

    def _render() -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 1200, "height": 680},
                    device_scale_factor=2,
                )

                def _route(route, request):  # noqa: ANN001
                    url = request.url
                    if url.startswith("data:"):
                        route.continue_()
                        return
                    if url.startswith("file:"):
                        try:
                            resolved = file_url_to_path(url)
                        except (ValueError, OSError):
                            route.abort()
                            return
                        if any(paths_equal(resolved, a) for a in allowed):
                            route.continue_()
                        else:
                            route.abort()
                        return
                    route.abort()

                context.route("**/*", _route)
                page = context.new_page()
                page.goto(index.as_uri(), wait_until="load", timeout=timeout_ms)
                # Inject via DOM (stray </div> cannot break #mount). Re-exec <script>
                # because browsers do not run scripts inserted with innerHTML.
                page.evaluate(
                    """(html) => {
                      const mount = document.getElementById('mount');
                      window.__CASE3_CHART_READY = false;
                      mount.innerHTML = html;
                      for (const old of Array.from(mount.querySelectorAll('script'))) {
                        const s = document.createElement('script');
                        s.textContent = old.textContent;
                        old.replaceWith(s);
                      }
                    }""",
                    html,
                )
                page.wait_for_function(
                    "() => window.__CASE3_CHART_READY === true",
                    timeout=timeout_ms,
                )
                page.wait_for_timeout(120)
                _assert_chart_visible(page)
                page.locator("#mount").screenshot(path=str(dest_png), type="png")
                context.close()
            finally:
                browser.close()

    _run_sync_playwright(_render)

    data = dest_png.read_bytes()
    if len(data) > _MAX_PNG:
        dest_png.unlink(missing_ok=True)
        raise RuntimeError(f"chart png too large: {len(data)} bytes")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        dest_png.unlink(missing_ok=True)
        raise RuntimeError("chart screenshot is not PNG")
    if len(data) < 800:
        dest_png.unlink(missing_ok=True)
        raise RuntimeError(f"chart png suspiciously small: {len(data)} bytes")


def generate_all_charts(
    charts: list[dict[str, Any]],
    figures_dir: Path,
    *,
    work_root: Path | None = None,
    max_charts: int | None = None,
) -> dict[str, Any]:
    """Render charts into figures_dir/<id>.png. Soft-fail per chart."""
    status: dict[str, Any] = {}
    limit = max_charts_from_env() if max_charts is None else max(0, int(max_charts))
    if limit <= 0:
        return status
    figures_dir.mkdir(parents=True, exist_ok=True)
    root = work_root or (figures_dir.parent / "chart_work")
    for chart in charts[:limit]:
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
