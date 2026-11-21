# Liber chat memory improvements — Implementation Plan

> **Closed 2026-11-21.** Tasks 1–8 are in the working tree. The allow-list decision is ADR-0015: ADR-0014 is already the dashboard. The refusal question still names a rejected model number, so the user can confirm it. The two-stem fixture pads with `_WINDOW` (48), not 6.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one Liber chat remember numbers the user actually wrote, obey a clear edit that ends with `?`, keep a diagram’s palette, show the outline of a long Source, lift an old turn only when the overlap is enough, edit the pixels of a photo already in the chat, delete a named section, and tell the user in chat when a request is outside that list.

**Architecture:** The chain stays a `prior_run_id` walk of at most 48 runs. Assistant prose stays off the allow-list. A new one-line block, built only from `chat_prompt` and `dialogue.user`, is pasted ahead of the thread and parsed back out by `user_stated_norms`. Edits stay on the ordered regexes in `resolve_act`. No second model, no embeddings.

**Tech Stack:** Python 3, pytest, existing `case3.chat_memory` / `chat_turn` / `chat_act` / `chat_revise` / `fact_ground` / `prior_turn`.

## Global Constraints

- Numbers the model wrote (`chat_summary`, `chat_opening`, `dialogue.assistant`, the open-report block, chart JSON) are not facts.
- A number may be repeated anywhere once it is allowed. The check is the value, not the nearby word. Do not build word-level grounding in this plan.
- Palettes stay `editorial` / `ocean` / `sunset` / `mono` / `atelier`. No purple.
- `resolve_act` stays the only edit router. Do not add a classifier model.
- User-facing strings stay Russian.
- `docs/` and `.agents/` are gitignored. Write ADR, KI, and `docs/MEMORY.md` on disk. Commit only `src/` and `tests/`.
- `draft_section` does not gain the user-number card. A rewrite may use numbers already in the paragraph, the Source, or the current message.
- In-place edits still do not open a new run.

## File structure

- `src/case3/chat_memory.py` — build the user-number line from raw turns. Raise the lift bar when the question has two content stems.
- `src/case3/prior_turn.py` — paste that line first in the prior block.
- `src/case3/chat_turn.py` — parse the line back into norms. Prepend a Source outline when the document is over 6000 characters.
- `src/case3/fact_ground.py` — one allow-list: Source ∪ current message ∪ user-number line.
- `src/case3/chat_act.py` — `?` blocks an edit only when the line has no imperative. Parse a photo-pixel phrase and a section-delete phrase.
- `src/case3/chat_revise.py` — diagram refine reads the run palette. Photo pixels go through `edit_figure_in_run(mode="edit")`. A named section is cut out of the TeX and the PDF is rebuilt once.
- `prompt/chat_answer.md` — the talk model’s menu of what a phrase can change and what it cannot. `try_chat_answer` adds one line when the router left the file alone.
- `docs/adr/0014-user-stated-numbers.md`, `docs/adr/README.md`, `.agents/knowledge/KI-chat-memory.md`, `docs/MEMORY.md` — the allow-list decision. Not committed.

Out of scope: deleting one paragraph while leaving its heading, table captions, chart series (the numbers on a bar or a line), diagram legends, speaker notes, a second router, parallel «сократи весь отчёт». A phrase that asks for a new picture («сделай фото цеха») stays a build. Pixel edit touches a PNG that is already in the chat.

---

### Task 1: Numbers the user wrote join the allow-list

**Files:**
- Modify: `src/case3/chat_memory.py` (after `format_card`)
- Modify: `src/case3/prior_turn.py` (`prior_block_for_form`)
- Modify: `src/case3/chat_turn.py` (`_MEMORY_AT`, new `user_stated_norms`, `_allowed_norms`)
- Modify: `src/case3/fact_ground.py` (`allowed_fact_norms`)
- Test: `tests/test_chat_turn.py`, `tests/test_fact_ground.py`, `tests/test_chat_memory.py`
- Docs (do not commit): `docs/adr/0014-user-stated-numbers.md`, `docs/adr/README.md`, `.agents/knowledge/KI-chat-memory.md`, `docs/MEMORY.md`

**Interfaces:**
- Consumes: turn dicts with `chat_prompt` and `dialogue[].user`. `_NUM` is `r"\d+(?:[.,]\d+)?%?"` in `chat_turn.py`.
- Produces:
  - `format_user_numbers(turns: list[dict] | None) -> str`
  - `user_stated_norms(intent: str | None) -> set[str]`
  - Marker text exactly: `Числа из реплик пользователя`
  - `allowed_fact_norms(source, intent)` includes `user_stated_norms(intent)`

The existing test `test_old_request_number_does_not_enter_the_answer` stays. A `77` that appears only inside `Разговор этого чата` is still rejected. The new block is the only door.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat_memory.py`:

```python
def test_user_number_line_keeps_user_tokens_and_drops_the_answer():
    from case3.chat_memory import format_user_numbers

    turns = [
        {
            "chat_prompt": "выручка 77",
            "chat_summary": "модель сказала 88",
            "dialogue": [
                {"user": "в кассе 12,5", "assistant": "оставил 99"},
            ],
        }
    ]
    line = format_user_numbers(turns)
    assert line.startswith("Числа из реплик пользователя")
    assert "77" in line
    assert "12,5" in line
    assert "88" not in line
    assert "99" not in line


def test_user_number_line_ignores_a_thread_pasted_into_the_prompt():
    from case3.chat_memory import format_user_numbers

    turns = [
        {
            "chat_prompt": (
                "что с кассой\n\n"
                "Разговор этого чата (не Source).\n"
                "Ход 1. Запрос: выручка 77\n"
                "Ответ: было 88."
            ),
            "chat_summary": "ок",
        }
    ]
    assert format_user_numbers(turns) == ""
```

Append to `tests/test_chat_turn.py`:

```python
def test_user_stated_number_enters_the_answer():
    intent = (
        "сколько я называл\n\n"
        "Числа из реплик пользователя (его слова, не ответ модели):\n"
        "77\n\n"
        "Разговор этого чата (не Source).\n"
        "Ход 1. Запрос: выручка 77\n"
        "Ответ: было."
    )
    client = _Seq(["Выручка 77.", "Выручка 77."])
    text = try_chat_answer("Касса была 20.", intent, client=client)
    assert "77" in text
    assert not text.startswith("В документах")


def test_answer_number_stays_out_when_the_card_lists_only_the_user():
    intent = (
        "что с кассой\n\n"
        "Числа из реплик пользователя (его слова, не ответ модели):\n"
        "77\n\n"
        "Разговор этого чата (не Source).\n"
        "Ответ: модель написала 88."
    )
    client = _Seq(["Там 88.", "Там 88."])
    text = try_chat_answer("Касса была 20.", intent, client=client)
    assert "88" not in text
