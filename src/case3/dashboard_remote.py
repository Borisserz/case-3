"""Read a Stimulsoft viewer service: /viewer stays open, GET /shot returns the files."""

from __future__ import annotations

import base64
import binascii
import io
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from case3.dashboard_source import DashboardSourceError


class DashboardRemoteError(Exception):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class ShotFile:
    name: str
    ext: str
    data: bytes


def service_base() -> str:
    raw = (os.environ.get("DASHBOARD_SERVICE_URL") or "http://127.0.0.1:8040").strip()
    return raw.rstrip("/") or "http://127.0.0.1:8040"


def viewer_url() -> str:
    return f"{service_base()}/viewer"


def _ext(item: dict) -> str:
    kind = str(item.get("kind") or "").lower()
    name = str(item.get("name") or "")
    if kind in {"png", "pdf"}:
        return kind
    if name.lower().endswith(".pdf"):
        return "pdf"
    return "png"


def _safe_name(name: str) -> str:
    base = Path(str(name or "")).name
    if not base or base in {".", ".."} or base != str(name):
        return ""
    return base


def _items(payload: dict) -> list[dict]:
    found: list[dict] = []
    png = payload.get("png")
    if isinstance(png, dict):
        found.append(png)
    for item in payload.get("pdfs") or []:
        if isinstance(item, dict):
            found.append(item)
    return found


def _read_local(path: str) -> bytes | None:
    """Same machine as the viewer: his JSON path is a real file."""
    try:
        file = Path(path)
        if not file.is_file():
            return None
        size = file.stat().st_size
        if size <= 0 or size > 40 * 1024 * 1024:
            return None
        return file.read_bytes()
    except OSError:
        return None


def files_from_shot(payload: dict, fetch_named) -> list[ShotFile]:
    """Bytes from /shot. A disk path on another machine is not a file."""
    files: list[ShotFile] = []
    for item in _items(payload):
        name = str(item.get("name") or "dashboard").strip() or "dashboard"
        ext = _ext(item)
        data: bytes | None = None
        encoded = item.get("data_b64")
        if isinstance(encoded, str) and encoded.strip():
            try:
                data = base64.b64decode(encoded, validate=False)
            except (binascii.Error, ValueError) as exc:
                raise DashboardRemoteError(
                    f"{name}: битый data_b64",
                    "bad_b64",
                ) from exc
        else:
            raw_path = item.get("path")
            if isinstance(raw_path, str) and raw_path.strip():
                data = _read_local(raw_path.strip())
            if not data:
                safe = _safe_name(name)
                data = fetch_named(safe) if safe else None
            if not data:
                shown = raw_path.strip() if isinstance(raw_path, str) else name
                raise DashboardRemoteError(
                    f"Сервис вернул путь {shown}, но этого файла нет на компьютере, "
                    f"где запущен Liber. API должен стоять на той же машине, что и его сервис.",
                    "no_bytes",
                )
        if not data:
            raise DashboardRemoteError(f"{name}: пустой файл", "no_bytes")
        files.append(ShotFile(name=name, ext=ext, data=data))
    return files


def join_pdfs(parts: list[bytes]) -> bytes | None:
    """One PDF for parse_dashboard, the same slot the settings drop uses."""
    blobs = [part for part in parts if part]
    if not blobs:
        return None
    if len(blobs) == 1:
        return blobs[0]
    import pypdfium2 as pdfium

    out = pdfium.PdfDocument.new()
    opened = []
    try:
        for raw in blobs:
            src = pdfium.PdfDocument(raw)
            opened.append(src)
            out.import_pages(src)
        sink = io.BytesIO()
        out.save(sink)
        return sink.getvalue()
    finally:
        for src in opened:
            src.close()
        out.close()


def capture_documents(payload: dict, fetch_named, parse) -> list[dict]:
    """One markdown: PNG and every table PDF go through parse_dashboard together."""
    if not isinstance(payload, dict) or not payload.get("ok"):
        detail = ""
        if isinstance(payload, dict):
            detail = str(payload.get("error") or "")
        raise DashboardRemoteError(detail or "снимок не удался", "shot_failed")
    files = files_from_shot(payload, fetch_named)
    pngs = [item for item in files if item.ext == "png"]
    pdfs = [item for item in files if item.ext == "pdf"]
    png = pngs[0].data if pngs else None
    pdf = join_pdfs([item.data for item in pdfs])
    if png is None and pdf is None:
        raise DashboardRemoteError("в снимке нет PNG и PDF", "empty")
    try:
        result = parse(png=png, pdf=pdf)
    except DashboardSourceError as exc:
        raise DashboardRemoteError(exc.message, exc.code) from exc
    source_name = pngs[0].name if pngs else pdfs[0].name
    return [
        {
            "name": source_name,
            "markdown": result.markdown,
            "warnings": list(getattr(result, "warnings", []) or []),
        }
    ]


def fetch_shot_payload(base: str, client: httpx.Client) -> dict:
    response = client.get(f"{base}/shot")
    try:
        body = response.json()
    except ValueError as exc:
        raise DashboardRemoteError("сервис снимка вернул не JSON", "bad_shot") from exc
    if not isinstance(body, dict):
        raise DashboardRemoteError("сервис снимка вернул не объект", "bad_shot")
    return body


def fetch_export(base: str, name: str, client: httpx.Client) -> bytes | None:
    safe = _safe_name(name)
    if not safe:
        return None
    response = client.get(f"{base}/exports/{quote(safe)}")
    if response.status_code != 200 or not response.content:
        return None
    return bytes(response.content)
