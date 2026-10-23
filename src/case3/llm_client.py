"""OpenAI-compatible text client (same HTTP shape as bam-bam-bam)."""

from __future__ import annotations

import http.client
import io
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("case3.llm")

_THINK = re.compile(r"<think>.*?</think>", re.S)


class LLMConfigError(ValueError):
    pass


class LLMError(RuntimeError):
    pass


def _env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _number(name: str, default: Any, kind: Callable[[str], Any]) -> Any:
    raw = _env(name)
    try:
        return default if raw is None else kind(raw)
    except ValueError as exc:
        raise LLMConfigError(f"{name}={raw!r} is not a number") from exc


_REASONING = ("off", "low", "medium", "high")


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str | None = None
    model: str | None = None
    timeout_s: float = 300.0
    max_retries: int = 2
    temperature: float = 0.2
    reasoning: str = "off"
    max_tokens: int = 16384

    @property
    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        base = base.removesuffix("/v1/chat/completions").removesuffix("/v1")
        return f"{base}/v1/chat/completions"

    @classmethod
    def from_env(cls) -> LLMConfig:
        base = _env("VISION_API_BASE_URL", "CASE3_API_BASE_URL", "INGEST_VISION_API_BASE_URL")
        if base is None:
            raise LLMConfigError(
                "Set VISION_API_BASE_URL in .env (e.g. http://192.168.x.x:8080)"
            )
        # Default off: thinking burns max_tokens and was the #1 truncation cause.
        reasoning = (_env("VISION_REASONING", "CASE3_REASONING") or "off").lower()
        if reasoning not in _REASONING:
            raise LLMConfigError(f"reasoning={reasoning!r}: expected {', '.join(_REASONING)}")
        return cls(
            base_url=base,
            api_key=_env("VISION_API_KEY", "CASE3_API_KEY", "INGEST_VISION_API_KEY"),
            model=_env("VISION_MODEL", "CASE3_MODEL", "INGEST_VISION_MODEL"),
            timeout_s=_number("VISION_TIMEOUT_S", 300, float),
            max_retries=_number("VISION_MAX_RETRIES", 2, int),
            temperature=_number("VISION_TEMPERATURE", 0.2, float),
            reasoning=reasoning,
            max_tokens=max(1024, int(_number("VISION_MAX_TOKENS", 16384, int))),
        )


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return "".join(p.get("text", "") for p in value if isinstance(p, dict))
    return value if isinstance(value, str) else ""


def _after_think(raw: str) -> str:
    text = _THINK.sub("", raw)
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()


def _has_tex_signal(text: str) -> bool:
    t = text or ""
    low = t.lower()
    return (
        r"\documentclass" in t
        or "```latex" in low
        or "```tex" in low
        or r"\begin{document}" in t
        or "```json" in low
        or '"charts"' in t
        or '"figures"' in t
    )


def _usable_assistant_text(raw: str) -> str:
    """Prefer post-think answer; if empty, keep raw when it still has LaTeX/JSON."""
    cleaned = _after_think(raw)
    if cleaned:
        return cleaned
    # Some Qwen builds put the whole answer inside <think>…</think>
    if _has_tex_signal(raw):
        return (raw or "").strip()
    return ""


def _content(data: Any) -> tuple[str, str]:
    """Return (assistant_text, finish_reason)."""
    finish = ""
    try:
        finish = str(data["choices"][0].get("finish_reason") or "")
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected response: {str(data)[:200]}") from exc
    if not isinstance(message, dict):
        raise LLMError(f"unexpected response: {str(data)[:200]}")

    blobs = [
        _as_text(message.get("content")),
        _as_text(message.get("reasoning_content")),
        _as_text(message.get("reasoning")),
    ]
    for blob in blobs:
        got = _usable_assistant_text(blob)
        if got:
            return got, finish

    # Last resort: any field that still contains a latex/json fence
    for blob in blobs:
        if _has_tex_signal(blob):
            return blob.strip(), finish

    hint = (
        "Проверь VISION_API_BASE_URL / модель; VISION_REASONING=off; "
        "на :free при length→empty смени модель "
        "(например google/gemini-2.0-flash-exp:free) и перезапусти API"
    )
    raise LLMError(
        "empty response from Vision API "
        f"(finish_reason={finish!r}). {hint}"
    )


def _http_body(exc: urllib.error.HTTPError) -> str:
    try:
        return " ".join(exc.read()[:300].decode("utf-8", "replace").split())
    except (OSError, http.client.HTTPException):
        return ""


