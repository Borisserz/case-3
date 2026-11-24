# ADR-0026: The local desk starts with uv and npm

## Status
Accepted

## Date
2026-11-24

## Context
Opening the desk required Windows `scripts\api.cmd` / `scripts\web.cmd` and a Docker image before the site would start. The colleague asked for a local path without Docker: a Python 3.12 venv, `uv pip install -r requirements.txt`, `uv run`, and for the UI `npm i` then `npm run dev`. He thought the requirements file held five or six libraries.

## Decision
The desk starts as two commands in two terminals.

- API, from the repo root: `uv venv --python 3.12`, `uv pip install -r requirements.txt`, `uv run inspectra` (http://127.0.0.1:8000).
- UI, from `web/`: `npm i`, `npm run dev` (http://127.0.0.1:5173).

`requirements.txt` installs this repo (`-e .`) and the host libraries the API imports, including PDF and PPTX. That is more than six packages. TeX, Pandoc, and LibreOffice are not in the file. Docker and the Windows scripts stay in the repo for print and the existing desk; they are not the way to open the chat.

## Alternatives Considered

### Make bare `uv run` start the server
- Pros: matches the voice note word for word.
- Cons: `uv run` requires a command name. A fake default would surprise anyone who uses `uv run pytest`.
- Rejected because `uv run inspectra` is the one command that starts the desk.

### Drop the PDF libraries to look like a six-package file
- Pros: matches the guess in the note.
- Cons: dashboard PDF cells and decks import pdfplumber, pypdfium2, and python-pptx.
- Rejected because the desk would start and then fail on a real file.

## Consequences
- Positive: a new machine opens the chat and the site without Docker.
- Negative / follow-ups: PDF and DOCX print still need the TeX image. Charts need `uv run playwright install chromium` once.
