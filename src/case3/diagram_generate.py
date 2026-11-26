"""One Mermaid JSON call shared by diagram mode and its empty-draft recovery."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any, Protocol

DIAGRAM_SOURCE_LIMIT = 12_000
# Extra LLM attempts after the first when Mermaid fails the render check.
DEFAULT_RENDER_RETRIES = 2

log = logging.getLogger("case3.diagram_generate")


class _DiagramClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user_text: str,
        cancel_check: Callable[[], None] | None = None,
    ) -> str: ...


def diagram_prompts(
    *,
    intent: str | None,
    source_text: str,
    max_diagrams: int,
    palette: str,
    gcp_block: str | None = None,
) -> tuple[str, str]:
    """System + user text. Source is clipped to ``DIAGRAM_SOURCE_LIMIT``."""
    from case3.diagram_edit import _load_generate_system

    budget = max(1, int(max_diagrams))
    system = _load_generate_system(max_diagrams=budget, palette=palette)
    clipped = (source_text or "")[:DIAGRAM_SOURCE_LIMIT]
    gcp = (gcp_block or "").strip()
    user = f"## Intent\n{(intent or '').strip() or '(none)'}\n\n"
    if gcp:
        user += gcp + "\n\n"
    user += (
        f"## Source\n{clipped}\n\n"
        "Return ONLY one ```json fence with a diagrams array "
        f"(1–{budget} Mermaid). No prose before the fence."
    )
    return system, user


def diagrams_pass_render(
    diagrams: list[dict[str, Any]],
    render_ok: Callable[[str], bool],
) -> bool:
    """True when there is at least one diagram and every mermaid body passes ``render_ok``."""
    if not diagrams:
        return False
    for item in diagrams:
        if not isinstance(item, dict):
            return False
        body = str(item.get("mermaid") or item.get("code") or "").strip()
        if not body or not render_ok(body):
            return False
    return True


def _resolve_render_retries(max_render_retries: int | None) -> int:
    if max_render_retries is not None:
        return max(0, int(max_render_retries))
    raw = (os.environ.get("CASE3_DIAGRAM_RENDER_RETRIES") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return DEFAULT_RENDER_RETRIES


def complete_diagrams(
    *,
    intent: str | None,
    source_text: str,
    max_diagrams: int,
    client: _DiagramClient,
    palette: str,
    cancel_check: Callable[[], None] | None = None,
    gcp_block: str | None = None,
    render_ok: Callable[[str], bool] | None = None,
    max_render_retries: int | None = None,
) -> list[dict[str, Any]]:
    """Call ``client`` and parse diagrams; silently retry when Mermaid fails render check.

    May raise InsufficientDataError. After exhausting retries, returns the last draft
    (caller / UI may still surface a soft failure).
    """
    from case3.diagram_repair import parse_repair_response
    from case3.diagram_render import mermaid_syntax_ok

    system, user = diagram_prompts(
        intent=intent,
        source_text=source_text,
        max_diagrams=max_diagrams,
        palette=palette,
        gcp_block=gcp_block,
    )
    check = render_ok or mermaid_syntax_ok
    retries = _resolve_render_retries(max_render_retries)
    budget = max(1, int(max_diagrams))
    last: list[dict[str, Any]] = []

    for attempt in range(retries + 1):
        raw = client.complete(system=system, user_text=user, cancel_check=cancel_check)
        diagrams = parse_repair_response(raw or "", max_diagrams=budget)
        last = diagrams
        if diagrams_pass_render(diagrams, check):
            if attempt:
                log.info(
                    "diagram render OK after silent retry %d/%d",
                    attempt,
                    retries,
                )
            return diagrams
        if attempt < retries:
            log.warning(
                "diagram Mermaid failed render check (attempt %d/%d) — silent retry",
                attempt + 1,
                retries + 1,
            )
        else:
            log.warning(
                "diagram Mermaid still failing after %d attempts — returning last draft",
                retries + 1,
            )
    return last