```

Append to `tests/test_fact_ground.py`:

```python
def test_user_stated_number_stays_in_a_new_report_and_the_answer_number_goes():
    from case3.fact_ground import ground_generated

    intent = (
        "собери отчёт\n\n"
        "Числа из реплик пользователя (его слова, не ответ модели):\n"
        "77\n\n"
        "Разговор этого чата (не Source).\n"
        "Ответ: было 88."
    )
    tex = (
        "\\documentclass{article}\n\\begin{document}\n"
        "Выручка 77. Модель дописала 88.\n"
        "\\end{document}\n"
    )
    out, charts, figures, diagrams, dropped = ground_generated(
        tex, [], [], [], source="Касса 20.", intent=intent
    )
    assert "77" in out
    assert "88" not in out
    assert "88" in dropped
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `pytest tests/test_chat_memory.py::test_user_number_line_keeps_user_tokens_and_drops_the_answer tests/test_chat_memory.py::test_user_number_line_ignores_a_thread_pasted_into_the_prompt tests/test_chat_turn.py::test_user_stated_number_enters_the_answer tests/test_chat_turn.py::test_answer_number_stays_out_when_the_card_lists_only_the_user tests/test_fact_ground.py::test_user_stated_number_stays_in_a_new_report_and_the_answer_number_goes -v`

Expected: FAIL. `format_user_numbers` and the allow-list path do not exist yet. `77` is still stripped from the chat answer.

- [ ] **Step 3: Implement the line, the parser, and the allow-list**

In `src/case3/chat_memory.py`, after `format_card`:

```python
_USER_NUMBER_MARK = "Числа из реплик пользователя"
_USER_NUMBER_CAP = 40
_PROMPT_CUTS = (
    "Требования UI:",
    "Разговор этого чата",
    "Карточка этого чата",
    "Один прошлый ход",
    "Предыдущий ход этого чата",
    _USER_NUMBER_MARK,
)


def _user_words(value: object) -> str:
    text = str(value or "")
    for marker in _PROMPT_CUTS:
        at = text.find(marker)
        if at != -1:
            text = text[:at]
    return text


def user_number_tokens(turns: list[dict[str, Any]] | None) -> list[str]:
    """Spellings the user wrote. Assistant fields are not scanned."""
    from case3.chat_turn import _NUM, _norm_num

    found: list[str] = []
    seen: set[str] = set()
    for turn in turns or []:
        if not isinstance(turn, dict):
            continue
        blobs = [_user_words(turn.get("chat_prompt"))]
        for note in turn.get("dialogue") or []:
            if isinstance(note, dict):
                blobs.append(_user_words(note.get("user")))
        for blob in blobs:
            for token in _NUM.findall(blob):
                norm = _norm_num(token)
                if not norm or norm in seen:
                    continue
                seen.add(norm)
                found.append(token)
                if len(found) >= _USER_NUMBER_CAP:
                    return found
    return found


def format_user_numbers(turns: list[dict[str, Any]] | None) -> str:
    tokens = user_number_tokens(turns)
    if not tokens:
        return ""
    return (
        f"{_USER_NUMBER_MARK} (его слова, не ответ модели):\n"
        + ", ".join(tokens)
    )
```

`chat_memory` already imports nothing from `chat_turn` at module level. Keep the import inside the function. `chat_turn` imports `chat_memory` only inside functions, so this does not cycle at import time.

In `src/case3/prior_turn.py`, inside `prior_block_for_form`, add `format_user_numbers` to the import from `case3.chat_memory` and put it first:

```python
    from case3.chat_memory import (
        _source_file,
        format_card,
        format_thread,
        format_user_numbers,
        load_chain,
        memory_card,
        recall_block,
    )
    # ... existing source walk ...
    parts = [
        format_user_numbers(chain),
        format_card(memory_card(chain, source)),
        format_thread(chain) or format_prior_turn(meta),
        recall_block(chain, user_text),
    ]
```

In `src/case3/chat_turn.py`, add the marker to `_MEMORY_AT` so `latest_user_line` still excludes it:

```python
_MEMORY_AT = (
    "\n\nЧисла из реплик пользователя",
    "\n\nКарточка этого чата",
    "\n\nРазговор этого чата",
    "\n\nПредыдущий ход этого чата",
    "\n\nОдин прошлый ход",
    "\n\nТребования UI:",
)
```

Add next to `number_norms`:

```python
def user_stated_norms(intent: str | None) -> set[str]:
    """Norms from the one user-number line. The rest of the thread is ignored."""
    text = intent or ""
    mark = "Числа из реплик пользователя"
    at = text.find(mark)
    if at < 0:
        return set()
    rest = text[at + len(mark) :]
    line = rest.split("\n", 1)[0]
    # The numbers sit on the next line. A parenthetical on the mark line is not a fact.
    body = rest.split("\n", 1)[1] if "\n" in rest else ""
    body = body.split("\n", 1)[0]
    return number_norms(body if body.strip() else line)
```

The mark line is `Числа из реплик пользователя (его слова, не ответ модели):` and has no digits. The next line is `77, 12,5`. Parse that next line. Ignore `line` when `body` is non-empty. The `line` fallback covers a one-line fixture.

Replace `_allowed_norms`:

```python
def _allowed_norms(source: str, intent: str, drop: set[str]) -> set[str]:
    have = number_norms(source) | number_norms(_request_blob(intent)) | user_stated_norms(intent)
    return have - drop
```

In `src/case3/fact_ground.py`:

```python
def allowed_fact_norms(source: str, intent: str) -> set[str]:
    """Source, this message, and numbers the user wrote earlier."""
    from case3.chat_turn import user_stated_norms

    return number_norms(source) | number_norms(latest_user_line(intent)) | user_stated_norms(intent)
```

`fact_conflict` keeps using `latest_user_line` only. An old `40` does not reopen the clash question on every later turn. `choice_instruction` still subtracts the rejected norm via `drop`, so choosing the document number removes the user’s earlier number for that answer.

- [ ] **Step 4: Run the new tests and the old locks**

Run: `pytest tests/test_chat_memory.py tests/test_chat_turn.py tests/test_fact_ground.py tests/test_memory_break_numbers.py tests/test_chat_prompt_tail.py -v`

Expected: PASS. `test_old_request_number_does_not_enter_the_answer` still rejects a `77` that lives only in the thread. `test_choosing_the_document_number_drops_the_rejected_one` still drops `40` when the current line picks `20`, because that fixture has no user-number block and `drop` still removes the rejected norm.

- [ ] **Step 5: Write the decision where agents read it**

Create `docs/adr/0014-user-stated-numbers.md`:

```markdown
# ADR-0014: Numbers the user wrote are allowed

## Status
Accepted. Amends the allow-list bullet of [ADR-0013](0013-chat-memory-chain.md).

## Date
2026-11-19

## Context
ADR-0013 keeps assistant digits out of the next PDF. It also drops a number the user wrote on an earlier turn. The model can see that number in the six-turn window and is then forbidden to repeat it.

## Decision
- Allowed numbers are Source, the current message before the memory markers, and the tokens in `format_user_numbers`.
- That line is built from `chat_prompt` and `dialogue.user` only, oldest first, at most 40 distinct values. Text after `Разговор этого чата`, `Карточка этого чата`, `Один прошлый ход`, `Предыдущий ход этого чата`, `Числа из реплик пользователя`, or `Требования UI:` is not scanned.
- `chat_summary`, `chat_opening`, `dialogue.assistant`, the open-report block, and chart JSON stay off the list.
- A thread digit that is not on this line is still illegal. `test_old_request_number_does_not_enter_the_answer` stays.
- Section rewrite (`draft_section`) does not read the line.

## Alternatives Considered

### Treat the whole six-turn window as Source
- Pros: the model may quote what it just said.
- Cons: a hallucinated digit becomes printable.
- Rejected.

## Consequences
- Positive: «сколько я называл» can repeat the user’s own figure.
- Negative: any allowed value may be repeated in a new place. A «слайд 2» the user typed allows the value 2 anywhere.
```

