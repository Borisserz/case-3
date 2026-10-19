"""Compile .tex → PDF (primary) / DOCX (secondary) via Docker image case-3:tex."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

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
    """Retry lookup — Docker daemon can flap under parallel load."""
    import time

    last = None
    for attempt in range(4):
        # `docker images -q` is more reliable than `image inspect` on some hosts.
        r = subprocess.run(
            ["docker", "images", "-q", IMAGE],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and (r.stdout or "").strip():
            return
        last = r
        time.sleep(0.35 * (attempt + 1))
    detail = ""
    if last is not None:
        detail = f" ({(last.stderr or last.stdout or '')[:120].strip()})"
    raise RenderError(
        f"Docker image {IMAGE!r} missing. Run: scripts\\setup.cmd{detail}"
    )


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


def _reference_docx(project_root: Path | None) -> Path | None:
    """Liber print-style Word template, if present."""
    roots: list[Path] = []
    if project_root is not None:
        roots.append(project_root.resolve())
    # case3/render.py → src/case3 → src → repo
    roots.append(Path(__file__).resolve().parents[2])
    for root in roots:
        cand = root / "assets" / "docx" / "reference.docx"
        if cand.is_file():
            return cand
    return None


def render_tex(
    tex_path: Path,
    *,
    out_dir: Path,
    formats: set[str],
    extra_dirs: list[Path] | None = None,
    log_dir: Path | None = None,
    force: bool = False,
    project_root: Path | None = None,
    on_format: Callable[[str], None] | None = None,
) -> dict[str, Path]:
    ensure_image()
    tex_path = tex_path.resolve()
    prepare_tex_source(tex_path)
    stem = tex_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}
    ref_docx = _reference_docx(project_root)

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
        if ref_docx is not None:
            shutil.copy2(ref_docx, work / "reference.docx")

        # PDF is the primary, reliable artifact.
        if "pdf" in formats:
            if on_format:
                on_format("pdf")
            try:
                latexmk_cmd = [
                    "latexmk",
                    "-xelatex",
                    "-interaction=nonstopmode",
                    "-synctex=1",
                ]
                # Chart edits keep the same .tex + same PNG paths — force
                # re-read figures so the last restyle lands in the PDF.
                if force:
                    latexmk_cmd.append("-g")
                latexmk_cmd.append(tex_path.name)
                _docker_run(
                    work,
                    *latexmk_cmd,
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

        # DOCX via pandoc + optional Liber reference.docx styles.
        if "docx" in formats:
            if on_format:
                on_format("docx")
            media_dir = "docx_media"
            pandoc_cmd = [
                "pandoc",
                tex_path.name,
                "-f",
                "latex",
                "-t",
                "docx",
            ]
            if (work / "reference.docx").is_file():
                pandoc_cmd.extend(["--reference-doc=reference.docx"])
            pandoc_cmd.extend(
                [
                    f"--extract-media=./{media_dir}",
                    "-o",
                    f"{stem}.docx",
                ]
            )
            try:
                _docker_run(work, *pandoc_cmd)
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
            log.info(
                "wrote %s%s",
                docx_dst,
                " (reference.docx)" if ref_docx else " (pandoc default)",
            )

    return results
