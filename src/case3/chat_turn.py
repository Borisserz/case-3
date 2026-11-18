"""Chat reply and the line spoken before an artifact job."""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from typing import Callable

from case3.chat_summary import is_clean_chat_summary
from case3.llm_client import LLMClient, LLMConfig, LLMConfigError, LLMError
from case3.prompts import load as load_prompt

log = logging.getLogger(__name__)

_KIND_LABEL = {
    "report": "отчёт",
    "diagram": "схему",
    "presentation": "презентацию",
}

_DONE_CLAIM = re.compile(r"(?i)\b(готово|собрано|pdf готов|презентац\w* готов\w*)\b")
_NUM = re.compile(r"\d+(?:[.,]\d+)?%?")

_BRIEF_LINE = {
    "clearer": "Сделай формулировку точнее. Смысл и числа те же.",
    "tighter": "Сделай короче. Смысл и числа те же.",
    "dislike": "Перепиши так, чтобы читалось яснее. Смысл и числа те же.",
    "prettier": "Сделай абзац ровнее и яснее. Смысл и числа те же.",
}


def opening_fallback(kind: str, user_text: str) -> str:
    """Local line when the opening model is unavailable. Does not claim the file is done."""
    label = _KIND_LABEL.get(kind, "материал")
    topic = " ".join((user_text or "").split())
    if len(topic) > 90:
        topic = topic[:89].rstrip() + "…"
    if topic:
        return (
            f"Соберу {label} по этому запросу: {topic}. "
            "Возьму только то, что уже написано, и ничего не допишу."
        )
    return (
        f"Соберу {label} по приложенным данным. "
        "Числа возьму только оттуда."
    )


def chat_fallback() -> str:
    return (
        "Не удалось получить ответ модели. "
        "Повторите вопрос или пришлите текст, который нужно разобрать."
    )


def _clip_source(source: str, limit: int = 6000) -> str:
    text = (source or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _user_block(source: str, intent: str) -> str:
    parts = []
    src = _clip_source(source)
    ask = " ".join((intent or "").split())
    if ask:
        parts.append("СООБЩЕНИЕ:\n" + ask[:2000])
    if src and src != ask:
        parts.append("ТЕКСТ:\n" + src)
    elif src:
        parts.append("ТЕКСТ:\n" + src)
    return "\n\n".join(parts) or "(пусто)"


def _speak(
    client: LLMClient,
    *,
    system: str,
    user_text: str,
    max_tokens: int,
    on_delta: Callable[[str], None] | None,
) -> str:
    parts: list[str] = []

    def emit(piece: str) -> None:
        if not piece:
            return
        parts.append(piece)
        if on_delta:
            on_delta(piece)

    if hasattr(client, "stream"):
        for piece in client.stream(
            system=system,
            user_text=user_text,
            reasoning="off",
            max_tokens=max_tokens,
        ):
            emit(piece or "")
    else:
        emit(
            client.complete(
                system=system,
                user_text=user_text,
                reasoning="off",
            )
        )
    return "".join(parts).strip()


def _client(max_tokens: int, timeout_s: float) -> LLMClient:
    cfg = LLMConfig.from_env()
    return LLMClient(
        replace(
            cfg,
            timeout_s=min(float(cfg.timeout_s), timeout_s),
            max_retries=0,
            max_tokens=max_tokens,
            reasoning="off",
        )
    )


def _accepted(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned or _DONE_CLAIM.search(cleaned) or not is_clean_chat_summary(cleaned):
        return ""
    return cleaned


def try_opening(
    kind: str,
    user_text: str,
    *,
    client: LLMClient | None = None,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Short line before the artifact job. Always returns Russian text."""
    fallback = opening_fallback(kind, user_text)
    system = load_prompt("chat_opening").strip()
    user = (
        f"Артефакт: {_KIND_LABEL.get(kind, kind)}.\n"
        f"Запрос:\n{(user_text or '').strip()[:1500] or '(только вложение)'}"
    )
    text = ""
    try:
        llm = client or _client(320, 25.0)
        text = _accepted(
            _speak(llm, system=system, user_text=user, max_tokens=320, on_delta=None)
        )
    except (LLMError, LLMConfigError, OSError, ValueError) as exc:
        log.warning("opening failed: %s", exc)
        text = ""
    spoken = text or fallback
    if on_delta:
        on_delta(spoken)
    return spoken


def try_chat_answer(
    source: str,
    intent: str,
    *,
    client: LLMClient | None = None,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Full chat answer. No TeX. Falls back to a short apology, never invented facts."""
    system = load_prompt("chat_answer").strip()
    user = _user_block(source, intent)
    text = ""
    try:
        llm = client or _client(1400, 90.0)
        text = _accepted(
            _speak(llm, system=system, user_text=user, max_tokens=1400, on_delta=None)
        )
    except (LLMError, LLMConfigError, OSError, ValueError) as exc:
        log.warning("chat answer failed: %s", exc)
        text = ""
    spoken = text or chat_fallback()
    if on_delta:
        on_delta(spoken)
    return spoken


def _norm_num(token: str) -> str:
    return token.replace(",", ".").replace("%", "")


def _numbers_grounded(draft: str, allowed: str) -> bool:
    have = {_norm_num(token) for token in _NUM.findall(allowed or "")}
    return all(_norm_num(token) in have for token in _NUM.findall(draft or ""))


def draft_section(
    *,
    section: str,
    current: str,
    source: str,
    brief: str,
    client: LLMClient | None = None,
) -> str:
    """One replacement paragraph. Empty when the draft adds a number or fails."""
    system = load_prompt("chat_section").strip()
    task = _BRIEF_LINE.get(brief, _BRIEF_LINE["prettier"])
    user = (
        f"Раздел: {(section or 'Раздел').strip()[:80]}\n"
        f"Задача: {task}\n\n"
        f"ТЕКСТ РАЗДЕЛА:\n{(current or '').strip()[:4000]}\n\n"
        f"SOURCE:\n{_clip_source(source)}"
    )
    text = ""
    try:
        llm = client or _client(500, 40.0)
        text = _accepted(
            _speak(llm, system=system, user_text=user, max_tokens=500, on_delta=None)
        )
    except (LLMError, LLMConfigError, OSError, ValueError) as exc:
        log.warning("section draft failed: %s", exc)
        text = ""
    if not text or not _numbers_grounded(text, f"{current}\n{source}"):
        return ""
    return " ".join(text.split())
