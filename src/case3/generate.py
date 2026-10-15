"""Generate .tex from a text file (text-to-text LLM only)."""

from __future__ import annotations

import logging
from pathlib import Path

from case3.llm_client import LLMClient, LLMConfig
from case3.tex_utils import extract_tex

log = logging.getLogger("case3.generate")


def _repo_root() -> Path:
    # src/case3/generate.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def load_system_prompt() -> str:
    path = _repo_root() / "prompts" / "system_tex.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}")
    return path.read_text(encoding="utf-8")


def load_gold_appendix(gold_dir: Path, *, max_chars: int = 8000) -> str:
    if not gold_dir.is_dir():
        return ""
    chunks: list[str] = []
    size = 0
    for p in sorted(gold_dir.glob("*.tex")):
        body = p.read_text(encoding="utf-8").strip()
        block = f"### {p.name}\n```latex\n{body}\n```\n"
        if size + len(block) > max_chars:
            break
        chunks.append(block)
        size += len(block)
    if not chunks:
        return ""
    return (
        "\n\n## Gold examples (follow style; do not copy unrelated content)\n\n"
        + "\n".join(chunks)
    )


def resolve_text_file(path: Path) -> Path:
    path = path.resolve()
    if path.is_file():
        if path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError(f"expected .txt/.md file, got: {path}")
        return path
    raise FileNotFoundError(f"not a text file: {path}")


def build_user_prompt(text: str) -> str:
    return "\n".join(
        [
            "Convert the following source text into ONE complete XeLaTeX article.",
            "Use the skeleton rules from the system prompt (DejaVu, polyglossia russian).",
            "Return ONLY LaTeX (or a single ```latex fence). No commentary.",
            "Do NOT include \\includegraphics or invent images — text only.",
            "",
            "## Source text",
            text.strip(),
        ]
    )


def generate_tex(
    source: Path,
    *,
    out_tex: Path,
    gold_dir: Path | None = None,
    client: LLMClient | None = None,
    dry_run: bool = False,
) -> Path:
    text_path = resolve_text_file(source)
    text = text_path.read_text(encoding="utf-8")
    stem = text_path.stem
    root = _repo_root()

    system = load_system_prompt()
    system = system + load_gold_appendix(gold_dir or (root / "gold"))
    user = build_user_prompt(text)
    log.info("source=%s (%d chars)", text_path, len(text))

    if dry_run:
        stub = Path(__file__).resolve().parent / "templates" / "article_skeleton.tex"
        body = stub.read_text(encoding="utf-8")
        body = body.replace("%%CONTENT%%", text[:2000].replace("\\", "/"))
        out_tex.parent.mkdir(parents=True, exist_ok=True)
        out_tex.write_text(body, encoding="utf-8")
        log.info("dry-run wrote %s", out_tex)
        return out_tex

    cfg = LLMConfig.from_env()
    llm = client or LLMClient(cfg)
    raw = llm.complete(system=system, user_text=user)
    tex = extract_tex(raw)
    out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_tex.write_text(tex, encoding="utf-8")
    (out_tex.parent / f"{stem}.raw_model.txt").write_text(raw, encoding="utf-8")
    log.info("wrote %s (%d chars)", out_tex, len(tex))
    return out_tex