Add a row to `docs/adr/README.md` after 0013:

```markdown
| [0014](0014-user-stated-numbers.md) | User-stated numbers join the allow-list | Accepted |
```

In `.agents/knowledge/KI-chat-memory.md`, replace the allow-list invariant with: Source ∪ current message ∪ `format_user_numbers` (user fields only, cap 40). State that assistant fields and a bare thread digit stay illegal.

In `docs/MEMORY.md`, in the «Память чата» row, add one sentence: numbers the user wrote earlier are on a separate line and may be repeated; numbers the model wrote may not.

- [ ] **Step 6: Commit the code and tests**

```bash
git add src/case3/chat_memory.py src/case3/prior_turn.py src/case3/chat_turn.py src/case3/fact_ground.py tests/test_chat_memory.py tests/test_chat_turn.py tests/test_fact_ground.py
git commit -m "$(cat <<'EOF'
feat: allow numbers the user wrote on earlier turns

EOF
)"
```

Do not `git add -f` the ADR or KI.

---

### Task 2: A question mark does not cancel a clear order

**Files:**
- Modify: `src/case3/chat_act.py` (the `question =` assignment in `resolve_act`, about line 892)
- Test: `tests/test_chat_act.py`

**Interfaces:**
- Consumes: `_EDIT`, `_REWRITE`, `_PROSE`, `_RECOLOR`, `_VISUAL`
- Produces: `asks_without_order(raw: str) -> bool`. `resolve_act` sets `question = asks_without_order(raw)`.

`почему` and `зачем` stay talk even if the line also has an edit verb. Undo and redo are matched before this flag and do not change.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat_act.py`:

```python
def test_question_mark_on_a_clear_edit_still_edits():
    act = resolve_act("убери слайд 2?", has_deck=True)
    assert act.kind == "revise"
    assert act.op == "delete_slide"
    assert act.slide == 2


def test_why_with_an_edit_verb_stays_talk():
    act = resolve_act("почему бы не убрать слайд 2?", has_deck=True, has_report=True)
    assert act.kind == "talk"


def test_bare_question_stays_talk():
    act = resolve_act("что это?", has_deck=True, has_report=True)
    assert act.kind == "talk"
```

Leave `test_question_stays_talk_even_with_a_deck` and `test_a_question_does_not_become_an_edit` as they are. Both use `почему`.

- [ ] **Step 2: Run the tests and confirm the edit one fails**

Run: `pytest tests/test_chat_act.py::test_question_mark_on_a_clear_edit_still_edits tests/test_chat_act.py::test_why_with_an_edit_verb_stays_talk tests/test_chat_act.py::test_bare_question_stays_talk tests/test_chat_act.py::test_a_question_does_not_become_an_edit -v`

Expected: `test_question_mark_on_a_clear_edit_still_edits` FAIL (`kind == "talk"`). The `почему` tests PASS already.

- [ ] **Step 3: Implement the narrower question flag**

In `src/case3/chat_act.py`, above `resolve_act`:

```python
def asks_without_order(raw: str) -> bool:
    """True when the line is a question and not an order.

    «почему» and «зачем» are always questions. A trailing ? on
    «убери слайд 2» is still an order.
    """
    text = raw or ""
    if re.search(r"(?:^|\s)(?:почему|зачем)\b", text, re.IGNORECASE):
        return True
    if "?" not in text:
        return False
    if (
        _EDIT.search(text)
        or _REWRITE.search(text)
        or _PROSE.search(text)
        or _RECOLOR.search(text)
        or _VISUAL.search(text)
    ):
        return False
    return True
```

In `resolve_act`, replace `question = bool(_QUESTION.search(raw))` with:

```python
    question = asks_without_order(raw)
```

Leave `_QUESTION` in the file. Nothing else should call it after this. If a search shows no other callers, delete `_QUESTION`.

- [ ] **Step 4: Run the act tests**

Run: `pytest tests/test_chat_act.py tests/test_chat_coverage.py -q`

Expected: PASS. «короче?» follows the same path as «короче» because `короче` is in `_PROSE`. «что если убрать слайд 2?» is an order, because `убрать` is in `_EDIT` and the line has no `почему`. That is accepted.

- [ ] **Step 5: Note the rule in KI and commit**

In `.agents/knowledge/KI-chat-memory.md` gotchas, add: a `?` does not cancel a line that already has an edit verb. `почему` and `зачем` stay talk.

```bash
git add src/case3/chat_act.py tests/test_chat_act.py
git commit -m "$(cat <<'EOF'
fix: keep a clear edit when the line ends with a question mark

EOF
)"
```

---

### Task 3: Diagram refine uses the run palette

**Files:**
- Modify: `src/case3/chat_revise.py` (`_refine_diagram`, about line 1455)
- Test: `tests/test_chat_revise_chain.py`

**Interfaces:**
- Consumes: `meta.json` keys `chart_palette`, then `image_style_pack`
- Produces: `_diagram_palette(meta: dict) -> str`, one of `editorial`, `ocean`, `sunset`, `mono`, `atelier`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat_revise_chain.py`. Reuse the diagram fixture shape from `test_diagram_phrase_refines_the_only_scheme`: a run dir, `figures.json` with one diagram, and a fake `refine_diagram_in_run`.

```python
def test_diagram_phrase_keeps_the_run_palette(tmp_path: Path, monkeypatch):
    report = "source_20261119T120000Z"
    out = _report_dir(tmp_path, report)
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["chart_palette"] = "ocean"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (out / "figures.json").write_text(
        json.dumps(
            {"diagrams": [{"id": "dia_01", "title": "Касса", "mermaid": "graph LR\nA-->B"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_refine(out_dir, diagram_id, *, instruction, client, palette, formats):
        seen["palette"] = palette
        return {"id": diagram_id}

    monkeypatch.setattr("case3.diagram_edit.refine_diagram_in_run", fake_refine)
    monkeypatch.setattr("case3.llm_client.LLMConfig.from_env", lambda: object())
    monkeypatch.setattr("case3.llm_client.LLMClient", lambda _cfg: object())
    result = try_chat_revise("на схеме убери кассу", report, root=tmp_path)
    assert result is not None
    assert seen["palette"] == "ocean"
```

`_report_dir` already writes `meta.json` with `output_mode: report`. The read-modify above only adds `chart_palette`.

- [ ] **Step 2: Run it and confirm the palette is atelier**

Run: `pytest tests/test_chat_revise_chain.py::test_diagram_phrase_keeps_the_run_palette -v`

Expected: FAIL. `seen["palette"]` is `"atelier"`.

- [ ] **Step 3: Read the palette from meta**

In `src/case3/chat_revise.py`, next to `_refine_diagram`:

```python
_CHART_PALETTES = frozenset({"editorial", "ocean", "sunset", "mono", "atelier"})


def _diagram_palette(meta: dict) -> str:
    for key in ("chart_palette", "image_style_pack"):
        val = str(meta.get(key) or "").strip().lower()
        if val in _CHART_PALETTES:
            return val
    return "atelier"
```

