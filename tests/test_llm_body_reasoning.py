"""OpenRouter vs local reasoning body shapes."""

from __future__ import annotations

from case3.llm_client import build_body


def test_local_off_uses_chat_template_kwargs() -> None:
    body = build_body(
        system="s",
        user_text="u",
        reasoning="off",
        base_url="http://192.168.1.10:8080",
    )
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert "reasoning" not in body


def test_openrouter_off_omits_reasoning_for_nemotron() -> None:
    """Nemotron free burns max_tokens on hidden reasoning → empty content + length."""
    body = build_body(
        system="s",
        user_text="u",
        model="nvidia/nemotron-3.5-lightning:free",
        reasoning="off",
        base_url="https://openrouter.ai/api",
    )
    assert "reasoning" not in body
    assert "chat_template_kwargs" not in body


def test_openrouter_off_minimax_keeps_low_exclude() -> None:
    body = build_body(
        system="s",
        user_text="u",
        model="minimax/minimax-m3.1-flash:free",
        reasoning="off",
        base_url="https://openrouter.ai/api",
    )
    assert body["reasoning"] == {"effort": "low", "exclude": True}
    assert "chat_template_kwargs" not in body
