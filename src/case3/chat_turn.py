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
# A year or a rank is not a rival cell. «за 2025», «1 место», «в 2 раза».
_ASIDE_YEAR = re.compile(r"(?:19|20)\d{2}")
_ASIDE_AFTER = re.compile(r"^\s*(?:место|раз|раза)\b", re.IGNORECASE)
# Spaced thousands are one value: «105 865,2», not 105 and 865,2.
_NUM = re.compile(
    r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?%?"
    r"|\d+(?:\\,\d{3})+(?:[.,]\d+)?%?"
    r"|\d+(?:[.,]\d+)?%?"
)
# Longer stems first so «двадцать» is not read as «два».
_SPOKEN_NUMBER = (
    ("девятнадцат", "19"),
    ("восемнадцат", "18"),
    ("семнадцат", "17"),
    ("шестнадцат", "16"),
    ("пятнадцат", "15"),
    ("четырнадцат", "14"),
    ("тринадцат", "13"),
    ("двенадцат", "12"),
    ("одиннадцат", "11"),
    ("девяност", "90"),
    ("восьмидесят", "80"),
    ("семидесят", "70"),
    ("шестидесят", "60"),
    ("пятидесят", "50"),
    ("тридцат", "30"),
    ("двадцат", "20"),
    ("четыр", "4"),
    ("девят", "9"),
    ("восем", "8"),
    ("десять", "10"),
    ("сорок", "40"),
    ("шест", "6"),
    ("пять", "5"),
    ("семь", "7"),
    ("три", "3"),
    ("сто", "100"),
    ("две", "2"),
    ("два", "2"),
)
_SPOKEN_RE = re.compile(
    r"\b(?:"
    + "|".join(stem for stem, _digit in _SPOKEN_NUMBER)
    + r")(?:ь|и|ю|е|а|у|о)?\b",
    re.IGNORECASE,
)
_SPOKEN_VALUE = {stem: digit for stem, digit in _SPOKEN_NUMBER}

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


def _source_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _fit_front(paras: list[str], budget: int) -> tuple[list[str], int]:
    from case3.chat_memory import _clip_prose

    chosen: list[str] = []
    used = 0
    for index, para in enumerate(paras):
        gap = 2 if chosen else 0
        if used + gap + len(para) <= budget:
            chosen.append(para)
            used += gap + len(para)
            continue
        room = budget - used - gap
        if room > 80 and not chosen:
            chosen.append(_clip_prose(para, room))
            return chosen, index + 1
        break
    return chosen, len(chosen)


def _fit_back(paras: list[str], budget: int) -> tuple[list[str], int]:
    chosen: list[str] = []
    used = 0
    start = len(paras)
    for index in range(len(paras) - 1, -1, -1):
        para = paras[index]
        gap = 2 if chosen else 0
        if used + gap + len(para) <= budget:
            chosen.append(para)
            used += gap + len(para)
            start = index
            continue
        room = budget - used - gap
        if room > 80:
            piece = para[-room:].lstrip()
            if len(para) > room:
                piece = "…" + piece
            chosen.append(piece)
            start = index
        break
    chosen.reverse()
    return chosen, start


def _focus_hits(para: str, stems: set[str]) -> int:
    from case3.chat_memory import _stem

    if not stems:
        return 0
    found = {
        _stem(word)
        for word in re.findall(r"[0-9A-Za-zА-Яа-яЁё]{4,}", para)
    }
    return len(stems & found)


def _focus_table(para: str, stems: set[str], budget: int) -> str | None:
    """Header plus the rows that name the question. A markdown table is one paragraph."""
    lines = [line.rstrip() for line in (para or "").splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].lstrip().startswith("|"):
        return None
    header = [lines[0]]
    rest = lines[1:]
    if rest and re.match(r"^\|?[\s\-:|]+\|?$", rest[0].strip()):
        header.append(rest[0])
        rest = rest[1:]
    hits = [row for row in rest if _focus_hits(row, stems) >= 1]
    chosen = hits or rest[:4]
    kept = list(header)
    for row in chosen:
        trial = "\n".join(kept + [row])
        if len(trial) > budget:
            break
        kept.append(row)
    return "\n".join(kept)


