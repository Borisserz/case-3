"""LAN Qwen / llama-server HTTP 500 «Context size exceeded» → shrink max_tokens."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
import urllib.error

from case3.llm_client import (
    LLMClient,
    LLMConfig,
    LLMError,
    context_exceeded,
    context_shrink_max_tokens,
    fit_oversize_prompt,
    parse_context_window,
)


def test_context_exceeded_detects_llama_server_message() -> None:
    assert context_exceeded('{"error":{"message":"Context size has been exceeded."}}')
    assert context_exceeded("context size has been exceeded")
    assert not context_exceeded("internal server error")


def test_context_shrink_halves_until_floor() -> None:
    assert context_shrink_max_tokens(16384) == 8192
    assert context_shrink_max_tokens(2048) == 1024
    assert context_shrink_max_tokens(1024) is None
    assert context_shrink_max_tokens(800) is None


def test_complete_retries_on_500_context_exceeded() -> None:
    cfg = LLMConfig(
        base_url="http://192.168.4.101:8080",
        model="qwen3.5-4b",
        max_retries=3,
        max_tokens=16384,
        timeout_s=5,
        reasoning="off",
    )
    client = LLMClient(cfg)

    err = _http_500("Context size has been exceeded.")
    ok = MagicMock()
    ok.read.return_value = json.dumps(
        {
            "choices": [
                {
                    "message": {"content": "\\documentclass{article}\\begin{document}x\\end{document}"},
                    "finish_reason": "stop",
                }
            ]
        }
    ).encode("utf-8")
    ok.__enter__ = lambda s: s
    ok.__exit__ = MagicMock(return_value=False)

    posts: list[int] = []

    def fake_urlopen(req, timeout=None):  # noqa: ANN001
        data = json.loads(req.data.decode("utf-8"))
        posts.append(int(data["max_tokens"]))
        if len(posts) == 1:
            raise err
        return ok

    with patch("case3.llm_client.urllib.request.urlopen", side_effect=fake_urlopen):
        with patch.object(client, "_sleep", return_value=None):
            text = client.complete(system="sys", user_text="user")

    assert "documentclass" in text
    assert posts[0] == 16384
    assert posts[1] == 8192


_OVERFLOW = (
    "HTTP 400 from http://192.168.4.101:8080/v1/chat/completions: "
    '{"error":{"code":400,"message":"request (40618 tokens) exceeds the available '
    'context size (31232 tokens), try increasing it","type":"exceed_context_size_error",'
    '"n_prompt_tokens":40618,"n_ctx":31232}}'
)


def test_parse_context_window_reads_llama_counts() -> None:
    assert parse_context_window(_OVERFLOW) == (40618, 31232)
    assert parse_context_window("context size has been exceeded") is None


def test_fit_oversize_prompt_keeps_the_head_and_cuts_the_source() -> None:
    rules = "Правила сборки слайдов. "
    source = "Факт 10. " * 4000
    body = {
        "messages": [
            {"role": "system", "content": rules + source},
            {"role": "user", "content": "Собери презентацию."},
        ],
        "max_tokens": 16384,
    }
    fitted = fit_oversize_prompt(body, _OVERFLOW, 16384)
    assert fitted is not None and fitted <= 4096
    system = body["messages"][0]["content"]
    assert system.startswith(rules)
    assert len(system) < len(rules + source)
    assert "обрезан" in system


def test_complete_clips_prompt_on_400_context_overflow() -> None:
    cfg = LLMConfig(
        base_url="http://192.168.4.101:8080",
        model="qwen3.5-4b",
        max_retries=1,
        max_tokens=16384,
        timeout_s=5,
        reasoning="off",
    )
    client = LLMClient(cfg)
    err = _http_400(_OVERFLOW)
    ok = MagicMock()
    ok.read.return_value = json.dumps(
        {
            "choices": [
                {
                    "message": {"content": '{"slides":[]}'},
                    "finish_reason": "stop",
                }
            ]
        }
    ).encode("utf-8")
    ok.__enter__ = lambda s: s
    ok.__exit__ = MagicMock(return_value=False)
    seen: list[tuple[int, int]] = []

    def fake_urlopen(req, timeout=None):  # noqa: ANN001
        data = json.loads(req.data.decode("utf-8"))
        system = data["messages"][0]["content"]
        seen.append((int(data["max_tokens"]), len(system)))
        if len(seen) == 1:
            raise err
        return ok

    with patch("case3.llm_client.urllib.request.urlopen", side_effect=fake_urlopen):
        with patch.object(client, "_sleep", return_value=None):
            text = client.complete(system="Правила. " + ("строка 12\n" * 3000), user_text="Собери.")

    assert "slides" in text
    assert seen[1][0] < seen[0][0]
    assert seen[1][1] < seen[0][1]


def test_complete_raises_500_context_when_cannot_shrink() -> None:
    cfg = LLMConfig(
        base_url="http://192.168.4.101:8080",
        model="qwen3.5-4b",
        max_retries=1,
        max_tokens=1024,
        timeout_s=5,
    )
    client = LLMClient(cfg)
    err = _http_500("Context size has been exceeded.")

    with patch("case3.llm_client.urllib.request.urlopen", side_effect=err):
        with patch.object(client, "_sleep", return_value=None):
            with pytest.raises(LLMError, match="500|Context|контекст"):
                client.complete(system="s", user_text="u")


def _http_400(message: str) -> Exception:
    body = message.encode("utf-8")
    return urllib.error.HTTPError(
        url="http://192.168.4.101:8080/v1/chat/completions",
        code=400,
        msg="Bad Request",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(body),
    )


def _http_500(message: str) -> Exception:
    body = json.dumps({"error": {"code": 500, "message": message, "type": "server_error"}}).encode(
        "utf-8"
    )
    return urllib.error.HTTPError(
        url="http://192.168.4.101:8080/v1/chat/completions",
        code=500,
        msg="Internal Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(body),
    )
