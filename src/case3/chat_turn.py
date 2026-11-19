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


_MEMORY_AT = (
    "\n\nКарточка этого чата",
    "\n\nРазговор этого чата",
    "\n\nПредыдущий ход этого чата",
    "\n\nОдин прошлый ход",
    "\n\nТребования UI:",
)
_CHOICE = re.compile(
    r"стоит (?P<doc>\d+(?:[.,]\d+)?%?), ты написал (?P<user>\d+(?:[.,]\d+)?%?)"
)
_INDEX_STEMS = frozenset(
    {
        "слайд",
        "пункт",
        "раздел",
        "глав",
        "строк",
        "таблиц",
        "график",
        "страниц",
        "рисун",
        "ход",
        "абзац",
    }
)
_STOP_STEMS = frozenset(
    {
        "был",
        "стал",
        "этот",
        "документ",
        "текст",
        "отчет",
        "отче",
        "чат",
        "сообщ",
        "напиш",
        "остав",
        "год",
        "числ",
        "сумм",
        "всег",
        "окол",
        "прим",
        "проц",
        "тольк",
        "потом",
        "затем",
        "котор",
        "нужн",
        "откры",
    }
)


def latest_user_line(intent: str | None) -> str:
    """The user's own words. Memory pasted after them is not a new statement."""
    text = intent or ""
    cut = len(text)
    for marker in _MEMORY_AT:
        at = text.find(marker)
        if at != -1:
            cut = min(cut, at)
    return text[:cut].strip()


def number_norms(text: str | None) -> set[str]:
    return {_norm_num(token) for token in _NUM.findall(text or "")}


def stray_numbers(text: str | None, allowed: set[str]) -> list[str]:
    """Number tokens in text that are not in the allowed set. Order kept."""
    found: list[str] = []
    seen: set[str] = set()
    for token in _NUM.findall(text or ""):
        norm = _norm_num(token)
        if norm in allowed or norm in seen:
            continue
        seen.add(norm)
        found.append(token)
    return found


def _words_before(text: str, start: int) -> list[str]:
    window = text[max(0, start - 48) : start]
    return re.findall(r"[0-9A-Za-zА-Яа-яЁё]{3,}", window)[-3:]


def _subject_word(text: str, start: int) -> str:
    from case3.chat_memory import _stem

    words = _words_before(text, start)
    picked = ""
    for word in words:
        stem = _stem(word)
        if stem in _INDEX_STEMS:
            continue
        if stem in _STOP_STEMS or len(stem) < 4:
            continue
        picked = word
    return picked


def _subjects_near(text: str, start: int) -> set[str]:
    from case3.chat_memory import _stem

    word = _subject_word(text, start)
    if not word:
        return set()
    return {_stem(word)}


def fact_conflict(user_text: str | None, source: str | None) -> tuple[str, str, str] | None:
    """User number and a different document number about the same word."""
    raw = user_text or ""
    doc = source or ""
    for hit in _NUM.finditer(raw):
        user_stems = _subjects_near(raw, hit.start())
        if not user_stems:
            continue
        user_norm = _norm_num(hit.group())
        same_subject_same_value = False
        for other in _NUM.finditer(doc):
            if _norm_num(other.group()) != user_norm:
                continue
            if user_stems & _subjects_near(doc, other.start()):
                same_subject_same_value = True
                break
        if same_subject_same_value:
            continue
        for other in _NUM.finditer(doc):
            if _norm_num(other.group()) == user_norm:
                continue
            if user_stems & _subjects_near(doc, other.start()):
                word = _subject_word(raw, hit.start())
                return word, other.group(), hit.group()
    return None


def conflict_question(word: str, doc: str, user: str) -> str:
    label = word[:1].upper() + word[1:] if word else "этом месте"
    return (
        f"В документе у «{label}» стоит {doc}, ты написал {user}. "
        f"Напиши {user}, чтобы оставить твоё, или {doc}, чтобы оставить документ."
    )


def invention_question(tokens: list[str]) -> str:
    shown = tokens[:3]
    if len(shown) == 1:
        names = f"числа {shown[0]}"
    else:
        names = "чисел " + " и ".join(shown)
    more = f" и ещё {len(tokens) - 3}" if len(tokens) > 3 else ""
    return (
        f"В документах и в твоём сообщении нет {names}{more}. "
        "Напиши нужное число, если его надо учесть, или напиши «без числа»."
    )


