"""Post-LLM prose harden: obvious bullet lines → itemize (PDF task 4)."""

from __future__ import annotations

import re

# LLM often closes \\textbf{…} with Markdown ** — microtype then sees \\par
# inside an unfinished argument (Runaway argument / MT@prot@check@F@).
_TEXTBF_MARKDOWN_CLOSE = re.compile(
    r"\\textbf\{([^{}\n]*?)\*\*(?!\*)",
)
_MARKDOWN_BOLD = re.compile(r"(?<!\\)\*\*([^*\n]{1,200}?)\*\*")


_ITEM_OR_END = re.compile(r"\n[ \t]*\\(item|end|begin|section|subsection|chapter)\b")


def fix_unclosed_textbf(tex: str) -> str:
    """Close ``\\textbf{…`` that never gets ``}`` before next ``\\item`` / env / EOF.

    LLM often drops the closing brace mid-question; microtype then runaway-parses
    into the rest of the document (``MT@prot@check@F@`` / fake enumerate error).
    """
    if not tex or r"\textbf{" not in tex:
        return tex
    out: list[str] = []
    i = 0
    needle = r"\textbf{"
    while i < len(tex):
        if tex.startswith(needle, i):
            out.append(needle)
            i += len(needle)
            depth = 1
            while i < len(tex) and depth > 0:
                ch = tex[i]
                if ch == "{":
                    depth += 1
                    out.append(ch)
                    i += 1
                elif ch == "}":
                    depth -= 1
                    out.append(ch)
                    i += 1
                elif ch == "\n" and depth == 1:
                    # Next structural token → close bold before it.
                    if _ITEM_OR_END.match(tex, i) or tex.startswith("\n\n", i):
                        out.append("}")
                        depth = 0
                        break
                    out.append(ch)
                    i += 1
                else:
                    out.append(ch)
                    i += 1
            if depth > 0:
                out.append("}")
        else:
            out.append(tex[i])
            i += 1
    return "".join(out)


# \\section / \\subsection go through \\@dblarg → \\@xdblarg. Missing ``}`` yields
# ``File ended while scanning use of \\@xdblarg`` (latexmk exit 12).
_HEADING_OPEN = re.compile(
    r"\\(chapter|section|subsection|subsubsection|paragraph)\*?\{"
)


def fix_unclosed_heading_args(tex: str) -> str:
    """Close ``\\section{…`` / ``\\subsection{…`` when the brace never closes.

    Titles are single-line in our reports: at depth 1, a newline ends the title.
    """
    if not tex or not _HEADING_OPEN.search(tex):
        return tex
    out: list[str] = []
    i = 0
    while i < len(tex):
        m = _HEADING_OPEN.match(tex, i)
        if not m:
            out.append(tex[i])
            i += 1
            continue
        out.append(m.group(0))
        i = m.end()
        depth = 1
        while i < len(tex) and depth > 0:
            ch = tex[i]
            if ch == "{":
                depth += 1
                out.append(ch)
                i += 1
            elif ch == "}":
                depth -= 1
                out.append(ch)
                i += 1
            elif ch == "\n" and depth == 1:
                out.append("}")
                depth = 0
                break
            else:
                out.append(ch)
                i += 1
        if depth > 0:
            out.append("}")
    return "".join(out)


# Unclosed \\caption{…} → runaway + \\Gin@iii / figure ended by \\end{document}.
_CAPTION_OPEN = re.compile(r"\\caption\*?\{")
_CAPTION_STOP = re.compile(
    r"\n[ \t]*\\"
    r"(end\{(?:figure|table|document)\}|label\{|begin\{|caption\b|"
    r"includegraphics\b|section\b|subsection\b|chapter\b)"
)