In the `refine_diagram_in_run` call, replace `palette="atelier"` with `palette=_diagram_palette(_read(out_dir))`.

A deck pack such as `board` is not in the set, so it falls through to `atelier`. Do not pass it to Mermaid.

- [ ] **Step 4: Run the diagram chat tests**

Run: `pytest tests/test_chat_revise_chain.py::test_diagram_phrase_keeps_the_run_palette tests/test_chat_revise_chain.py::test_diagram_phrase_refines_the_only_scheme -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/case3/chat_revise.py tests/test_chat_revise_chain.py
git commit -m "$(cat <<'EOF'
fix: keep the report palette when a chat phrase edits a diagram

EOF
)"
```

---

### Task 4: A long Source keeps its headings in the chat prompt

**Files:**
- Modify: `src/case3/chat_turn.py` (`_user_block`, new `_source_outline`)
- Test: `tests/test_chat_turn.py`

**Interfaces:**
- Consumes: markdown headings `#{1,3}` in the Source string already passed to `_user_block`
- Produces: `_source_outline(text: str, limit: int = 1200) -> str`. Empty when there is no heading or the Source is at most 6000 characters.

The 6000 body budget does not shrink. The outline is extra, capped at 1200. Numbers in headings are already allowed because `allowed_fact_norms` scans the full Source, not the clipped prompt.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat_turn.py`:

```python
def test_long_source_prompt_keeps_a_middle_heading():
    from case3.chat_turn import _user_block

    middle = "# Касса в середине\n\n" + ("абзац про склад. " * 80)
    source = ("# Начало\n\n" + ("вводные слова. " * 200)) + "\n\n" + middle
    source += "\n\n# Конец\n\n" + ("хвост документа. " * 200)
    assert len(source) > 6000
    block = _user_block(source, "что в конце")
    assert "# Касса в середине" in block
    assert "склад" not in block.split("# Касса в середине", 1)[-1].split("# Конец", 1)[0]


def test_short_source_has_no_extra_outline():
    from case3.chat_turn import _user_block

    block = _user_block("# Касса\n\nБыло 20.", "что в кассе")
    assert block.count("# Касса") == 1
    assert "Оглавление документа" not in block
```

The first assertion wants the heading line itself. The body paragraph that contains `склад` stays out when the question does not share a stem with it. If the head budget happens to include that paragraph because the fixture is short, lengthen the opening filler until `склад` is outside both the head and the tail. The heading line must still be present via the outline.

- [ ] **Step 2: Run the test and confirm it fails**

Run: `pytest tests/test_chat_turn.py::test_long_source_prompt_keeps_a_middle_heading tests/test_chat_turn.py::test_short_source_has_no_extra_outline -v`

Expected: the long-source test FAIL (`# Касса в середине` absent). The short-source test PASS already.

- [ ] **Step 3: Prepend the outline only for a long Source**

In `src/case3/chat_turn.py`:

```python
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
```

In `_user_block`, after `src = _clip_source(...)`:

```python
    if len((source or "").strip()) > 6000:
        outline = _source_outline(source)
        if outline and src:
            src = outline + "\n\n" + src
        elif outline:
            src = outline
```

- [ ] **Step 4: Run the prompt tests**

Run: `pytest tests/test_chat_turn.py::test_long_source_prompt_keeps_a_middle_heading tests/test_chat_turn.py::test_short_source_has_no_extra_outline tests/test_chat_turn.py::test_long_source_keeps_the_head_the_match_and_the_tail -v`

Expected: PASS.

- [ ] **Step 5: Commit**

In KI, one line: a Source longer than 6000 characters also sends its markdown headings, capped at 1200, and the body budget stays 6000.

```bash
git add src/case3/chat_turn.py tests/test_chat_turn.py
git commit -m "$(cat <<'EOF'
feat: send markdown headings when Source is clipped for chat

EOF
)"
```

---

### Task 5: One shared word does not lift an old turn when the question named two

**Files:**
- Modify: `src/case3/chat_memory.py` (`_best_older`)
- Test: `tests/test_chat_memory.py`

**Interfaces:**
- Consumes: `_query_stems`, `_best_older`
- Produces: the same `_best_older` signature. Need 1 hit when the question has one content stem. Need 2 hits when it has two or more.

Explicit recall (`вспомни`, `что ты говорил`) still requires every topic word via `_covers`. Do not change that path. `test_plain_question_lifts_a_turn_outside_the_window` uses one stem (`касса`) and must keep passing.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat_memory.py`:

```python
def test_two_stems_do_not_lift_a_turn_that_shares_one():
    from case3.chat_memory import recall_block

    turns = [
        {"chat_prompt": "отчёт за квартал", "chat_summary": "КВАРТАЛТОЛЬКО"},
        {"chat_prompt": "выручка за квартал", "chat_summary": "ОБАСТОВА"},
    ]
    turns.extend(
        {"chat_prompt": f"другой ход {i}", "chat_summary": "спокойно"}
        for i in range(6)
    )
    weak = recall_block(turns[:1] + turns[2:], "что с выручкой за квартал")
    assert weak == ""
    strong = recall_block(turns, "что с выручкой за квартал")
    assert "ОБАСТОВА" in strong
    assert "КВАРТАЛТОЛЬКО" not in strong
```

`turns[:1] + turns[2:]` drops the turn that contains both words, leaves the one-word turn outside the six-turn window, and pads with six fresh turns so the weak turn is outside the window. Count the padding: one old turn plus six window turns is seven, so the old turn is outside `_WINDOW`. The strong case has two old turns plus six window turns.

Check the stems before trusting the fixture. `_query_stems` keeps tokens of at least 4 letters and drops `_LIFT_STOP`. `выручка` and `квартал` both survive. `что` does not. If a stem is swallowed, lengthen the fixture words. Do not lower the bar to make the fixture pass.

- [ ] **Step 2: Run it and confirm the weak query lifts the quarter turn**

Run: `pytest tests/test_chat_memory.py::test_two_stems_do_not_lift_a_turn_that_shares_one tests/test_chat_memory.py::test_plain_question_lifts_a_turn_outside_the_window -v`

Expected: the new test FAIL (`КВАРТАЛТОЛЬКО` is lifted). The single-stem test PASS.

- [ ] **Step 3: Require two hits when the question has two stems**

In `_best_older`, replace the final threshold:

```python
    need = 2 if len(stems) >= 2 else 1
    if best_score < need:
        return None
    return best
```

Remove the old `if best_score < 1` branch. Keep the tie rule: a later turn wins an equal score.

- [ ] **Step 4: Run the recall tests**

Run: `pytest tests/test_chat_memory.py tests/test_memory_break_chain.py -q`

Expected: PASS, including `test_plain_question_lifts_a_turn_outside_the_window` and `test_attack_recall_lifts_matched_turn_prose_near_2000`.

- [ ] **Step 5: Commit**

KI gotcha: a plain message lifts an old turn on one stem when that is the only content stem, and on two stems when the question has two or more.

```bash
git add src/case3/chat_memory.py tests/test_chat_memory.py
git commit -m "$(cat <<'EOF'
fix: do not lift an old turn on one shared word of a longer question