def _clip_source(source: str, limit: int = 6000, focus: str = "") -> str:
    """Head, paragraphs that match the question, then the tail.

    A short document is unchanged. A long one stays inside ``limit``.
    A markdown table keeps its header and the rows the question names.
    """
    text = (source or "").strip()
    if len(text) <= limit:
        return text
    from case3.chat_memory import _query_stems

    stems = set(_query_stems(focus or ""))
    paras = [
        _focus_table(para, stems, min(limit, 2200)) or para
        for para in _source_paragraphs(text)
    ]
    if not paras:
        return text[: limit - 1].rstrip() + "…"
    head, head_n = _fit_front(paras, max(200, (limit * 2) // 5))
    tail, tail_at = _fit_back(paras, max(200, limit // 4))
    if head_n > tail_at:
        chunks = [part for part in ("\n\n".join(head), "\n\n".join(tail)) if part]
        body = "\n\n…\n\n".join(chunks)
        if len(body) <= limit:
            return body
        return body[: limit - 1].rstrip() + "…"
    middle = paras[head_n:tail_at]
    ranked = sorted(
        range(len(middle)),
        key=lambda index: (-_focus_hits(middle[index], stems), index),
    )
    used = len("\n\n".join(head)) + len("\n\n".join(tail)) + 12
    picked: list[tuple[int, str]] = []
    for index in ranked:
        if _focus_hits(middle[index], stems) < 1:
            break
        para = middle[index]
        if used + len(para) + 2 > limit:
            continue
        picked.append((index, para))
        used += len(para) + 2
    picked.sort(key=lambda item: item[0])
    chunks = ["\n\n".join(head)]
    if picked:
        chunks.append("\n\n".join(para for _index, para in picked))
    if tail:
        chunks.append("\n\n".join(tail))
    body = "\n\n…\n\n".join(chunk for chunk in chunks if chunk)
    if len(body) <= limit:
        return body
    return body[: limit - 1].rstrip() + "…"


# format_thread keeps eight turns as paragraphs and the rest as short lines.
# A legal 48-hop thread stays under this cap
# (test_fattest_legal_thread_is_pasted_whole). The cap only stops a runaway
# blob. 150000 characters is about 75–95k tokens of Russian.
_MEMORY_CAP = 150_000
_CHAT_ANSWER_TOKENS = 4096
_PIN_BITS = (
    "не Source",
    "не источник",
    "Числа и факты бери только из",
)


def _split_message(intent: str) -> tuple[str, str]:
    """User words, then the memory blocks pasted after them."""
    text = intent or ""
    cut = len(text)
    for marker in _MEMORY_AT:
        at = text.find(marker)
        if at != -1:
            cut = min(cut, at)
    return text[:cut].strip(), text[cut:].strip()


def _end_slice(text: str, limit: int) -> str:
    """Keep the end of one over-long line, on a word break when it is close."""
    if len(text) <= limit:
        return text
    if limit <= 1:
        return ""
    piece = text[-(limit - 1) :]
    spot = piece.find(" ")
    if 0 < spot <= 40:
        piece = piece[spot + 1 :]
    return "…" + piece


_TURN_START = (
    "Ход ",
    "Начало:",
    "Раньше:",
    "Дальше:",
    "Ответ",
    "Последняя правка",
    "Один прошлый",
    "Запрос:",
    "Карточка",
    "Предыдущий",
)
# A new block. An unlabeled line before one of these is the cut edge of an
# older turn. A line before «Ответ» or «Дальше» is the previous paragraph.
_NEW_BLOCK = (
    "Ход ",
    "Начало:",
    "Раньше:",
    "Один прошлый",
    "Карточка",
    "Предыдущий",
    "Последняя правка",
)
_PIN_MAX = 240
_MESSAGE_CAP = 6000


def _on_turn_boundary(line: str) -> bool:
    return line.startswith(_TURN_START) or (
        len(line) <= _PIN_MAX and any(bit in line for bit in _PIN_BITS)
    )


def _is_pin(line: str) -> bool:
    """Short grounding line. A long answer that mentions the phrase is not one."""
    return len(line) <= _PIN_MAX and any(bit in line for bit in _PIN_BITS)


def _pack_tail(lines: list[str], limit: int) -> list[str]:
    if limit <= 1:
        return []
    chosen: list[str] = []
    used = 0
    for line in reversed(lines):
        need = len(line) + (1 if chosen else 0)
        if used + need > limit:
            if not chosen:
                chosen.append(_end_slice(line, limit))
            break
        chosen.append(line)
        used += need
    chosen.reverse()
    return chosen


def _snap_before_new_block(chosen: list[str]) -> list[str]:
    while len(chosen) > 1 and not _on_turn_boundary(chosen[0]):
        if not chosen[1].startswith(_NEW_BLOCK):
            break
        chosen.pop(0)
    return chosen


def _dropped_pins(lines: list[str], tail: str) -> list[str]:
    kept = set(tail.split("\n"))
    pins: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not _is_pin(line) or line in seen or line in kept:
            continue
        seen.add(line)
        pins.append(line)
    return pins


def _keep_tail(text: str, limit: int) -> str:
    """Drop old lines first. The latest answer stays. Short grounding lines stay."""
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    lines = body.split("\n")
    chosen = _snap_before_new_block(_pack_tail(lines, limit))
    tail = "\n".join(chosen).strip()
    pins = _dropped_pins(lines, tail)
    pin = "\n".join(pins)
    if not pin:
        return tail
    glued = pin + "\n…\n" + tail
    if len(glued) <= limit:
        return glued
    room = limit - len(pin) - len("\n…\n")
    if room <= 1:
        return _end_slice(body, limit)
    chosen = _snap_before_new_block(_pack_tail(tail.split("\n"), room))
    tail = "\n".join(chosen).strip()
    if not tail:
        return pin
    return pin + "\n…\n" + tail


def _keep_question(text: str, limit: int = _MESSAGE_CAP) -> str:
    """The current question. Over the cap, keep the opening and the last paragraph."""
    from case3.chat_memory import _clip_prose

    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(raw) <= limit:
        return _clip_prose(raw, limit)
    head_budget = max(1, (limit * 2) // 3)
    tail_budget = max(1, limit - head_budget - 5)
    head = _clip_prose(raw, head_budget)
    piece = raw[-tail_budget:]
    for sep in ("\n\n", "\n", ". "):
        spot = piece.find(sep)
        if 0 <= spot <= 180:
            piece = piece[spot + len(sep) :].lstrip()
            break
    piece = piece.strip()
    if not piece or piece in head:
        return head
    return head + "\n\n…\n\n" + piece


_MD_HEADING = re.compile(r"^(#{1,3})[ \t]+(\S.*?)\s*$", re.MULTILINE)


def _source_outline(text: str, limit: int = 1200) -> str:
    titles: list[str] = []
    for match in _MD_HEADING.finditer(text or ""):
        title = " ".join(match.group(2).split())
        if title:
            titles.append(f"{match.group(1)} {title}")
    if not titles:
        return ""
    body = "\n".join(titles)
    if len(body) > limit:
        body = body[: limit - 1].rstrip() + "…"
    return "Оглавление документа:\n" + body


def _user_block(source: str, intent: str) -> str:
    """Question, document, then memory.

    The question keeps its paragraphs, and its last paragraph if it is long.
    Memory is cut from the front, so the latest answer is the last thing in
    the prompt when the chain is long.
    """
    message, memory = _split_message(intent or "")
    message = _keep_question(message)
    memory = _keep_tail(memory, _MEMORY_CAP)
    src = _clip_source(source, focus=message)
    if len((source or "").strip()) > 6000:
        outline = _source_outline(source)
        if outline and src:
            src = outline + "\n\n" + src
        elif outline:
            src = outline
    parts: list[str] = []
    if message:
        parts.append("СООБЩЕНИЕ:\n" + message)
    if src and src != message:
        parts.append("ТЕКСТ:\n" + src)
    elif src and not message:
        parts.append("ТЕКСТ:\n" + src)
    if memory:
        parts.append(memory)
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


def _accepted(text: str, *, block_done: bool = False) -> str:
    """Keep a chat answer that says «собрано». Block that word only in the opening line."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if block_done and _DONE_CLAIM.search(cleaned):
        return ""
    if not is_clean_chat_summary(cleaned):
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
            _speak(llm, system=system, user_text=user, max_tokens=320, on_delta=None),
            block_done=True,
        )
    except (LLMError, LLMConfigError, OSError, ValueError) as exc:
        log.warning("opening failed: %s", exc)
        text = ""
    spoken = text or fallback
    if on_delta:
        on_delta(spoken)
    return spoken


_MEMORY_AT = (
    "\n\nЧисла из реплик пользователя",
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
        # Column words on every dashboard row. A named region still conflicts.
        "область",
        "област",
        "регион",
        "район",
    }
)


def _aside_number(text: str, match: re.Match[str]) -> bool:
    """True when this digit is a period or a rank, not a cell the user is correcting."""
    token = match.group(0).replace("%", "")
    if _ASIDE_YEAR.fullmatch(token):
        return True
    return bool(_ASIDE_AFTER.match(text[match.end() : match.end() + 16]))


def latest_user_line(intent: str | None) -> str:
    """The user's own words. Memory pasted after them is not a new statement."""
    text = intent or ""
    cut = len(text)
    for marker in _MEMORY_AT:
        at = text.find(marker)
        if at != -1:
            cut = min(cut, at)
    return text[:cut].strip()


def spoken_number_norms(text: str | None) -> set[str]:
    """Cardinals written as words. «двенадцать» is 12. «один» is not a number."""
    found: set[str] = set()
    for match in _SPOKEN_RE.finditer(text or ""):
        stem = match.group(0).casefold().replace("ё", "е")
        for prefix, digit in _SPOKEN_NUMBER:
            if stem.startswith(prefix):
                found.add(digit)
                break
    return found


def number_norms(text: str | None) -> set[str]:
    return {_norm_num(token) for token in _NUM.findall(text or "")} | spoken_number_norms(
        text
    )


def user_stated_norms(intent: str | None) -> set[str]:
    """Norms from the one user-number line. The rest of the thread is ignored."""
    text = intent or ""
    mark = "Числа из реплик пользователя"
    at = text.find(mark)
    if at < 0:
        return set()
    rest = text[at + len(mark) :]
    line = rest.split("\n", 1)[0]
    body = rest.split("\n", 1)[1] if "\n" in rest else ""
    body = body.split("\n", 1)[0]
    return number_norms(body if body.strip() else line)


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
    for match in _SPOKEN_RE.finditer(text or ""):
        word = match.group(0)
        stem = word.casefold().replace("ё", "е")
        digit = ""
        for prefix, value in _SPOKEN_NUMBER:
            if stem.startswith(prefix):
                digit = value
                break
        if not digit or digit in allowed or digit in seen:
            continue
        seen.add(digit)
        found.append(word)
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


def _fact_words(text: str, start: int) -> list[tuple[str, str]]:
    """Content words before a number, nearest last. «кассе теперь 30» keeps both."""
    from case3.chat_memory import _stem

    found: list[tuple[str, str]] = []
    for word in _words_before(text, start):
        stem = _stem(word)
        if stem in _INDEX_STEMS or stem in _STOP_STEMS or len(stem) < 4:
            continue
        found.append((word, stem))
    return found


def _subjects_near(text: str, start: int) -> set[str]:
    return {stem for _word, stem in _fact_words(text, start)}


def _nearest_stem(text: str, start: int) -> str:
    words = _fact_words(text, start)
    return words[-1][1] if words else ""


_CHANGE_PREFIXES = ("вырос", "сниз", "упа", "прирос", "измен", "увелич", "сократ", "паден")


def _claim_words(text: str, start: int, token: str) -> list[tuple[str, str]]:
    """A growth percent belongs to the verb, not the noun before it."""
    words = _fact_words(text, start)
    if token.endswith("%") and words and words[-1][1].startswith(_CHANGE_PREFIXES):
        return [words[-1]]
    return words


def fact_conflict(user_text: str | None, source: str | None) -> tuple[str, str, str] | None:
    """User number and a different document number about the same word."""
    raw = user_text or ""
    doc = source or ""
    for hit in _NUM.finditer(raw):
        if _aside_number(raw, hit):
            continue
        pairs = _claim_words(raw, hit.start(), hit.group())
        user_stems = {stem for _word, stem in pairs}
        if not user_stems:
            continue
        user_norm = _norm_num(hit.group())
        same_subject_same_value = False
        for other in _NUM.finditer(doc):
            if _norm_num(other.group()) != user_norm:
                continue
            # The same digit on a later metric does not excuse this one.
            if _nearest_stem(doc, other.start()) in user_stems:
                same_subject_same_value = True
                break
        if same_subject_same_value:
            continue
        for other in _NUM.finditer(doc):
            if _norm_num(other.group()) == user_norm:
                continue
            shared = user_stems & _subjects_near(doc, other.start())
            if not shared:
                continue
            word = ""
            for surface, stem in pairs:
                if stem in shared:
                    word = surface
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
    """Only the latest line. A «Запрос:» inside the thread is not an allow-list."""
    return latest_user_line(intent)


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
    have = number_norms(source) | number_norms(_request_blob(intent)) | user_stated_norms(intent)
    return have - drop


def _ask_model(client: LLMClient, system: str, user_text: str) -> str:
    try:
        return _accepted(
            _speak(
                client,
                system=system,
                user_text=user_text,
                max_tokens=_CHAT_ANSWER_TOKENS,
                on_delta=None,
            )
        )
    except (LLMError, LLMConfigError, OSError, ValueError) as exc:
        log.warning("chat answer failed: %s", exc)
        return ""


_ASK_STOP_WORDS = (
    "отчёт",
    "отчет",
    "раздел",
    "текст",
    "документ",
    "чат",
    "файл",
    "вопрос",
    "сообщение",
    "ответ",
    "этот",
    "эта",
)
_SECTION_CAP = 3500
_OUTLINE_CAP = 24


def _content_words(text: str) -> list[str]:
    from case3.chat_memory import _stem

    stems: list[str] = []
    for word in re.findall(r"[0-9A-Za-zА-Яа-яЁё]+", text or ""):
        stem = _stem(word)
        if len(stem) >= 4:
            stems.append(stem)
    return stems


def _same_topic(left: str, right: str) -> bool:
    """«введении» and «введение» keep one letter of difference after stemming."""
    if left == right:
        return True
    short, long = (left, right) if len(left) <= len(right) else (right, left)
    return len(short) >= 5 and long.startswith(short)


def _heading_score(title: str, needles: list[str]) -> float:
    title_stems = _content_words(title)
    if not title_stems or not needles:
        return 0.0
    hits = sum(
        1 for stem in title_stems if any(_same_topic(stem, needle) for needle in needles)
    )
    if hits == 0:
        return 0.0
    return hits / len(title_stems)


def _named_heading(question: str, titles: list[str]) -> tuple[str, str]:
    """(heading title, name the user asked). Title is empty when nothing matches."""
    from case3.chat_act import section_target
    from case3.chat_memory import _stem

    asked = section_target(latest_user_line(question))
    if asked:
        needles = _content_words(asked)
        best = ""
        best_score = 0.0
        for title in titles:
            score = _heading_score(title, needles)
            if score > best_score:
                best_score = score
                best = title
        return best, asked
    stop = {_stem(word) for word in _ASK_STOP_WORDS}
    needles = [stem for stem in _content_words(latest_user_line(question)) if stem not in stop]
    scored = [(_heading_score(title, needles), title) for title in titles]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or (len(scored) > 1 and scored[0][0] == scored[1][0]):
        return "", ""
    return scored[0][1], ""


def _table_prose(block: dict) -> str:
    lines: list[str] = []
    caption = str(block.get("caption") or "").strip()
    if caption:
        lines.append("Таблица: " + caption)
    headers = [str(cell).strip() for cell in (block.get("headers") or [])]
    if headers:
        lines.append(" | ".join(headers))
    rows = [row for row in (block.get("rows") or []) if isinstance(row, list)]
    for row in rows:
        lines.append(" | ".join(str(cell).strip() for cell in row))
    return "\n".join(lines)


def _section_prose(blocks: list[dict], title: str) -> str:
    from case3.chat_memory import _clip_prose

    start = -1
    level = 1
    for index, block in enumerate(blocks):
        if block.get("type") == "heading" and str(block.get("text") or "").strip() == title:
            start = index
            level = int(block.get("level") or 1)
            break
    if start < 0:
        return ""
    parts: list[str] = []
    for block in blocks[start + 1 :]:
        kind = block.get("type")
        if kind == "heading" and int(block.get("level") or 1) <= level:
            break
        if kind == "heading":
            text = str(block.get("text") or "").strip()
        elif kind == "paragraph":
            text = str(block.get("text") or "").strip()
        elif kind == "list":
            rows = [
                "- " + str((item or {}).get("text") or "").strip()
                for item in (block.get("items") or [])
                if str((item or {}).get("text") or "").strip()
            ]
            text = "\n".join(rows)
        elif kind == "table":
            text = _table_prose(block)
        elif kind == "figure":
            caption = str(block.get("caption") or "").strip()
            text = "Рисунок: " + caption if caption else ""
        else:
            text = ""
        if text:
            parts.append(text)
    return _clip_prose("\n\n".join(parts), _SECTION_CAP)


def report_context(tex: str, question: str) -> str:
    """Outline plus the named section. Empty when this chat has no report.

    The block is labeled not-Source. Numbers in it stay illegal unless Source
    or the user's own message already has them.
    """
    from case3.tex_preview import tex_to_preview_blocks

    data = tex_to_preview_blocks(tex or "")
    blocks = [block for block in (data.get("blocks") or []) if isinstance(block, dict)]
    headings = [
        (str(block.get("text") or "").strip(), int(block.get("level") or 1))
        for block in blocks
        if block.get("type") == "heading" and str(block.get("text") or "").strip()
    ]
    if not headings:
        return ""
    lines = [
        "Открытый отчёт (не Source).",
        "Числа и факты бери только из текста документов.",
        "Оглавление:",
    ]
    title = str(data.get("title") or "").strip()
    if title:
        lines.append("Название: " + title)
    for text, level in headings[:_OUTLINE_CAP]:
        pad = "  " if level > 1 else ""
        lines.append(f"{pad}- {text}")
    if len(headings) > _OUTLINE_CAP:
        lines.append("- …")
    found, asked = _named_heading(question, [text for text, _level in headings])
    if found:
        body = _section_prose(blocks, found)
        lines.append(f"Раздел «{found}»:")
        if body:
            lines.append(body)
    elif asked:
        lines.append(f"Раздела «{asked}» в отчёте нет.")
    return "\n".join(lines)


def chat_report_block(root, prior_run_id: str, user_text: str) -> str:
    """Report block for the chat that continues prior_run_id."""
    from pathlib import Path

    from case3.chat_memory import report_tex

    return report_context(report_tex(Path(root), prior_run_id or ""), user_text or "")


def limit_note(intent: str) -> str:
    """Tell the talk model that this line did not edit the file."""
    from case3.chat_act import _EDIT, _PROSE, _unsupported_shape, resolve_act

    line = latest_user_line(intent)
    if not line:
        return ""
    act = resolve_act(
        line,
        has_deck=True,
        has_report=True,
        has_diagram=True,
    )
    if act.kind != "talk":
        return ""
    if not (_EDIT.search(line) or _PROSE.search(line) or _unsupported_shape(line)):
        return ""
    return (
        "Файл не изменился.\n"
        "Ответь обычным предложением, без заголовка капсом: чего не умеешь, "
        "что рядом умеешь, и одну фразу, которую можно скопировать."
    )


def try_chat_answer(
    source: str,
    intent: str,
    *,
    client: LLMClient | None = None,
    on_delta: Callable[[str], None] | None = None,
    report: str = "",
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
    extra = (report or "").strip()
    if extra:
        user += "\n\n" + extra
    note_limit = limit_note(intent)
    if note_limit:
        user += "\n\n" + note_limit
    llm = client or _client(_CHAT_ANSWER_TOKENS, 180.0)
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
        kept = _without_stray(text, stray)
        if len(re.findall(r"[А-Яа-яЁё]", kept)) >= 12:
            spoken = kept
        else:
            spoken = invention_question(stray)
    else:
        spoken = text or chat_fallback()
    spoken = _hide_memory_marks(spoken)
    if on_delta:
        on_delta(spoken)
    return spoken


def _without_stray(text: str, stray: list[str]) -> str:
    """Drop a sentence whose only numbers are foreign. Keep the grounded sentences."""
    norms = {_norm_num(token) for token in stray}
    if not text or not norms:
        return text or ""
    kept_lines: list[str] = []
    for line in text.split("\n"):
        bits = re.split(r"([.!?]+(?:\s+|$))", line)
        kept: list[str] = []
        index = 0
        while index < len(bits):
            chunk = bits[index]
            delim = bits[index + 1] if index + 1 < len(bits) else ""
            index += 2 if delim else 1
            nums = {_norm_num(token) for token in _NUM.findall(chunk)}
            if nums and nums <= norms:
                continue
            if nums & norms:
                chunk = _NUM.sub(
                    lambda match: "" if _norm_num(match.group(0)) in norms else match.group(0),
                    chunk,
                )
            chunk = re.sub(r"[ \t]{2,}", " ", chunk).strip(" ,;")
            if not chunk:
                continue
            kept.append(chunk)
            if delim:
                kept.append(delim if delim.startswith((".", "!", "?")) else " ")
        if kept:
            kept_lines.append("".join(kept).strip())
    return "\n".join(kept_lines).strip()


def _hide_memory_marks(text: str) -> str:
    """The model must not read the memory labels aloud."""
    kept: list[str] = []
    for line in (text or "").split("\n"):
        bare = line.strip().lstrip("#").strip()
        if bare.startswith(
            (
                "Числа из реплик пользователя",
                "Разговор этого чата",
                "Карточка этого чата",
            )
        ):
            continue
        kept.append(
            line.replace("Числа из реплик пользователя", "твои числа")
            .replace("Разговор этого чата", "этот разговор")
            .replace("Карточка этого чата", "этот разговор")
        )
    return "\n".join(kept).strip()


def _norm_num(token: str) -> str:
    compact = re.sub(r"[ \u00a0\u202f]+", "", token or "")
    compact = compact.replace("\\,", "")
    return compact.replace(",", ".").replace("%", "")


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
        f"SOURCE:\n{_clip_source(source, focus=said)}"
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
