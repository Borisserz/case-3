"""In-process token bus for chat-summary SSE (per run_id)."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _RunState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    deltas: list[str] = field(default_factory=list)
    full: str = ""
    status: str = "pending"  # pending|streaming|ok|error|skipped
    done: bool = False
    waiters: list[threading.Event] = field(default_factory=list)
    cond: threading.Condition = field(default_factory=threading.Condition)


class SummaryBus:
    """Publish deltas; subscribers get replay + live until done."""

    def __init__(self) -> None:
        self._runs: dict[str, _RunState] = {}
        self._lock = threading.Lock()

    def _state(self, run_id: str) -> _RunState:
        with self._lock:
            st = self._runs.get(run_id)
            if st is None:
                st = _RunState()
                self._runs[run_id] = st
            return st

    def start(self, run_id: str) -> None:
        st = self._state(run_id)
        with st.cond:
            st.status = "streaming"
            st.done = False
            st.deltas.clear()
            st.full = ""
            st.cond.notify_all()

    def publish(self, run_id: str, text: str) -> None:
        if not text:
            return
        st = self._state(run_id)
        with st.cond:
            st.deltas.append(text)
            st.status = "streaming"
            st.cond.notify_all()

    def finish(self, run_id: str, text: str, status: str = "ok") -> None:
        st = self._state(run_id)
        with st.cond:
            st.full = text or "".join(st.deltas)
            st.status = status
            st.done = True
            st.cond.notify_all()

    def snapshot(self, run_id: str) -> dict[str, Any]:
        st = self._state(run_id)
        with st.cond:
            return {
                "text": st.full or "".join(st.deltas),
                "status": st.status,
                "done": st.done,
            }

    def subscribe(self, run_id: str, *, timeout_s: float = 120.0) -> Iterator[dict[str, Any]]:
        """Yield {event, text?, status?} until done or timeout."""
        st = self._state(run_id)
        sent = 0
        deadline = time.monotonic() + max(0.1, timeout_s)
        while True:
            with st.cond:
                while sent >= len(st.deltas) and not st.done:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        yield {
                            "event": "done",
                            "text": st.full or "".join(st.deltas),
                            "status": st.status if st.done else "error",
                        }
                        return
                    st.cond.wait(timeout=min(0.5, remaining))

                while sent < len(st.deltas):
                    piece = st.deltas[sent]
                    sent += 1
                    yield {"event": "delta", "text": piece}

                if st.done:
                    yield {
                        "event": "done",
                        "text": st.full or "".join(st.deltas),
                        "status": st.status,
                    }
                    return


# Process-wide bus used by pipeline + API
BUS = SummaryBus()