EOF
)"
```

---

### Task 6: A phrase edits the pixels of a photo already in the chat

**Files:**
- Modify: `src/case3/chat_act.py` (parser, and a branch in `resolve_act` immediately after the caption branch)
- Modify: `src/case3/chat_revise.py` (`try_chat_revise` dispatch, new `_edit_photo`)
- Test: `tests/test_chat_act.py`, `tests/test_chat_revise_chain.py`

**Interfaces:**
- Consumes: `edit_figure_in_run(out_dir, figure_id, *, mode, prompt, caption=None, formats=None)` in `figure_edit.py`. `mode="edit"` calls Image API `edit_png` on the existing PNG. The test never lets that call leave the process.
- Produces: `parse_photo_edit(text: str | None) -> tuple[str, str] | None`. `None` means this is not a pixel edit. `("", "")` means the user named a photo and did not say the change. `("usr_01", "убери людей")` names the file and the change. An empty id means the only `usr_*.png` in the run. `ChatAct.op` is `edit_photo`. `section` holds the id. `title` holds the instruction.

Caption phrases stay on `parse_caption`. «сделай фото цеха» stays a build. Generated `fig_*` pictures are not the pool. Only `figures/usr_*.png`.

- [ ] **Step 1: Write the failing parser tests**

Append to `tests/test_chat_act.py`:

```python
def test_photo_phrase_is_a_pixel_edit():
    act = resolve_act("на фото сделай небо темнее", has_report=True)
    assert act.kind == "revise"
    assert act.op == "edit_photo"
    assert act.title == "небо темнее"
    assert act.section == ""


def test_named_photo_keeps_its_id():
    act = resolve_act("поправь фото usr_01: убери людей", has_report=True)
    assert act.op == "edit_photo"
    assert act.section == "usr_01"
    assert "люди" in act.title or "убери людей" in act.title


def test_caption_phrase_is_not_a_pixel_edit():
    act = resolve_act("подпись фото: цех ночью", has_report=True)
    assert act.op == "caption"


def test_a_new_photo_request_is_not_a_pixel_edit():
    act = resolve_act("сделай фото цеха", has_report=True)
    assert act.op != "edit_photo"


def test_photo_without_a_change_asks():
    act = resolve_act("поправь фото", has_report=True)
    assert act.op == "ask"
    assert "фото" in act.say.lower()
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `pytest tests/test_chat_act.py::test_photo_phrase_is_a_pixel_edit tests/test_chat_act.py::test_named_photo_keeps_its_id tests/test_chat_act.py::test_caption_phrase_is_not_a_pixel_edit tests/test_chat_act.py::test_a_new_photo_request_is_not_a_pixel_edit tests/test_chat_act.py::test_photo_without_a_change_asks -v`

Expected: the two pixel-edit tests FAIL (`op` is not `edit_photo`). The caption test PASS already. The new-photo test PASS if the router does not invent `edit_photo`. The bare «поправь фото» test FAIL until the ask branch exists. It may currently return `rewrite` because `поправь` is in `_PROSE`. That failure is the one to fix.

- [ ] **Step 3: Parse the phrase and route it before rewrite**

In `src/case3/chat_act.py`, next to `parse_caption`:

```python
def parse_photo_edit(text: str | None) -> tuple[str, str] | None:
    """None when this is not a pixel edit of a photo already on the table.

    ("", "") means the photo was named and the change was not.
    The id is "" when the user did not name usr_NN.
    """
    raw = _norm(text or "").strip()
    if re.search(r"подпис", raw, re.IGNORECASE):
        return None
    if not re.search(r"\bфото\b|usr_", raw, re.IGNORECASE):
        return None
    aimed = re.search(
        r"на фото|у фото|это фото|поправь\s+фото|измени\s+фото|перерисуй\s+фото|убери\s+.+?\s+с фото|фото\s+usr_",
        raw,
        re.IGNORECASE,
    )
    if not aimed:
        return None
    found = re.search(r"\b(usr_[A-Za-z0-9_]+)", raw, re.IGNORECASE)
    fid = found.group(1) if found else ""
    tail = re.search(r"[:—–-]\s*(.{2,})$", raw)
    if tail:
        return fid, tail.group(1).strip(" .")
    inline = re.search(
        r"(?:на фото|у фото|это фото)\s+(?:сделай|убери|добавь|поправь|измени|перерисуй)\s+(.{2,})$",
        raw,
        re.IGNORECASE,
    )
    if inline:
        return fid, inline.group(1).strip(" .")
    return fid, ""
```

In `resolve_act`, immediately after the caption `return`, still inside `if not question`:

```python
        photo = parse_photo_edit(raw)
        if photo is not None:
            fid, instruction = photo
            if not instruction:
                return ChatAct(
                    kind="revise",
                    op="ask",
                    say="Что изменить на фото? Напиши «на фото сделай небо темнее».",
                )
            say = (
                f"Меняю фото {fid}."
                if fid
                else "Меняю фото."
            )
            return ChatAct(
                kind="revise",
                op="edit_photo",
                section=fid,
                title=instruction,
                say=say + " Картинку перерисую по твоей фразе.",
            )
```

`поправь фото` matches `aimed` and has no instruction, so it asks instead of rewriting the introduction.

- [ ] **Step 4: Run the parser tests**

Run: `pytest tests/test_chat_act.py::test_photo_phrase_is_a_pixel_edit tests/test_chat_act.py::test_named_photo_keeps_its_id tests/test_chat_act.py::test_caption_phrase_is_not_a_pixel_edit tests/test_chat_act.py::test_a_new_photo_request_is_not_a_pixel_edit tests/test_chat_act.py::test_photo_without_a_change_asks tests/test_chat_coverage.py::test_caption_names_the_figure -v`

Expected: PASS.

- [ ] **Step 5: Write the failing execution test**

Append to `tests/test_chat_revise_chain.py`:

```python
def test_photo_phrase_edits_the_only_png(tmp_path: Path, monkeypatch):
    report = "source_20261119T130000Z"
    out = _report_dir(tmp_path, report)
    figs = out / "figures"
    figs.mkdir()
    (figs / "usr_01.png").write_bytes(b"png")
    seen: dict[str, object] = {}

    def fake_edit(out_dir, figure_id, *, mode, prompt, caption=None, formats=None, cfg=None):
        seen["id"] = figure_id
        seen["mode"] = mode
        seen["prompt"] = prompt
        seen["formats"] = formats
        return {"figure_id": figure_id}

    monkeypatch.setattr("case3.figure_edit.edit_figure_in_run", fake_edit)
    result = try_chat_revise("на фото сделай небо темнее", report, root=tmp_path)
    assert result is not None
    assert result["op"] == "edit_photo"
    assert seen["id"] == "usr_01"
    assert seen["mode"] == "edit"
    assert seen["prompt"] == "небо темнее"
    assert seen["formats"] == {"pdf", "docx"}
```

- [ ] **Step 6: Run it and confirm it fails**

Run: `pytest tests/test_chat_revise_chain.py::test_photo_phrase_edits_the_only_png -v`

Expected: FAIL. `result` is `None` or `op` is not `edit_photo`, because dispatch does not know the op yet.

- [ ] **Step 7: Dispatch the edit onto the run that holds the PNG**

In `try_chat_revise`, add a branch beside the diagram branch:

```python
    elif act.op == "edit_photo":
        for run_id, path, _row in reversed(rows):
            if any((path / "figures").glob("usr_*.png")):
                work_id, work_dir = run_id, path
                break
```

