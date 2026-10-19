"""Compile .tex → PDF (primary) / DOCX (secondary) via Docker image case-3:tex."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from case3.tex_preamble import (
    TexStructureError,
    assert_tex_structure,
    ensure_document_preamble,
    strip_orphan_slots,
)

log = logging.getLogger("case3.render")

IMAGE = os.environ.get("CASE3_IMAGE", "case-3:tex")


class RenderError(RuntimeError):
    """LaTeX/Docker failed; optional path to saved .log."""

    def __init__(self, message: str, *, log_path: Path | None = None) -> None:
        super().__init__(message)
        self.log_path = log_path


def _docker_run(workdir: Path, *cmd: str) -> None:
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
            f"{workdir.resolve().as_posix()}:/work",
            "-w",
            "/work",
            IMAGE,
            *cmd,
        ]
    else:
        args = [
            "docker",
            "run",
            "--rm",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--net=none",
            "-e",
            "HOME=/work",
            "-e",
            "XDG_CACHE_HOME=/work/.cache",
            "-v",
            f"{workdir.resolve().as_posix()}:/work",
            "-w",
            "/work",
            IMAGE,
            *cmd,
        ]
    log.info("exec: %s", " ".join(args))
    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        tail = ((exc.stderr or "") + "\n" + (exc.stdout or ""))[-2000:]
        raise RenderError(
            f"docker {' '.join(cmd[:2])} failed (exit {exc.returncode}): {tail.strip()}"
        ) from exc


def ensure_image() -> None:
    r = subprocess.run(
        ["docker", "image", "inspect", IMAGE], capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RenderError(f"Docker image {IMAGE!r} missing. Run: scripts\\setup.cmd")


def _save_tex_logs(work: Path, stem: str, log_dir: Path | None) -> Path | None:
    if log_dir is None:
        return None
    log_dir.mkdir(parents=True, exist_ok=True)
    saved = None
    for name in (f"{stem}.log", f"{stem}.blg", "texput.log"):
        src = work / name
        if src.is_file():
            dest = log_dir / name
            shutil.copy2(src, dest)
            saved = dest
            log.info("saved TeX log → %s", dest)
    return saved


def prepare_tex_source(tex_path: Path) -> str:
    """Harden .tex on disk before Docker: structure, slots, preamble."""
    raw = tex_path.read_text(encoding="utf-8")
    try:
        assert_tex_structure(raw)
    except TexStructureError as exc:
        raise RenderError(str(exc)) from exc
    hardened = ensure_document_preamble(strip_orphan_slots(raw))
    if hardened != raw:
        tex_path.write_text(hardened, encoding="utf-8")
        log.info("hardened TeX preamble/slots → %s", tex_path)
    return hardened


def render_tex(
    tex_path: Path,
    *,
    out_dir: Path,
    formats: set[str],
    extra_dirs: list[Path] | None = None,
    log_dir: Path | None = None,
) -> dict[str, Path]:
    ensure_image()
    tex_path = tex_path.resolve()
    prepare_tex_source(tex_path)
    stem = tex_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}

    with tempfile.TemporaryDirectory(prefix="case3-") as tmp:
        work = Path(tmp)
        (work / ".cache").mkdir()
        shutil.copy2(tex_path, work / tex_path.name)
        for d in extra_dirs or []:
            if d.is_dir():
                dest = work / d.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(d, dest)

        # PDF is the primary, reliable artifact.
        if "pdf" in formats:
            try:
                _docker_run(
                    work,
                    "latexmk",
                    "-xelatex",
                    "-interaction=nonstopmode",
                    "-synctex=1",
                    tex_path.name,
                )
            except RenderError as exc:
                saved = _save_tex_logs(work, stem, log_dir)
                raise RenderError(str(exc), log_path=saved) from exc

            pdf_src = work / f"{stem}.pdf"
            if not pdf_src.is_file():
                saved = _save_tex_logs(work, stem, log_dir)
                raise RenderError("latexmk did not produce PDF", log_path=saved)
            _save_tex_logs(work, stem, log_dir)
            pdf_dst = out_dir / f"{stem}.pdf"
            shutil.copy2(pdf_src, pdf_dst)
            results["pdf"] = pdf_dst
            log.info("wrote %s", pdf_dst)

        # DOCX is best-effort from the same .tex (+ extracted media for PNGs).
        if "docx" in formats:
            media_dir = "docx_media"
            try:
                _docker_run(
                    work,
                    "pandoc",
                    tex_path.name,
                    "-f",
                    "latex",
                    "-t",
                    "docx",
                    f"--extract-media=./{media_dir}",
                    "-o",
                    f"{stem}.docx",
                )
            except RenderError as exc:
                raise RenderError(str(exc), log_path=None) from exc
            docx_src = work / f"{stem}.docx"
            if not docx_src.is_file():
                raise RenderError("pandoc did not produce DOCX")
            docx_dst = out_dir / f"{stem}.docx"
            shutil.copy2(docx_src, docx_dst)
            results["docx"] = docx_dst
            media_src = work / media_dir
            if media_src.is_dir() and any(media_src.rglob("*")):
                media_dst = out_dir / media_dir
                if media_dst.exists():
                    shutil.rmtree(media_dst)
                shutil.copytree(media_src, media_dst)
            log.info("wrote %s (DOCX is secondary to PDF)", docx_dst)

    return results
