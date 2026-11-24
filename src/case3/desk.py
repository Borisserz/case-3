"""Local desk. `uv run inspectra` → http://127.0.0.1:8000

Chat and the site do not need Docker. PDF/DOCX print still uses the TeX image later.
"""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    reload = os.environ.get("CASE3_RELOAD", "").strip() == "1"
    uvicorn.run(
        "case3.api:app",
        host="127.0.0.1",
        port=8000,
        reload=reload,
    )