Add `"edit_photo"` to the carried-file fallback only when the current `work_dir` has no `usr_*.png` and `carried_path / "figures"` does. Mirror the tex/deck fallback already in that function.

In the `elif act.op == ...` chain:

```python
    elif act.op == "edit_photo" and act.title:
        say = _edit_photo(work_dir, act.section, act.title) or say
```

```python
def _edit_photo(out_dir: Path, figure_id: str, instruction: str) -> str:
    from case3.figure_edit import FigureEditError, edit_figure_in_run

    figs = out_dir / "figures"
    pngs = sorted(figs.glob("usr_*.png")) if figs.is_dir() else []
    fid = (figure_id or "").strip()
    if fid:
        dest = figs / f"{fid}.png"
        if not dest.is_file():
            shown = ", ".join(path.stem for path in pngs[:6]) or "фото не вижу"
            return f"Фото {fid} нет. Сейчас: {shown}."
    elif len(pngs) == 1:
        fid = pngs[0].stem
    elif not pngs:
        return "В этом чате нет фото."
    else:
        shown = ", ".join(path.stem for path in pngs[:6])
        return f"Какое фото менять? Сейчас: {shown}."
    formats = {"pdf", "docx"} if any(out_dir.glob("*.tex")) else set()
    try:
        edit_figure_in_run(
            out_dir,
            fid,
            mode="edit",
            prompt=instruction,
            formats=formats,
        )
    except FigureEditError as exc:
        return str(exc)
    return f"Меняю фото {fid}. Картинку перерисую по твоей фразе."
```

`edit_figure_in_run` translates the prompt to English and calls Image API. The unit test replaces that function, so no network. Do not add a live API call to the test.

Two or more `usr_*.png` and no id: `_edit_photo` asks. One file: it is the target. A deck-only run with a PNG and no `.tex` passes `formats=set()` so PDF is not rebuilt.

- [ ] **Step 8: Run the photo tests and commit**

Run: `pytest tests/test_chat_act.py tests/test_chat_revise_chain.py::test_photo_phrase_edits_the_only_png tests/test_chat_coverage.py::test_caption_names_the_figure -q`

Expected: PASS.

In KI, replace the gotcha «Photo pixel edit is not a chat op» with: a phrase that aims at a photo already in the chat (`на фото …`, `поправь фото usr_01: …`) calls `edit_figure_in_run` with `mode="edit"`. A caption phrase stays a caption. «сделай фото …» stays a new build.

```bash
git add src/case3/chat_act.py src/case3/chat_revise.py tests/test_chat_act.py tests/test_chat_revise_chain.py
git commit -m "$(cat <<'EOF'
feat: edit a photo already in the chat from a phrase

EOF
)"
```

---

### Task 7: A phrase deletes a named section

**Files:**
- Modify: `src/case3/chat_act.py` (`parse_section_delete`, branch in `resolve_act`)
- Modify: `src/case3/chat_revise.py` (dispatch, `_delete_section`)
- Test: `tests/test_chat_act.py`, `tests/test_chat_coverage.py`

**Interfaces:**
- Consumes: `find_heading_spans` from `tex_preview.py`. A heading span is the `\section` or `\subsection` command. Level 1 is `\section`, level 2 is `\subsection`.
- Produces: `parse_section_delete(text: str | None) -> str | None`. `None` means this is not a section delete. `""` means the verb was there and the name was not. A non-empty string is the name. `ChatAct.op` is `delete_section`. `section` holds the name.

The cut runs from the start of the matched heading through the start of the next heading of the same or higher level. Subsections inside a deleted `\section` go with it. A deleted `\subsection` leaves the parent section. `\end{document}` stays. Undo is `capture_before_edit(..., kind="section_delete", target=name)`.

- [ ] **Step 1: Write the failing parser tests**

Append to `tests/test_chat_act.py`:

```python
def test_delete_section_names_the_heading():
    act = resolve_act("убери раздел Введение", has_report=True)
    assert act.kind == "revise"
    assert act.op == "delete_section"
    assert act.section == "Введение"


def test_delete_section_without_a_name_asks():
    act = resolve_act("удали раздел", has_report=True)
    assert act.op == "ask"
    assert "раздел" in act.say.lower()


def test_list_delete_is_not_a_section_delete():
    act = resolve_act("убери кассу из списка", has_report=True)
    assert act.op == "delete_item"


def test_slide_delete_is_not_a_section_delete():
    act = resolve_act("убери слайд 2", has_deck=True, has_report=True)
    assert act.op == "delete_slide"
```

- [ ] **Step 2: Run them and confirm the section tests fail**

Run: `pytest tests/test_chat_act.py::test_delete_section_names_the_heading tests/test_chat_act.py::test_delete_section_without_a_name_asks tests/test_chat_act.py::test_list_delete_is_not_a_section_delete tests/test_chat_act.py::test_slide_delete_is_not_a_section_delete -v`

Expected: the two section tests FAIL. The list and slide tests PASS already.

- [ ] **Step 3: Parse and return the act before the generic edit ask**

In `src/case3/chat_act.py`:

```python
def parse_section_delete(text: str | None) -> str | None:
    """None when this is not a section delete. Empty string asks for the name."""
    raw = _norm(text or "").strip()
    if not re.search(r"раздел", raw, re.IGNORECASE):
        return None
    if re.search(r"слайд|спис|таблиц|строк|абзац", raw, re.IGNORECASE):
        return None
    if not re.search(r"убери|удали|убрать|удалить", raw, re.IGNORECASE):
        return None
    match = re.search(
        r"(?:убери|удали|убрать|удалить)\s+раздел\w*\s+[«\"]?(.{2,80})",
        raw,
        re.IGNORECASE,
    )
    if not match:
        return ""
    name = _clean_name(match.group(1).strip(" «».:"))
    return name
```

`_clean_name` already exists in this file. It keeps «Введение» and returns empty for a stop-word such as «текст». An empty name is the ask branch.

In `resolve_act`, inside `if not question`, before `paragraph_at`:

```python
        removed_section = parse_section_delete(raw)
        if removed_section is not None:
            if not has_report:
                return ChatAct(
                    kind="talk",
                    say="Отчёта в этом чате ещё нет, раздел убрать некуда.",
                )
            if not removed_section:
                return ChatAct(
                    kind="revise",
                    op="ask",
                    say="Какой раздел убрать? Напиши «убери раздел Введение».",
                )
            return ChatAct(
                kind="revise",
                op="delete_section",
                section=removed_section,
                say=f"Убираю раздел «{removed_section}».",
            )
```

- [ ] **Step 4: Run the parser tests**

Run: `pytest tests/test_chat_act.py::test_delete_section_names_the_heading tests/test_chat_act.py::test_delete_section_without_a_name_asks tests/test_chat_act.py::test_list_delete_is_not_a_section_delete tests/test_chat_act.py::test_slide_delete_is_not_a_section_delete tests/test_chat_act.py -q`

Expected: PASS.

- [ ] **Step 5: Write the failing cut test**

Append to `tests/test_chat_coverage.py`:

