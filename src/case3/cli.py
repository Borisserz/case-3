"""CLI entry: case3 generate|render|run|push-debug helpers."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def _root() -> Path:
    # src/case3/cli.py → parents[2] = repo root when editable; else cwd
    here = Path(__file__).resolve()
    cand = here.parents[2]
    if (cand / "Dockerfile").is_file():
        return cand
    return Path.cwd()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="case3", description="Text/images → LaTeX → PDF/DOCX")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Full pipeline for a job folder")
    p_run.add_argument("job", type=Path, help="Job dir with content.txt and optional images/")
    p_run.add_argument("--format", choices=("pdf", "docx", "both"), default="both")
    p_run.add_argument("--dry-run", action="store_true", help="Skip LLM; use skeleton template")

    p_gen = sub.add_parser("generate", help="Only LLM → .tex")
    p_gen.add_argument("job", type=Path)
    p_gen.add_argument("-o", "--output", type=Path, default=None)
    p_gen.add_argument("--dry-run", action="store_true")

    p_ren = sub.add_parser("render", help="Only .tex → PDF/DOCX")
    p_ren.add_argument("tex", type=Path)
    p_ren.add_argument("-o", "--out-dir", type=Path, default=None)
    p_ren.add_argument("--format", choices=("pdf", "docx", "both"), default="both")

    args = parser.parse_args(argv)
    root = _root()

    if args.cmd == "run":
        from case3.pipeline import run_job

        fmt = {"pdf", "docx"} if args.format == "both" else {args.format}
        out = run_job(args.job, project_root=root, formats=fmt, dry_run=args.dry_run)
        print(out)
        return 0

    if args.cmd == "generate":
        from case3.generate import generate_tex

        out = args.output or (root / "work" / f"{args.job.name}.tex")
        generate_tex(args.job, out_tex=out, gold_dir=root / "gold", dry_run=args.dry_run)
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

    return 1


if __name__ == "__main__":
    sys.exit(main())
