"""Post-LLM prose harden: obvious bullet lines → itemize (PDF task 4)."""

from __future__ import annotations

import re

# Environments whose body must not be rewritten.
_SKIP_ENVS = (
    "itemize",
    "enumerate",
    "description",
    "tabular",
    "tabularx",
    "table",
    "figure",
    "verbatim",
    "lstlisting",
    "minted",
    "tikzpicture",
)

_BULLET_LINE = re.compile(r"^([ \t]*)([-•])\s+(\S.*)$")
_BEGIN_ENV = re.compile(r"\\begin\{([a-zA-Z*]+)\}")
_END_ENV = re.compile(r"\\end\{([a-zA-Z*]+)\}")


def harden_prose_lists(tex: str) -> str:
    """Turn consecutive ``- `` / ``• `` lines outside skip-envs into itemize.

    Leaves existing itemize/enumerate/tabular bodies untouched. Idempotent.
    """
    if not tex or ("- " not in tex and "•" not in tex and "• " not in tex):
        # Fast path: still allow "•foo" without space? require space via regex.
        if "•" not in tex and "- " not in tex:
            return tex

    lines = tex.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    depth: list[str] = []

    def in_skip() -> bool:
        return any(e.rstrip("*") in _SKIP_ENVS for e in depth)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip("\n")
        # Track env stack (best-effort; nested same-name ok).
        for m in _BEGIN_ENV.finditer(stripped):
            depth.append(m.group(1))
        for m in _END_ENV.finditer(stripped):
            name = m.group(1)
            for j in range(len(depth) - 1, -1, -1):
                if depth[j] == name:
                    del depth[j]
                    break

        if in_skip():
            out.append(line)
            i += 1
            continue

        m = _BULLET_LINE.match(stripped.rstrip("\r"))
        if not m:
            out.append(line)
            i += 1
            continue

        # Collect consecutive bullet lines at this depth.
        bullets: list[str] = []
        indent = m.group(1)
        while i < len(lines):
            raw = lines[i]
            s = raw.strip("\n").rstrip("\r")
            bm = _BULLET_LINE.match(s)
            if not bm:
                break
            # Don't advance env tracking twice — peek only bullets.
            bullets.append(bm.group(3).strip())
            i += 1

        if len(bullets) < 1:
            out.append(line)
            i += 1
            continue

        block = [f"{indent}\\begin{{itemize}}\n"]
        for item in bullets:
            block.append(f"{indent}\\item {item}\n")
        block.append(f"{indent}\\end{{itemize}}\n")
        out.extend(block)

    return "".join(out)
