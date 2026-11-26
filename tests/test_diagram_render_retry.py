"""Silent LLM retry when Mermaid fails the render check (Liber «Ещё вариант» under the hood)."""

from __future__ import annotations

from case3.diagram_generate import complete_diagrams, diagrams_pass_render
from case3.diagram_render import mermaid_structurally_ok


def _json_diagram(mermaid: str) -> str:
    escaped = mermaid.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return (
        "```json\n"
        '{"diagrams":[{"id":"dia_01","type":"flowchart","title":"Тест",'
        f'"mermaid":"{escaped}"}}]}}\n'
        "```"
    )


class _ScriptedClient:
    def __init__(self, payloads: list[str]) -> None:
        self.payloads = list(payloads)
        self.calls = 0

    def complete(self, *, system: str, user_text: str, cancel_check=None) -> str:  # noqa: ANN001
        self.calls += 1
        if cancel_check is not None:
            cancel_check()
        if not self.payloads:
            raise AssertionError("unexpected extra LLM call")
        return self.payloads.pop(0)


def test_structurally_rejects_idless_nodes() -> None:
    bad = "flowchart TD\n  ([ИМНС Пинский р-ну]) Акцизы ([НДС])\n"
    good = "flowchart TD\n  A([ИМНС Пинский р-ну]) --> B[Акцизы]\n"
    assert mermaid_structurally_ok(bad) is False
    assert mermaid_structurally_ok(good) is True


def test_diagrams_pass_render_requires_all() -> None:
    ok = [{"id": "dia_01", "mermaid": "flowchart TD\nA-->B"}]
    assert diagrams_pass_render(ok, lambda _m: True) is True
    assert diagrams_pass_render(ok, lambda _m: False) is False
    assert diagrams_pass_render([], lambda _m: True) is False


def test_complete_diagrams_retries_when_render_fails() -> None:
    bad = _json_diagram("flowchart TD\n  ([ИМНС]) Акцизы ([НДС])")
    good = _json_diagram("flowchart TD\n  A[ИМНС] --> B[Акцизы]")
    client = _ScriptedClient([bad, good])
    checks: list[bool] = []

    def render_ok(mermaid: str) -> bool:
        ok = "-->" in mermaid and "A[" in mermaid
        checks.append(ok)
        return ok

    diagrams = complete_diagrams(
        intent="схема",
        source_text="ИМНС / Акцизы",
        max_diagrams=1,
        client=client,
        palette="atelier",
        render_ok=render_ok,
        max_render_retries=2,
    )
    assert client.calls == 2
    assert len(diagrams) == 1
    assert "-->" in diagrams[0]["mermaid"]
    assert checks == [False, True]


def test_complete_diagrams_stops_after_retries_and_returns_last() -> None:
    bad = _json_diagram("flowchart TD\n  ([ИМНС]) Акцизы ([НДС])")
    client = _ScriptedClient([bad, bad, bad])
    diagrams = complete_diagrams(
        intent="схема",
        source_text="данные",
        max_diagrams=1,
        client=client,
        palette="atelier",
        render_ok=lambda _m: False,
        max_render_retries=2,
    )
    assert client.calls == 3
    assert len(diagrams) == 1


def test_svg_error_detection_ignores_css_error_icon_rules() -> None:
    """Successful Mermaid SVGs include `.error-icon` CSS; that must not fail the check."""
    from case3.diagram_render import mermaid_syntax_ok

    good = "flowchart TD\n  A[Start] --> B[End]\n"
    assert mermaid_syntax_ok(good) is True


def test_default_check_retries_on_structurally_bad_mermaid() -> None:
    """Without an injected checker, structural NODE_DSTART drafts still retry."""
    bad = _json_diagram("flowchart TD\n  ([ИМНС Пинский р-ну]) Акцизы ([НДС])")
    good = _json_diagram(
        "flowchart TD\n  A([ИМНС Пинский р-ну]) --> B[Акцизы] --> C[НДС]"
    )
    client = _ScriptedClient([bad, good])
    diagrams = complete_diagrams(
        intent="структура поступлений",
        source_text="ИМНС Пинский р-н: Акцизы, НДС",
        max_diagrams=1,
        client=client,
        palette="atelier",
        max_render_retries=2,
    )
    assert client.calls == 2
    assert "-->" in diagrams[0]["mermaid"]
    assert "A(" in diagrams[0]["mermaid"] or "A[" in diagrams[0]["mermaid"]