def build_body(
    *,
    system: str,
    user_text: str,
    model: str | None = None,
    temperature: float = 0.2,
    reasoning: str = "off",
    max_tokens: int = 16384,
    base_url: str | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    thinking: dict[str, Any] = (
        {"enable_thinking": False}
        if reasoning == "off"
        else {"enable_thinking": True, "resolved_reasoning_effort": reasoning}
    )
    body: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "temperature": temperature,
        "max_tokens": max(16, int(max_tokens)),
    }
    if stream:
        body["stream"] = True
    host = (base_url or "").lower()
    openrouter = "openrouter.ai" in host
    model_l = (model or "").lower()
    if openrouter:
        # MiniMax Flash: thinking object is mandatory — low + exclude when off.
        # Nemotron / most free models: sending reasoning still burns max_tokens into
        # hidden thought → finish_reason=length with empty content. Omit when off.
        if reasoning == "off":
            if "minimax" in model_l:
                body["reasoning"] = {"effort": "low", "exclude": True}
        else:
            effort = reasoning
            if effort not in ("low", "medium", "high", "xhigh", "max", "minimal"):
                effort = "low"
            body["reasoning"] = {"effort": effort, "exclude": False}
    else:
        # Local Qwen / vLLM-style thinking switch.
        body["chat_template_kwargs"] = thinking
    if model:
        body["model"] = model
    return body


class LLMClient:
    def __init__(self, config: LLMConfig, *, sleep: Callable[[float], None] = time.sleep) -> None:
        self.config = config
        self._sleep = sleep
        self.last_finish_reason: str = ""

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if "openrouter.ai" in (self.config.base_url or "").lower():
            headers.setdefault("HTTP-Referer", "https://github.com/Borisserz/case-3")
            headers.setdefault("X-Title", "case-3")
        return headers

    def complete(self, *, system: str, user_text: str, reasoning: str | None = None) -> str:
        r = reasoning or self.config.reasoning
        if r not in _REASONING:
            raise LLMConfigError(f"reasoning={r!r}: expected {', '.join(_REASONING)}")
        body = build_body(
            system=system,
            user_text=user_text,
            model=self.config.model,
            temperature=self.config.temperature,
            reasoning=r,
            max_tokens=self.config.max_tokens,
            base_url=self.config.base_url,
        )
        data = json.dumps(body).encode("utf-8")
        headers = self._headers()
        log.info(
            "LLM POST %s model=%s bytes=%d timeout_s=%.0f",
            self.config.endpoint,
            self.config.model or "(default)",
            len(data),
            self.config.timeout_s,
        )

        error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            if attempt:
                self._sleep(float(attempt))
            req = urllib.request.Request(self.config.endpoint, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
                    text, finish = _content(json.loads(resp.read().decode("utf-8")))
                    self.last_finish_reason = finish
                    log.info(
                        "LLM OK chars=%d finish_reason=%s",
                        len(text),
                        finish or "-",
                    )
                    return text
            except urllib.error.HTTPError as exc:
                error = LLMError(f"HTTP {exc.code} from {self.config.endpoint}: {_http_body(exc)}")
                if exc.code < 500 and exc.code != 429:
                    raise error from exc
            except TimeoutError as exc:
                raise LLMError(f"timed out after {self.config.timeout_s:.0f}s") from exc
            except (urllib.error.URLError, ConnectionError, http.client.HTTPException) as exc:
                if isinstance(getattr(exc, "reason", None), TimeoutError):
                    raise LLMError(f"timed out after {self.config.timeout_s:.0f}s") from exc
                error = LLMError(f"{type(exc).__name__}: {exc}")
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise LLMError(f"invalid JSON from {self.config.endpoint}") from exc
        raise error or LLMError("request failed")

    def stream(
        self,
        *,
        system: str,
        user_text: str,
        reasoning: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Yield content deltas from an OpenAI-compatible SSE chat completion."""
        r = reasoning or self.config.reasoning
        if r not in _REASONING:
            raise LLMConfigError(f"reasoning={r!r}: expected {', '.join(_REASONING)}")
        tok = int(max_tokens) if max_tokens is not None else self.config.max_tokens
        body = build_body(
            system=system,
            user_text=user_text,
            model=self.config.model,
            temperature=self.config.temperature,
            reasoning=r,
            max_tokens=tok,
            base_url=self.config.base_url,
            stream=True,
        )
        data = json.dumps(body).encode("utf-8")
        headers = self._headers()
        req = urllib.request.Request(self.config.endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
                # Prefer line iteration for true streaming; fall back to full read.
                line_iter: Any
                if hasattr(resp, "__iter__") and not isinstance(resp, (bytes, str)):
                    line_iter = resp
                else:
                    line_iter = io.BytesIO(resp.read())

                for raw_line in line_iter:
                    if isinstance(raw_line, bytes):
                        line = raw_line.decode("utf-8", "replace")
                    else:
                        line = str(raw_line)
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = _as_text(delta.get("content"))
                    if piece:
                        yield piece
                    fr = choices[0].get("finish_reason")
                    if fr:
                        self.last_finish_reason = str(fr)
        except urllib.error.HTTPError as exc:
            raise LLMError(
                f"HTTP {exc.code} from {self.config.endpoint}: {_http_body(exc)}"
            ) from exc
        except TimeoutError as exc:
            raise LLMError(f"timed out after {self.config.timeout_s:.0f}s") from exc
        except (urllib.error.URLError, ConnectionError, http.client.HTTPException) as exc:
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                raise LLMError(f"timed out after {self.config.timeout_s:.0f}s") from exc
            raise LLMError(f"{type(exc).__name__}: {exc}") from exc
