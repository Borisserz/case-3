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


def test_openrouter_free_off_omits_reasoning() -> None:
    body = build_body(
        system="s",
        user_text="u",
        model="openrouter/free",
        reasoning="off",
        base_url="https://openrouter.ai/api",
    )
    assert "reasoning" not in body


def test_images_become_qwen_vision_parts() -> None:
    body = build_body(
        system="s",
        user_text="build the deck",
        reasoning="off",
        base_url="http://192.168.1.10:8080",
        images=[("usr_01", "data:image/jpeg;base64,aaaa")],
    )
    content = body["messages"][1]["content"]
    assert isinstance(content, list)
    assert content[0]["text"] == "build the deck"
    assert content[1]["text"] == "Image id usr_01."
    assert content[2]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    # Local Qwen still gets the thinking switch alongside vision parts.
    assert body["chat_template_kwargs"]["enable_thinking"] is False


def test_no_images_keeps_plain_string_content() -> None:
    body = build_body(system="s", user_text="u", reasoning="off", images=[])
    assert body["messages"][1]["content"] == "u"
