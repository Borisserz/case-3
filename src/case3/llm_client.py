"""OpenAI-compatible client (same pattern as bam-bam-bam VisionClient)."""

from __future__ import annotations

import base64
import http.client
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    max_long_edge: int = 2048
    temperature: float = 0.2
    reasoning: str = "low"

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
                "API not configured: set VISION_API_BASE_URL "
                "(e.g. http://127.0.0.1:8080 or LAN host at work)"
            )
        reasoning = (_env("VISION_REASONING", "CASE3_REASONING") or "low").lower()
        if reasoning not in _REASONING:
            raise LLMConfigError(f"reasoning={reasoning!r}: expected {', '.join(_REASONING)}")
        return cls(
            base_url=base,
            api_key=_env("VISION_API_KEY", "CASE3_API_KEY", "INGEST_VISION_API_KEY"),
            model=_env("VISION_MODEL", "CASE3_MODEL", "INGEST_VISION_MODEL"),
            timeout_s=_number("VISION_TIMEOUT_S", 300, float),
            max_retries=_number("VISION_MAX_RETRIES", 2, int),
            max_long_edge=_number("VISION_MAX_LONG_EDGE", 2048, int),
            temperature=_number("VISION_TEMPERATURE", 0.2, float),
            reasoning=reasoning,
        )


def image_data_url(path: Path, *, max_long_edge: int = 2048) -> str:
    """Encode image as data URL; optionally downscale long edge (Pillow)."""
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    raw = path.read_bytes()
    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
            w, h = im.size
            long_edge = max(w, h)
            if long_edge > max_long_edge:
                scale = max_long_edge / long_edge
                im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            buf = io.BytesIO()
            fmt = "JPEG" if mime == "image/jpeg" else "PNG"
            im.save(buf, format=fmt)
            raw = buf.getvalue()
            mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    except Exception:
        pass
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return "".join(p.get("text", "") for p in value if isinstance(p, dict))
    return value if isinstance(value, str) else ""


def _after_think(raw: str) -> str:
    text = _THINK.sub("", raw)
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()


def _content(data: Any) -> str:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected response: {str(data)[:200]}") from exc
    if not isinstance(message, dict):
        raise LLMError(f"unexpected response: {str(data)[:200]}")
    content_raw = _as_text(message.get("content"))
    cleaned = _after_think(content_raw)
    if cleaned:
        return cleaned
    for key in ("reasoning_content", "reasoning"):
        got = _after_think(_as_text(message.get(key)))
        if got:
            return got
    raise LLMError("empty response")


def _http_body(exc: urllib.error.HTTPError) -> str:
    try:
        return " ".join(exc.read()[:300].decode("utf-8", "replace").split())
    except (OSError, http.client.HTTPException):
        return ""


def build_body(
    *,
    system: str,
    user_text: str,
    image_urls: Sequence[str] = (),
    model: str | None = None,
    temperature: float = 0.2,
    reasoning: str = "low",
) -> dict[str, Any]:
    thinking: dict[str, Any] = (
        {"enable_thinking": False}
        if reasoning == "off"
        else {"enable_thinking": True, "resolved_reasoning_effort": reasoning}
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    body: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        "temperature": temperature,
        "chat_template_kwargs": thinking,
    }
    if model:
        body["model"] = model
    return body


class LLMClient:
    """POST {base}/v1/chat/completions — text-only or text+images."""

    def __init__(self, config: LLMConfig, *, sleep: Callable[[float], None] = time.sleep) -> None:
        self.config = config
        self._sleep = sleep

    def complete(
        self,
        *,
        system: str,
        user_text: str,
        image_urls: Sequence[str] = (),
        reasoning: str | None = None,
    ) -> str:
        r = reasoning or self.config.reasoning
        if r not in _REASONING:
            raise LLMConfigError(f"reasoning={r!r}: expected {', '.join(_REASONING)}")
        body = build_body(
            system=system,
            user_text=user_text,
            image_urls=image_urls,
            model=self.config.model,
            temperature=self.config.temperature,
            reasoning=r,
        )
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            if attempt:
                self._sleep(float(attempt))
            req = urllib.request.Request(self.config.endpoint, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
                    return _content(json.loads(resp.read().decode("utf-8")))
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
