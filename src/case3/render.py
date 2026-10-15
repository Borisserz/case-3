"""Compile .tex → PDF/DOCX via Docker image case-3:tex."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("case3.render")

IMAGE = os.environ.get("CASE3_IMAGE", "case-3:tex")


def _docker_run(workdir: Path, *cmd: str) -> None:
    args = [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "1000:1000",
        "--net=none",
        "-e",
        "HOME=/work",
        "-e",
        "XDG_CACHE_HOME=/work/.cache",
        "-v",
        f"{workdir}:/work",
        "-w",
        "/work",
        IMAGE,
        *cmd,
    ]
    # Windows Docker Desktop: --user often breaks volume writes; omit on nt
    if os.name == "nt":
        args = [
            "docker",
            "run",
            "--rm",
            "--net=none",
            "-e",
            "HOME=/work",
            "-e",
            "XDG_CACHE_HOME=/work/.cache",
            "-v",
            f"{workdir}:/work",
            "-w",
            "/work",
            IMAGE,
            *cmd,
        ]
    log.info("exec: %s", " ".join(args))
    subprocess.run(args, check=True)


def ensure_image() -> None:
    r = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Docker image {IMAGE!r} missing. Run: docker compose build")


def render_tex(
    tex_path: Path,
    *,
    out_dir: Path,
    formats: set[str],
    asset_dirs: list[Path] | None = None,
) -> dict[str, Path]:
    """formats subset of {'pdf','docx'}."""
    ensure_image()
    tex_path = tex_path.resolve()
    stem = tex_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}

    with tempfile.TemporaryDirectory(prefix="case3-") as tmp:
        work = Path(tmp)
        (work / ".cache").mkdir()
        shutil.copy2(tex_path, work / tex_path.name)
        for ad in asset_dirs or []:
            if ad.is_dir():
                dest = work / ad.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(ad, dest)
        # also copy sibling images/ next to tex if present
        sib = tex_path.parent / "images"
        if sib.is_dir() and not (work / "images").exists():
            shutil.copytree(sib, work / "images")

        if "pdf" in formats:
            _docker_run(
                work,
                "latexmk",
                "-xelatex",
                "-interaction=nonstopmode",
                "-synctex=1",
                tex_path.name,
            )
            pdf_src = work / f"{stem}.pdf"
            if not pdf_src.is_file():
                raise RuntimeError("latexmk did not produce PDF — see logs")
            pdf_dst = out_dir / f"{stem}.pdf"
            shutil.copy2(pdf_src, pdf_dst)
            results["pdf"] = pdf_dst
            log.info("wrote %s", pdf_dst)

        if "docx" in formats:
            _docker_run(work, "pandoc", tex_path.name, "-o", f"{stem}.docx")
            docx_src = work / f"{stem}.docx"
            docx_dst = out_dir / f"{stem}.docx"
            shutil.copy2(docx_src, docx_dst)
            results["docx"] = docx_dst
            log.info("wrote %s", docx_dst)

    return results
