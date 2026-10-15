"""Parse LLM reply: ```latex ... ``` then ```json ... ```."""

from __future__ import annotations

import json
import re
from typing import Any

from case3.tex_utils import extract_tex

_FENCE = re.compile(r"```(\w*)\s*([\s\S]*?)```", re.I)
_ID_OK = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def parse_model_output(raw: str, *, max_images: int) -> tuple[str, list[dict[str, Any]]]:
    fences = [(m.group(1).lower(), m.group(2).strip()) for m in _FENCE.finditer(raw or "")]
    tex_body = None
    json_body = None
    for lang, body in fences:
        if lang in ("latex", "tex") and tex_body is None:
            tex_body = body
        elif lang in ("json", "") and json_body is None and body.lstrip().startswith("{"):
            json_body = body
        elif lang == "json" and json_body is None:
            json_body = body

    if tex_body is None:
        tex = extract_tex(raw)
    else:
        tex = extract_tex("```latex\n" + tex_body + "\n```")

    figures: list[dict[str, Any]] = []
    if json_body and max_images > 0:
        try:
            data = json.loads(json_body)
        except json.JSONDecodeError:
            data = {}
        raw_figs = data.get("figures") if isinstance(data, dict) else None
        if isinstance(raw_figs, list):
            for item in raw_figs:
                if not isinstance(item, dict):
                    continue
                fid = str(item.get("id", "")).strip()
                prompt = str(item.get("prompt", "")).strip()
                if not _ID_OK.match(fid) or not prompt:
                    continue
                figures.append(
                    {
                        "id": fid,
                        "caption": str(item.get("caption", "")).strip() or fid,
                        "prompt": prompt,
                        "width": str(item.get("width", r"0.85\textwidth")).strip(),
                    }
                )
                if len(figures) >= max_images:
                    break
    return tex, figures
