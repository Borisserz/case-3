"""OpenRouter vs local reasoning body shapes."""

from __future__ import annotations

from case3.llm_client import LLMClient, LLMConfig, build_body
import io
import json
import urllib.error
from unittest.mock import patch


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


def test_llm_complete_falls_back_to_text_on_400_with_images() -> None:
    cfg = LLMConfig(
        base_url="http://test.api",
        api_key="key",
        max_retries=1,
    )
    client = LLMClient(cfg)

    calls = 0
    posted_contents = []

    def mock_urlopen(req, timeout=None):
        nonlocal calls
        calls += 1
        payload = json.loads(req.data.decode("utf-8"))
        posted_contents.append(payload["messages"][1]["content"])
        if calls == 1:
            # First call with images fails with 400 (e.g. image not supported)
            err = urllib.error.HTTPError(
                url="http://test.api/chat/completions",
                code=400,
                msg="Bad Request",
                hdrs={},
                fp=io.BytesIO(b'{"error": "Images not supported by this model"}'),
            )
            raise err
        # Second call succeeds
        resp_obj = {
            "choices": [
                {
                    "message": {"content": "ok text response"},
                    "finish_reason": "stop",
                }
            ]
        }
        mock_resp = io.BytesIO(json.dumps(resp_obj).encode("utf-8"))
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        res = client.complete(
            system="sys",
            user_text="describe",
            images=[("usr_01", "data:image/jpeg;base64,1234")],
        )

    assert res == "ok text response"
    assert calls == 2
    # First call had list content (multimodal)
    assert isinstance(posted_contents[0], list)
    # Fallback call was pure string
    assert posted_contents[1] == "describe"