def fix_unclosed_caption_args(tex: str) -> str:
    """Close ``\\caption{…`` before float end / blank line / next structural cmd."""
    if not tex or not _CAPTION_OPEN.search(tex):
        return tex
    out: list[str] = []
    i = 0
    while i < len(tex):
        m = _CAPTION_OPEN.match(tex, i)
        if not m:
            out.append(tex[i])
            i += 1
            continue
        out.append(m.group(0))
        i = m.end()
        depth = 1
        while i < len(tex) and depth > 0:
            ch = tex[i]
            if ch == "{":
                depth += 1
                out.append(ch)
                i += 1
            elif ch == "}":
                depth -= 1
                out.append(ch)
                i += 1
            elif ch == "\n" and depth == 1:
                if tex.startswith("\n\n", i) or _CAPTION_STOP.match(tex, i):
                    out.append("}")
                    depth = 0
                    break
                out.append(ch)
                i += 1
            else:
                out.append(ch)
                i += 1
        if depth > 0:
            out.append("}")
    return "".join(out)


_FLOAT_ENVS = ("figure", "table")


def fix_unclosed_float_envs(tex: str) -> str:
    """Insert missing ``\\end{figure|table}`` immediately before ``\\end{document}``."""
    if not tex or r"\end{document}" not in tex:
        return tex
    end_doc = tex.rfind(r"\end{document}")
    head = tex[:end_doc]
    tail = tex[end_doc:]
    closes: list[str] = []
    for env in _FLOAT_ENVS:
        opens = len(re.findall(rf"\\begin\{{{env}\}}", head))
        ends = len(re.findall(rf"\\end\{{{env}\}}", head))
        for _ in range(max(0, opens - ends)):
            closes.append(f"\\end{{{env}}}")
    if not closes:
        return tex
    return head.rstrip() + "\n" + "\n".join(closes) + "\n" + tail


def fix_markdown_bold_leaks(tex: str) -> str:
    """Repair ``\\textbf{…**``, leftover ``**…**``, and unclosed ``\\textbf{``."""
    if not tex:
        return tex
    out = tex
    if "**" in out:
        out = _TEXTBF_MARKDOWN_CLOSE.sub(r"\\textbf{\1}", out)
        out = _MARKDOWN_BOLD.sub(r"\\textbf{\1}", out)
    return fix_unclosed_textbf(out)


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

# Markdown ``* `` / ``- `` / ``• `` — LLM outline dumps use asterisks a lot.
_BULLET_LINE = re.compile(r"^([ \t]*)([-•*])\s+(\S.*)$")
_BEGIN_ENV = re.compile(r"\\begin\{([a-zA-Z*]+)\}")
_END_ENV = re.compile(r"\\end\{([a-zA-Z*]+)\}")
# Emoji / dingbats in \\section titles break Liber print look (Win desk 070133).
_EMOJI_IN_TITLE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs
    "\U00002700-\U000027BF"  # dingbats
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE0F"  # variation selector
    "]+",
)


def scrub_emoji_from_headings(tex: str) -> str:
    """Strip emoji from ``\\section{…}`` / ``\\subsection{…}`` titles."""
    if not tex or not _HEADING_OPEN.search(tex):
        return tex
    out: list[str] = []
    i = 0
    while i < len(tex):
        m = _HEADING_OPEN.match(tex, i)
        if not m:
            out.append(tex[i])
            i += 1
            continue
        out.append(m.group(0))
        i = m.end()
        depth = 1
        title_chars: list[str] = []
        while i < len(tex) and depth > 0:
            ch = tex[i]
            if ch == "{":
                depth += 1
                title_chars.append(ch)
                i += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cleaned = _EMOJI_IN_TITLE.sub("", "".join(title_chars))
                    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip(" \t")
                    out.append(cleaned)
                    out.append("}")
                    i += 1
                else:
                    title_chars.append(ch)
                    i += 1
            else:
                title_chars.append(ch)
                i += 1
        if depth > 0:
            cleaned = _EMOJI_IN_TITLE.sub("", "".join(title_chars))
            out.append(cleaned)
            out.append("}")
    return "".join(out)


def harden_prose_lists(tex: str) -> str:
    """Turn consecutive ``- `` / ``• `` / ``* `` lines outside skip-envs into itemize.

    Leaves existing itemize/enumerate/tabular bodies untouched. Idempotent.
    """
    if not tex or (
        "- " not in tex and "* " not in tex and "•" not in tex and "• " not in tex
    ):
        # Fast path: still allow "•foo" without space? require space via regex.
        if "•" not in tex and "- " not in tex and "* " not in tex:
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
