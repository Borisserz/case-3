"""In-process SSE bus for Liber run progress (stages / artifacts / terminal).

Does not stream model thoughts — only craft stage bumps and file-ready pulses.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class _RunEvents:
    lock: threading.Lock = field(default_factory=threading.Lock)
    events: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    terminal: str | None = None  # done|error|cancelled
    artifacts_seen: set[str] = field(default_factory=set)
    film_seen: set[str] = field(default_factory=set)
    started_at: float = field(default_factory=time.time)
    cond: threading.Condition = field(default_factory=threading.Condition)


def build_success_recap(
    *,
    elapsed_s: float,
    artifacts_seen: set[str] | None = None,
    charts: int = 0,
    figures: int = 0,
) -> dict[str, Any]:
    """Payload for SSE done.recap (success only)."""
    seen = artifacts_seen or set()
    formats: list[str] = []
    for key in ("pdf", "docx", "pptx", "slides_pdf"):
        if key in seen:
            formats.append(key)
    return {
        "elapsed_s": max(0, int(round(float(elapsed_s)))),
        "charts": max(0, int(charts)),
        "figures": max(0, int(figures)),
        "formats": formats,
    }


class RunEventBus:
    """Publish stage/artifact/terminal; subscribers get replay + live until done."""

    def __init__(self) -> None:
        self._runs: dict[str, _RunEvents] = {}
        self._lock = threading.Lock()

    def _state(self, run_id: str) -> _RunEvents:
        with self._lock:
            st = self._runs.get(run_id)
            if st is None:
                st = _RunEvents()
                self._runs[run_id] = st
            return st

    def start(self, run_id: str) -> None:
        """Reset bus for a new run (clears history)."""
        st = self._state(run_id)
        with st.cond:
            st.events.clear()
            st.done = False
            st.terminal = None
            st.artifacts_seen.clear()
            st.film_seen.clear()
            st.started_at = time.time()
            st.cond.notify_all()

    def ensure(self, run_id: str) -> None:
        """Open bus without wiping events (pipeline after API queued seed)."""
        st = self._state(run_id)
        with st.cond:
            st.done = False
            st.terminal = None
            st.cond.notify_all()

    def reopen(self, run_id: str) -> None:
        """Allow more events after pipeline done (e.g. on-demand slides job)."""
        self.ensure(run_id)

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        st = self._state(run_id)
        with st.cond:
            kind = str(event.get("event") or "")
            scope = str(event.get("scope") or "")
            # Slides craft can continue after pipeline terminal if reopened;
            # drop only hard duplicates of terminal while still closed.
            if st.done and kind in {"done", "error", "cancelled"}:
                return
            if st.done and kind not in {"stage", "step", "artifact", "film"}:
                return
            if st.done and kind == "stage" and scope != "slides":
                return
            st.events.append(dict(event))
            if kind in {"done", "error", "cancelled"}:
                st.done = True
                st.terminal = kind
            st.cond.notify_all()

    def publish_stage(
        self,
        run_id: str,
        stage: str,
        *,
        detail: str | None = None,
        scope: str = "pipeline",
        eta_s: float | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": "stage",
            "stage": stage,
            "scope": scope,  # pipeline | slides
            "t": time.time(),
        }
        if detail:
            payload["detail"] = detail
        if eta_s is not None and eta_s > 0:
            payload["eta_s"] = float(eta_s)
        self.publish(run_id, payload)

    def publish_step(
        self,
        run_id: str,
        *,
        parent: str,
        step_id: str,
        status: str = "active",
        reason: str | None = None,
        label: str | None = None,
        scope: str = "pipeline",
    ) -> None:
        """Fine-grained craft beat (cht_01 under charts, skipped photos, …)."""
        st = (status or "active").strip().lower()
        if st not in {"active", "done", "skipped"}:
            st = "active"
        payload: dict[str, Any] = {
            "event": "step",
            "parent": (parent or "").strip() or "charts",
            "id": (step_id or "").strip() or "step",
            "status": st,
            "scope": scope,
            "t": time.time(),
        }
        if reason:
            payload["reason"] = reason
        if label:
            payload["label"] = label
        self.publish(run_id, payload)

    def publish_artifact(self, run_id: str, kind: str) -> None:
        st = self._state(run_id)
        with st.cond:
            if kind in st.artifacts_seen or st.done:
                return
            st.artifacts_seen.add(kind)
            st.events.append(
                {
                    "event": "artifact",
                    "kind": kind,
                    "ready": True,
                    "t": time.time(),
                }
            )
            st.cond.notify_all()

    def publish_film_frame(
        self,
        run_id: str,
        *,
        frame_id: str,
        kind: str,
        url: str,
    ) -> None:
        """One PNG birth for ThinkingFold film strip (cht_* / fig_*)."""
        fid = (frame_id or "").strip()
        if not fid or not url:
            return
        st = self._state(run_id)
        with st.cond:
            if fid in st.film_seen:
                return
            st.film_seen.add(fid)
            st.events.append(
                {
                    "event": "film",
                    "id": fid,
                    "kind": (kind or "chart").strip() or "chart",
                    "url": url,
                    "t": time.time(),
                }
            )
            st.cond.notify_all()

    def publish_terminal(
        self,
        run_id: str,
        status: str,
        *,
        error: str | None = None,
        hint: str | None = None,
        recap: dict[str, Any] | None = None,
    ) -> None:
        kind = status if status in {"done", "error", "cancelled"} else "done"
        if status == "ok":
            kind = "done"
        payload: dict[str, Any] = {"event": kind, "status": status, "t": time.time()}
        if error:
            payload["error"] = error
        if hint:
            payload["hint"] = hint
        # Recap only on success
        if kind == "done" and recap:
            payload["recap"] = dict(recap)
        self.publish(run_id, payload)

    def elapsed_s(self, run_id: str) -> float:
        st = self._state(run_id)
        with st.cond:
            return max(0.0, time.time() - float(st.started_at or time.time()))

    def success_recap(
        self,
        run_id: str,
        *,
        charts: int = 0,
        figures: int = 0,
    ) -> dict[str, Any]:
        st = self._state(run_id)
        with st.cond:
            seen = set(st.artifacts_seen)
            elapsed = max(0.0, time.time() - float(st.started_at or time.time()))
            # Prefer film counts when meta counts missing
            film_charts = sum(1 for x in st.film_seen if x.startswith("cht_"))
            film_figs = sum(
                1 for x in st.film_seen if x.startswith(("fig_", "usr_"))
            )
        return build_success_recap(
            elapsed_s=elapsed,
            artifacts_seen=seen,
            charts=charts or film_charts,
            figures=figures or film_figs,
        )

    def scan_artifacts(self, run_id: str, out_dir: Path) -> None:
        """Detect PDF/DOCX/PPTX/PNG ready under out/ and emit once each."""
        out = Path(out_dir)
        if not out.is_dir():
            return
        for pdf in out.glob("*.pdf"):
            if pdf.is_file() and pdf.stat().st_size > 100:
                name = pdf.name.lower()
                if "deck" in name or name.startswith("slides"):
                    self.publish_artifact(run_id, "slides_pdf")
                else:
                    self.publish_artifact(run_id, "pdf")
                break
        for docx in out.glob("*.docx"):
            if docx.is_file() and docx.stat().st_size > 100:
                self.publish_artifact(run_id, "docx")
                break
        slides = out / "slides"
        pptx_candidates = list(out.glob("*.pptx")) + (
            list(slides.glob("*.pptx")) if slides.is_dir() else []
        )
        for pptx in pptx_candidates:
            if pptx.is_file() and pptx.stat().st_size > 100:
                self.publish_artifact(run_id, "pptx")
                break
        figs = out / "figures"
        if figs.is_dir():
            pngs = [
                p
                for p in sorted(figs.glob("*.png"))
                if p.is_file() and p.stat().st_size > 50
            ]
            if any(p.name.startswith("cht_") for p in pngs):
                self.publish_artifact(run_id, "chart")
            if any(p.name.startswith("fig_") for p in pngs):
                self.publish_artifact(run_id, "figure")
            elif pngs and not any(p.name.startswith("cht_") for p in pngs):
                self.publish_artifact(run_id, "figure")
            for png in pngs:
                stem = png.stem
                if stem.startswith("cht_"):
                    kind = "chart"
                elif stem.startswith(("fig_", "usr_")):
                    kind = "figure"
                else:
                    continue
                self.publish_film_frame(
                    run_id,
                    frame_id=stem,
                    kind=kind,
                    url=f"/api/runs/{run_id}/figures/{png.name}",
                )

    def snapshot(self, run_id: str) -> dict[str, Any]:
        st = self._state(run_id)
        with st.cond:
            return {
                "count": len(st.events),
                "done": st.done,
                "terminal": st.terminal,
                "artifacts": sorted(st.artifacts_seen),
                "film": sorted(st.film_seen),
            }

    def subscribe(self, run_id: str, *, timeout_s: float = 1200.0) -> Iterator[dict[str, Any]]:
        """Yield event dicts until terminal or timeout."""
        st = self._state(run_id)
        sent = 0
        deadline = time.monotonic() + max(0.1, timeout_s)
        while True:
            with st.cond:
                while sent >= len(st.events) and not st.done:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        yield {
                            "event": "error",
                            "status": "error",
                            "error": "events timeout",
                            "t": time.time(),
                        }
                        return
                    st.cond.wait(timeout=min(0.5, remaining))

                while sent < len(st.events):
                    ev = st.events[sent]
                    sent += 1
                    yield dict(ev)

                if st.done:
                    return


# Process-wide bus used by pipeline + slides + API
EVENTS = RunEventBus()
