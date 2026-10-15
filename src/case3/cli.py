"""CLI: case3 run notes.txt → PDF/DOCX."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from case3.envfile import load_dotenv
from case3.llm_client import LLMConfigError, LLMError


def _root() -> Path:
    here = Path(__file__).resolve()
    cand = here.parents[2]
    if (cand / "Dockerfile").is_file():
        return cand
    return Path.cwd()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        prog="case3",
        description="Text → LaTeX (Qwen) → PDF/DOCX",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="notes.txt → LLM → PDF/DOCX")
    p_run.add_argument("input", type=Path, help=".txt/.md in project root")
    p_run.add_argument("--format", choices=("pdf", "docx", "both"), default="both")
    p_run.add_argument("--dry-run", action="store_true")

    p_gen = sub.add_parser("generate", help="Only LLM → .tex")
    p_gen.add_argument("input", type=Path)
    p_gen.add_argument("-o", "--output", type=Path, default=None)
    p_gen.add_argument("--dry-run", action="store_true")

    p_ren = sub.add_parser("render", help="Only .tex → PDF/DOCX")
    p_ren.add_argument("tex", type=Path)
    p_ren.add_argument("-o", "--out-dir", type=Path, default=None)
    p_ren.add_argument("--format", choices=("pdf", "docx", "both"), default="both")

    args = parser.parse_args(argv)
    root = _root()
    load_dotenv(root / ".env")

    try:
        if args.cmd == "run":
            from case3.pipeline import run_pipeline

            fmt = {"pdf", "docx"} if args.format == "both" else {args.format}
            out = run_pipeline(args.input, project_root=root, formats=fmt, dry_run=args.dry_run)
            print(out)
            return 0

        if args.cmd == "generate":
            from case3.generate import generate_tex, resolve_text_file

            src = resolve_text_file(args.input)
            out = args.output or (root / "work" / f"{src.stem}.tex")
            generate_tex(src, out_tex=out, gold_dir=root / "gold", dry_run=args.dry_run)
            print(out)
            return 0

        if args.cmd == "render":
            from case3.render import render_tex

            out_dir = args.out_dir or (root / "out")
            fmt = {"pdf", "docx"} if args.format == "both" else {args.format}
            arts = render_tex(args.tex, out_dir=out_dir, formats=fmt)
            for k, v in arts.items():
                print(f"{k}: {v}")
            return 0
    except (LLMConfigError, LLMError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("See logs\\  then: scripts\\push-debug.cmd", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