```python
def test_delete_section_drops_that_heading_and_keeps_the_next(tmp_path: Path, monkeypatch):
    from case3.chat_revise import _delete_section

    tex = (
        "\\documentclass{article}\n\\begin{document}\n"
        "\\section{Введение}\nКасса была тихой.\n"
        "\\subsection{Ночь}\nСмена кончилась.\n"
        "\\section{Выводы}\nДальше пусто.\n"
        "\\end{document}\n"
    )
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.tex").write_text(tex, encoding="utf-8")
    (out / "meta.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("case3.run_rebuild.rebuild_run_docs", lambda *_a, **_k: {})
    say = _delete_section(out, "Введение")
    got = (out / "report.tex").read_text(encoding="utf-8")
    assert "Введение" not in got
    assert "Ночь" not in got
    assert "Смена" not in got
    assert r"\section{Выводы}" in got
    assert r"\end{document}" in got
    assert "Введение" in say
```

And one for a subsection that must leave the parent:

```python
def test_delete_subsection_leaves_the_parent(tmp_path: Path, monkeypatch):
    from case3.chat_revise import _delete_section

    tex = (
        "\\documentclass{article}\n\\begin{document}\n"
        "\\section{Введение}\nКасса была тихой.\n"
        "\\subsection{Ночь}\nСмена кончилась.\n"
        "\\section{Выводы}\nДальше пусто.\n"
        "\\end{document}\n"
    )
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.tex").write_text(tex, encoding="utf-8")
    (out / "meta.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("case3.run_rebuild.rebuild_run_docs", lambda *_a, **_k: {})
    _delete_section(out, "Ночь")
    got = (out / "report.tex").read_text(encoding="utf-8")
    assert r"\section{Введение}" in got
    assert "Касса" in got
    assert "Ночь" not in got
    assert "Смена" not in got
    assert r"\section{Выводы}" in got
```

- [ ] **Step 6: Run them and confirm they fail**

Run: `pytest tests/test_chat_coverage.py::test_delete_section_drops_that_heading_and_keeps_the_next tests/test_chat_coverage.py::test_delete_subsection_leaves_the_parent -v`

Expected: FAIL with `ImportError` or `AttributeError` on `_delete_section`.

- [ ] **Step 7: Cut the heading span and rebuild once**

Add `"delete_section"` to the tex op set in `try_chat_revise` (the set that walks back to a directory with `*.tex`, and the carried-file tex set).

```python
    elif act.op == "delete_section" and act.section:
        say = _delete_section(work_dir, act.section) or say
```

```python
def _delete_section(out_dir: Path, name: str) -> str:
    import re

    from case3.run_rebuild import rebuild_run_docs
    from case3.run_undo import capture_before_edit
    from case3.tex_preview import find_heading_spans

    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        return "В этом чате нет текста отчёта, раздел убрать некуда."
    tex_path = texs[0]
    try:
        tex = tex_path.read_text(encoding="utf-8")
    except OSError:
        return "Не смог прочитать отчёт."
    titles = _heading_titles(tex)
    headings = find_heading_spans(tex)
    levels = []
    for start, end in headings:
        chunk = tex[start:end]
        levels.append(2 if chunk.startswith("\\subsection") else 1)
    want = name.casefold()
    hits = [
        i
        for i, title in enumerate(titles)
        if want in title.casefold() or title.casefold() in want
    ]
    if len(hits) != 1:
        shown = ", ".join(titles[:8]) if titles else "разделов не вижу"
        return f"Раздела «{name}» нет одного. Есть: {shown}."
    index = hits[0]
    start = headings[index][0]
    level = levels[index]
    end = len(tex)
    for later in range(index + 1, len(headings)):
        if levels[later] <= level:
            end = headings[later][0]
            break
    end_doc = tex.find(r"\end{document}", start)
    if end_doc != -1 and end > end_doc:
        end = end_doc
    patched = tex[:start] + tex[end:]
    patched = re.sub(r"\n{3,}", "\n\n", patched)
    try:
        capture_before_edit(out_dir, kind="section_delete", target=titles[index])
    except Exception as exc:  # noqa: BLE001
        return str(exc)
    tex_path.write_text(patched, encoding="utf-8")
    try:
        rebuild_run_docs(out_dir, formats={"pdf", "docx"})
    except Exception as exc:  # noqa: BLE001
        tex_path.write_text(tex, encoding="utf-8")
        return f"Раздел не убрал: {exc}"
    return f"Убрал раздел «{titles[index]}»."
```

Two headings that both contain the same word return the «нет одного» line and do not write the file. A missing name does the same.

- [ ] **Step 8: Run the cut tests and commit**

Run: `pytest tests/test_chat_coverage.py::test_delete_section_drops_that_heading_and_keeps_the_next tests/test_chat_coverage.py::test_delete_subsection_leaves_the_parent tests/test_chat_act.py::test_delete_section_names_the_heading tests/test_chat_coverage.py::test_added_section_lands_before_the_end -q`

Expected: PASS. Adding a section still inserts before `\end{document}`.

In KI: «убери раздел Название» deletes that heading and the body through the next heading of the same or higher level, then rebuilds PDF and DOCX once. One paragraph inside a section is still a rewrite, not a delete.

```bash
git add src/case3/chat_act.py src/case3/chat_revise.py tests/test_chat_act.py tests/test_chat_coverage.py
git commit -m "$(cat <<'EOF'
feat: delete a named report section from a chat phrase

EOF
)"
```

---

### Task 8: The talk model says what a phrase cannot change

**Files:**
- Modify: `prompt/chat_answer.md`
- Modify: `src/case3/chat_act.py` (two early exits so a known impossible edit stays talk)
- Modify: `src/case3/chat_turn.py` (`try_chat_answer` appends one note)
- Test: `tests/test_chat_act.py`, `tests/test_chat_turn.py`

**Interfaces:**
- Consumes: `resolve_act` and `load_prompt("chat_answer")`.
- Produces: `limit_note(intent: str) -> str`. Empty on a normal question, on a build, and on a revise the router would actually run. A non-empty note starts with `Файл не изменился.` The reply the user sees is an ordinary sentence, not a caps heading.

The regex router still decides the edit. This task does not add a second model. A matched edit still runs and never reaches `try_chat_answer`. A short `ask` («Какой раздел?», «Какой цвет?») stays the canned line from `resolve_act`. The model speaks only when the line asked for a change and the router left it as talk.

Known holes that must stay talk, so the model can explain them instead of rewriting a section:

- Chart numbers: the line has `график` and one of `числ`, `данн`, `столб`, `значен`, and it does not name a chart type or a palette.
- Diagram legend: the line has `схем` and `легенд`.

- [ ] **Step 1: Write the failing router tests**

Append to `tests/test_chat_act.py`:

```python
def test_chart_numbers_stay_talk():
    act = resolve_act("поменяй числа на графике", has_report=True, has_deck=True)
    assert act.kind == "talk"


def test_diagram_legend_stays_talk():
    act = resolve_act("поправь легенду схемы", has_diagram=True, has_report=True)
    assert act.kind == "talk"


def test_chart_type_is_still_a_retype():
    act = resolve_act("сделай график линейным", has_report=True)
    assert act.op == "retype_charts"
    assert act.chart == "line"
```

- [ ] **Step 2: Run them and confirm the first two fail**

Run: `pytest tests/test_chat_act.py::test_chart_numbers_stay_talk tests/test_chat_act.py::test_diagram_legend_stays_talk tests/test_chat_act.py::test_chart_type_is_still_a_retype -v`