def _request_blob(intent: str) -> str:
    latest = latest_user_line(intent)
    earlier = re.findall(r"Запрос:\s*(.+)", intent or "")
    return "\n".join([latest, *earlier])


def _answering_choice(intent: str) -> bool:
    latest = latest_user_line(intent)
    if (
        len(latest) <= 80
        and re.search(r"без\s+числа", latest, re.IGNORECASE)
        and "В документах и в твоём сообщении нет" in (intent or "")
    ):
        return True
    found = _CHOICE.search(intent or "")
    if not found:
        return False
    latest = latest_user_line(intent)
    if len(latest) > 80:
        return False
    if number_norms(latest) & { _norm_num(found.group("doc")), _norm_num(found.group("user")) }:
        return True
    return bool(re.search(r"документ|твоё|твое|без числа", latest, re.IGNORECASE))


def choice_instruction(intent: str) -> tuple[str, set[str]]:
    """What the user picked, and number norms that pick removes."""
    found = _CHOICE.search(intent or "")
    if not found or not _answering_choice(intent):
        return "", set()
    doc, usr = found.group("doc"), found.group("user")
    latest = latest_user_line(intent)
    picked_doc = _norm_num(doc) in number_norms(latest) and _norm_num(usr) not in number_norms(latest)
    if picked_doc or re.search(r"как в документе|из документа|оставь документ", latest, re.IGNORECASE):
        return f"Пользователь выбрал {doc} из документа, не {usr}.", {_norm_num(usr)}
    if _norm_num(usr) in number_norms(latest) or re.search(r"моё|мое|как я", latest, re.IGNORECASE):
        return f"Пользователь выбрал {usr}, не {doc} из документа.", set()
    return "", set()


def _allowed_norms(source: str, intent: str, drop: set[str]) -> set[str]:
    have = number_norms(source) | number_norms(_request_blob(intent))
    return have - drop


def _ask_model(client: LLMClient, system: str, user_text: str) -> str:
    try:
        return _accepted(
            _speak(client, system=system, user_text=user_text, max_tokens=1400, on_delta=None)
        )
    except (LLMError, LLMConfigError, OSError, ValueError) as exc:
        log.warning("chat answer failed: %s", exc)
        return ""


def try_chat_answer(
    source: str,
    intent: str,
    *,
    client: LLMClient | None = None,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Full chat answer. No TeX.

    A number the user wrote is kept. A number neither they nor the document
    stated is not shown. A clash on the same word becomes one question.
    """
    note, drop = choice_instruction(intent)
    if not _answering_choice(intent):
        clash = fact_conflict(latest_user_line(intent), source)
        if clash:
            question = conflict_question(*clash)
            if on_delta:
                on_delta(question)
            return question

    system = load_prompt("chat_answer").strip()
    user = _user_block(source, intent)
    if note:
        user += "\n\n" + note
    llm = client or _client(1400, 90.0)
    allowed = _allowed_norms(source, intent, drop)
    text = _ask_model(llm, system, user)
    stray = stray_numbers(text, allowed) if text else []
    if stray:
        retry = (
            user
            + "\n\nПовтор: не пиши числа, которых нет в сообщении и в тексте: "
            + ", ".join(stray)
            + ". Если цифры не хватает, так и напиши, без новой цифры."
        )
        text = _ask_model(llm, system, retry)
        stray = stray_numbers(text, allowed) if text else []
    if stray:
        spoken = invention_question(stray)
    else:
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
    user_text: str = "",
    client: LLMClient | None = None,
) -> str:
    """One replacement paragraph. Empty when the draft adds a number or fails.

    A number the user wrote in this message is allowed. A number from neither
    the section, the source, nor that message is not.
    """
    system = load_prompt("chat_section").strip()
    task = _BRIEF_LINE.get(brief, _BRIEF_LINE["prettier"])
    said = (user_text or "").strip()[:500]
    user = (
        f"Раздел: {(section or 'Раздел').strip()[:80]}\n"
        f"Задача: {task}\n\n"
        f"СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:\n{said or '(нет)'}\n\n"
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
    allowed = f"{current}\n{source}\n{said}"
    if not text or not _numbers_grounded(text, allowed):
        return ""
    return " ".join(text.split())
