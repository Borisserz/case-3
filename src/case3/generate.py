"""Generate .tex from job folder (content.txt + images/) via Qwen API."""

from __future__ import annotations

import logging
from pathlib import Path

from case3.llm_client import LLMClient, LLMConfig, image_data_url
from case3.tex_utils import extract_tex

log = logging.getLogger("case3.generate")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _pkg_file(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)


def load_system_prompt() -> str:
    candidates = [
        Path(__file__).resolve().parents[2] / "prompts" / "system_tex.md",
        _pkg_file("prompts", "system_tex.md"),
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError("prompts/system_tex.md not found")


def load_gold_appendix(gold_dir: Path, *, max_chars: int = 12000) -> str:
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


def find_job_text(job_dir: Path) -> Path:
    for name in ("content.txt", "content.md", "input.txt", "text.txt"):
        p = job_dir / name
        if p.is_file():
            return p
    txts = sorted(job_dir.glob("*.txt")) + sorted(job_dir.glob("*.md"))
    if not txts:
        raise FileNotFoundError(f"no .txt/.md in {job_dir}")
    return txts[0]


def find_images(job_dir: Path) -> list[Path]:
    dirs = [job_dir / "images", job_dir / "attachments", job_dir]
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.resolve() not in seen:
                # skip if sitting next to content and we already have images/
                if d == job_dir and (job_dir / "images").is_dir():
                    continue
                seen.add(p.resolve())
                out.append(p)
    return out


def build_user_prompt(text: str, image_names: list[str]) -> str:
    lines = [
        "Convert the following source material into ONE complete XeLaTeX article.",
        "Use the skeleton rules from the system prompt (DejaVu, polyglossia russian).",
        "Return ONLY LaTeX (or a single ```latex fence). No commentary.",
        "",
        "## Source text",
        text.strip(),
    ]
    if image_names:
        lines += [
            "",
            "## Available image files (use these exact relative paths under images/)",
            *[f"- images/{name}" for name in image_names],
            "Include each relevant image with \\includegraphics and \\caption / \\label.",
        ]
    return "\n".join(lines)


def generate_tex(
    job_dir: Path,
    *,
    out_tex: Path,
    gold_dir: Path | None = None,
    client: LLMClient | None = None,
    dry_run: bool = False,
) -> Path:
    job_dir = job_dir.resolve()
    text_path = find_job_text(job_dir)
    text = text_path.read_text(encoding="utf-8")
    images = find_images(job_dir)
    image_names = [p.name for p in images]

    system = load_system_prompt()
    if gold_dir is None:
        gold_dir = Path(__file__).resolve().parents[2] / "gold"
    system = system + load_gold_appendix(gold_dir)

    user = build_user_prompt(text, image_names)
    log.info("job=%s text=%s images=%d", job_dir.name, text_path.name, len(images))

    if dry_run:
        stub = _pkg_file("templates", "article_skeleton.tex")
        if not stub.is_file():
            stub = Path(__file__).resolve().parents[2] / "templates" / "article_skeleton.tex"
        body = stub.read_text(encoding="utf-8")
        body = body.replace("%%CONTENT%%", text[:2000].replace("\\", "/"))
        out_tex.parent.mkdir(parents=True, exist_ok=True)
        out_tex.write_text(body, encoding="utf-8")
        log.info("dry-run wrote %s", out_tex)
        return out_tex

    cfg = LLMConfig.from_env()
    llm = client or LLMClient(cfg)
    urls = [image_data_url(p, max_long_edge=cfg.max_long_edge) for p in images]
    raw = llm.complete(system=system, user_text=user, image_urls=urls)
    tex = extract_tex(raw)
    out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_tex.write_text(tex, encoding="utf-8")
    (out_tex.parent / "raw_model.txt").write_text(raw, encoding="utf-8")
    log.info("wrote %s (%d chars)", out_tex, len(tex))
    return out_tex