Expected: the number test and the legend test FAIL (`kind == "revise"`, usually a rewrite, because `поменяй` and `поправь` are edit verbs). The line-chart test PASS already.

- [ ] **Step 3: Let those two phrases fall through to talk**

In `src/case3/chat_act.py`, above `resolve_act`:

```python
def _unsupported_shape(raw: str) -> bool:
    """A change the phrase router will never perform."""
    if re.search(r"график", raw, re.IGNORECASE) and re.search(
        r"числ|данн|столб|значен", raw, re.IGNORECASE
    ):
        if chart_type_named(raw) or _named(raw, _PALETTES):
            return False
        return True
    if re.search(r"схем", raw, re.IGNORECASE) and re.search(r"легенд", raw, re.IGNORECASE):
        return True
    return False
```

At the top of `resolve_act`, after `raw = _norm(...)` and before the undo check:

```python
    if _unsupported_shape(raw):
        return ChatAct(kind="talk")
```

Undo on a short line still wins only when the line is an undo. `_unsupported_shape` does not match `отмени`.

- [ ] **Step 4: Run the router tests**

Run: `pytest tests/test_chat_act.py::test_chart_numbers_stay_talk tests/test_chat_act.py::test_diagram_legend_stays_talk tests/test_chat_act.py::test_chart_type_is_still_a_retype tests/test_chat_act.py::test_diagram_edit_is_not_a_new_diagram -q`

Expected: PASS. «на схеме убери кассу» is still `refine_diagram`.

- [ ] **Step 5: Write the failing answer test**

Append to `tests/test_chat_turn.py`:

```python
def test_unsupported_edit_tells_the_model_the_file_stayed():
    class _Catch:
        def __init__(self) -> None:
            self.system = ""
            self.user = ""

        def stream(self, **kwargs):
            self.system = kwargs.get("system") or ""
            self.user = kwargs.get("user_text") or ""
            yield "Числа на графике я поменять не умею. Могу перекрасить или сменить вид. Напиши «перекрась графики в ocean»."

    client = _Catch()
    text = try_chat_answer("Касса была 20.", "поменяй числа на графике", client=client)
    assert "Файл не изменился" in client.user
    assert "числа на графике" in client.system
    assert "не умею" in text
    assert "ПРАВКА НЕ ВЗЯТА" not in text


def test_a_plain_question_has_no_limit_note():
    client = _Seq(["Касса была 20."])
    try_chat_answer("Касса была 20.", "что с кассой", client=client)
    assert "Файл не изменился" not in client.seen[0]
```

- [ ] **Step 6: Run the answer test and confirm it fails**

Run: `pytest tests/test_chat_turn.py::test_unsupported_edit_tells_the_model_the_file_stayed tests/test_chat_turn.py::test_a_plain_question_has_no_limit_note -v`

Expected: the first FAIL (`Файл не изменился` absent, and the system prompt has no chart-number limit). The second PASS already.

- [ ] **Step 7: Put the menu in the prompt and the note on the user block**

Append to `prompt/chat_answer.md`:

```markdown
Если просьба меняет файл и её нет в списке ниже, не делай вид, что файл изменился. Ответь обычным предложением, без заголовка капсом: чего не умеешь, что рядом умеешь, и одну фразу, которую можно скопировать. На обычный вопрос по тексту этот список не зачитывай.

Могу по фразе:
- переписать раздел или абзац: «перепиши введение»;
- сократить весь отчёт: «сократи весь отчёт»;
- добавить абзац или раздел;
- убрать раздел: «убери раздел Введение»;
- ячейку или строку таблицы: «в таблице замени 10 на 12»;
- пункт списка: «в списке замени кассу на выручку»;
- подпись рисунка: «подпись рисунка fig_01: цех»;
- пиксели своего фото: «на фото сделай небо темнее»;
- схему одной фразой: «на схеме убери кассу»;
- вид или цвет графика, числа те же: «сделай график линейным», «перекрась графики в ocean»;
- стиль, структуру и слайд презентации;
- «отмени».

Не могу:
- поменять числа на графике;
- править легенду схемы отдельно;
- перерисовать картинку fig_, у неё меняется только подпись;
- вырезать один абзац и оставить заголовок раздела.
Числа из строки «Числа из реплик пользователя» можно повторять. Числа из прошлых ответов модели нельзя.
```

In `src/case3/chat_turn.py`:

```python
def limit_note(intent: str) -> str:
    """Tell the talk model that this line did not edit the file."""
    from case3.chat_act import _EDIT, _PROSE, resolve_act

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
    if not (_EDIT.search(line) or _PROSE.search(line)):
        return ""
    return (
        "Файл не изменился.\n"
        "Ответь обычным предложением, без заголовка капсом: чего не умеешь, "
        "что рядом умеешь, и одну фразу, которую можно скопировать."
    )
```

`_EDIT` and `_PROSE` are private. Importing them here is the contract for this task. Do not copy the verb lists into `chat_turn.py`.

In `try_chat_answer`, after the report block is appended and before `_ask_model`:

```python
    note_limit = limit_note(intent)
    if note_limit:
        user += "\n\n" + note_limit
```

The variable `note` is already the choice instruction. Use `note_limit` so the two do not collide.

- [ ] **Step 8: Run the answer tests and commit**

Run: `pytest tests/test_chat_turn.py::test_unsupported_edit_tells_the_model_the_file_stayed tests/test_chat_turn.py::test_a_plain_question_has_no_limit_note tests/test_chat_act.py::test_chart_numbers_stay_talk tests/test_chat_turn.py::test_chat_answer_uses_the_model_text -q`

Expected: PASS. A normal answer still returns the model text. `prompt/chat_answer.md` is tracked (it is not under `docs/`).

In KI: a talk answer about an edit the router did not take is an ordinary sentence: what it cannot do, what it can do instead, and one phrase to copy. No caps heading. Chart numbers and a diagram legend are talk on purpose.

```bash
git add prompt/chat_answer.md src/case3/chat_act.py src/case3/chat_turn.py tests/test_chat_act.py tests/test_chat_turn.py
git commit -m "$(cat <<'EOF'
feat: tell the chat when a phrase cannot change the file

EOF
)"
```

---

## Self-review

Spec coverage from the 2026-11-19 audit:

| Audit item | Task |
|---|---|
| User-stated numbers on the allow-list, assistant numbers still banned | Task 1 |
| `убери слайд 2?` edits, `почему …?` stays talk | Task 2 |
| Diagram palette from the run, not a hardcoded atelier | Task 3 |
| Long Source keeps its headings | Task 4 |
| Lift threshold when the question has two stems | Task 5 |
| Edit pixels of a photo already in the chat | Task 6 |
| Delete a named section, including its subsections | Task 7 |
| Tell the user when a phrase cannot change the file | Task 8 |
| Second model, embeddings, chart series as an edit, one paragraph delete, table captions | Out of scope. Task 8 explains the chart-number and legend holes. It does not implement them. |

`test_old_request_number_does_not_enter_the_answer` is unchanged on purpose. The door is the new line, not the thread body.

`format_user_numbers` and `user_stated_norms` agree on the marker `Числа из реплик пользователя`. The numbers are on the following line. `user_stated_norms` reads that line only.

`_allowed_norms` subtracts `drop` after adding `user_stated_norms`, so a conflict choice still removes the rejected value.
