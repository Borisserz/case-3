"""Unpack vendored Playwright Chromium for the linux/amd64 image."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path("/ms-playwright")
PAIRS = (
    ("/tmp/pw/chrome-linux64.zip", "chromium-1255"),
    ("/tmp/pw/chrome-headless-shell-linux64.zip", "chromium_headless_shell-1255"),
)


def main() -> None:
    for src, name in PAIRS:
        dest = ROOT / name
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as archive:
            archive.extractall(dest)
            for info in archive.infolist():
                mode = (info.external_attr >> 16) & 0o777
                if mode:
                    os.chmod(dest / info.filename, mode)
        (dest / "INSTALLATION_COMPLETE").write_text("1255\n", encoding="utf-8")


if __name__ == "__main__":
    main()
