"""Read a Stimulsoft viewer service: /viewer stays open, GET /shot returns the files."""

from __future__ import annotations

import base64
import binascii
import io
import json
import os
import re
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


_ASK_BITS = (
    "дашборд",
    "фильтр",
    "стимул",
    "январ",
    "феврал",
    "март",
    "апрел",
    "мая",
    "июн",
    "июл",
    "август",
    "сентябр",
    "октябр",
    "ноябр",
    "декабр",
)


def might_ask_dashboard(text: str) -> bool:
    low = (text or "").casefold().replace("ё", "е")
    return any(re.search(rf"(?<![0-9a-zа-я]){re.escape(bit)}", low) for bit in _ASK_BITS)


def _norm(value: object) -> str:
    return str(value or "").strip().casefold().replace("ё", "е")


def _phrase_has(phrase: str, needle: object) -> bool:
    left = _norm(phrase)
    right = _norm(needle)
    if not left or not right:
        return False
    if right in left:
        return True
    digits = "".join(ch for ch in right if ch.isdigit())
    if len(digits) >= 4 and digits[-2:] in left:
        return True
    return False


def _json_object(raw: str) -> dict:
    text = (raw or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        body = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return body if isinstance(body, dict) else {}


def _choice_pairs(field: dict) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for choice in field.get("choices") or []:
        if isinstance(choice, dict):
            key = str(choice.get("key") if choice.get("key") is not None else "").strip()
            label = str(
                choice.get("value") if choice.get("value") is not None else key
            ).strip()
            pairs.append((key, label))
        elif choice is not None:
            text = str(choice).strip()
            pairs.append((text, text))
    return pairs


def _open_value(raw: object) -> object:
    """Choice keys go to /open. A plain integer stays a number; 0000000 stays text."""
    text = str(raw if raw is not None else "").strip()
    if re.fullmatch(r"-?(?:0|[1-9]\d*)", text):
        return int(text)
    return text


def filters_from_model(catalog: dict, phrase: str, raw: str) -> dict[str, object]:
    """Keep only catalog filters the sentence actually names."""
    body = _json_object(raw)
    if not body.get("pull"):
        return {}
    wanted = body.get("filters")
    if not isinstance(wanted, dict):
        return {}
    fields = [item for item in (catalog.get("filters") or []) if isinstance(item, dict)]
    by_name: dict[str, dict] = {}
    for field in fields:
        for label in (field.get("name"), field.get("alias")):
            key = _norm(label)
            if key:
                by_name[key] = field
    picked: dict[str, object] = {}
    for key, value in wanted.items():
        field = by_name.get(_norm(key))
        if field is None:
            continue
        name = str(field.get("name") or key).strip()
        pairs = _choice_pairs(field)
        if pairs:
            wanted_norm = _norm(value)
            match = next(
                (
                    pair
                    for pair in pairs
                    if wanted_norm and wanted_norm in {_norm(pair[0]), _norm(pair[1])}
                ),
                None,
            )
            if match is None:
                continue
            if not (_phrase_has(phrase, match[1]) or _phrase_has(phrase, match[0])):
                continue
            picked[name] = _open_value(match[0] if match[0] != "" else match[1])
            continue
        if _phrase_has(phrase, value):
            picked[name] = _open_value(value)
    return picked


def open_payload(filters: dict[str, object]) -> dict[str, object]:
    return {"filters": dict(filters)}


def catalog_file() -> Path:
    raw = (os.environ.get("DASHBOARD_FILTERS_FILE") or "").strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / "local" / "dashboard_filters.json"


def read_filter_catalog(path: Path | None = None) -> dict | None:
    """Full filter list dropped on the work machine. Missing file means ask /filters."""
    file = path or catalog_file()
    if not file.is_file():
        return None
    try:
        body = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardRemoteError(
            f"не читается {file.name}: нужен JSON каталога фильтров",
            "filters",
        ) from exc
    if isinstance(body, list):
        body = {"filters": body}
    if not isinstance(body, dict) or not isinstance(body.get("filters"), list):
        raise DashboardRemoteError(
            f"{file.name}: нужен объект с полем filters",
            "filters",
        )
    return body


def post_open_filters(base: str, filters: dict[str, object], client) -> None:
    response = client.post(f"{base.rstrip('/')}/open", json=open_payload(filters))
    status = int(getattr(response, "status_code", 500) or 500)
    if status >= 400:
        raise DashboardRemoteError("сервис не принял фильтры", "open")


def finish_dashboard_phrase(plan: dict, base: str, client) -> dict:
    """POST the choice keys, then the iframe loads /viewer on that same service."""
    if not plan.get("pull"):
        return plan
    filters = plan.get("filters")
    if not isinstance(filters, dict) or not filters:
        return plan
    post_open_filters(base, filters, client)
    return {**plan, "viewer": viewer_url()}


OPEN_REPLY = "Сейчас открою."


def plan_dashboard_phrase(text: str, catalog: dict, complete) -> dict:
    """Map a chat sentence onto his /open URL. No match means a normal send."""
    if not might_ask_dashboard(text):
        return {"pull": False}
    from case3.prompts import load as load_prompt

    raw = complete(
        system=load_prompt("dashboard_filters"),
        user_text=(
            text.strip()
            + "\n\nКаталог:\n"
            + json.dumps(catalog, ensure_ascii=False)
        ),
    )
    if not _json_object(str(raw or "")).get("pull"):
        return {"pull": False}
    picked = filters_from_model(catalog, text, str(raw or ""))
    if not picked:
        return {
            "pull": False,
            "asked": True,
            "reply": "В фразе нет фильтра, который есть в дашборде. Назови период как в отчёте.",
        }
    return {
        "pull": True,
        "filters": picked,
        "viewer": viewer_url(),
        "reply": OPEN_REPLY,
    }


def fetch_export(base: str, name: str, client: httpx.Client) -> bytes | None:
    safe = _safe_name(name)
    if not safe:
        return None
    response = client.get(f"{base}/exports/{quote(safe)}")
    if response.status_code != 200 or not response.content:
        return None
    return bytes(response.content)
