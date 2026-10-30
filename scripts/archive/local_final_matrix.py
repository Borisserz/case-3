#!/usr/bin/env python3
"""Local Liber final matrix: report + diagram + presentation via /api/run.

Usage (repo root, API on :8000):
  PYTHONPATH=src python3 scripts/archive/local_final_matrix.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]

SOURCE_A = """Liber Atelier — квартальный обзор ops SaaS «Северная логистика», Q3 2026.
Офис: Минск, ул. Интернациональная 25; склад: Брест, логистический хаб «Буг».
Продукт: TMS + last-mile трекинг для ритейла.

KPI Q3 2026 (абсолют):
MRR: июл 412 тыс. BYN, авг 428, сен 451.
Churn: июл 3.1%, авг 2.8%, сен 2.4%.
NPS: июл 41, авг 44, сен 48.
SLA on-time: июл 93.2%, авг 94.1%, сен 95.0%.
Тикеты поддержки: июл 1280, авг 1190, сен 1050.

Выручка по каналам Q3, тыс. BYN:
Direct 380 | Partner 210 | Marketplace 145 | Enterprise 290.

Доля сегментов клиентов Q3, %:
Retail 42 | Food 28 | Pharma 18 | Other 12.

Топ-5 городов по объёму доставок Q3, тыс. заказов:
Минск 86 | Брест 41 | Гродно 33 | Витебск 29 | Гомель 27.

Процесс инцидента: Detect → Triage → Fix → Verify → Postmortem.
Роли: Dispatcher, Driver, Support L1, Ops Lead, Client CSM.
Сцены для иллюстраций: ночной склад в Бресте; диспетчерская с экранами трекинга в Минске.
"""

INTENT_A = """Собери полный отчёт по Source, палитра atelier, без выдуманных цифр.
Обязательно: 1 таблица KPI/каналов; 2 разных Chart.js (line по MRR или SLA + donut по сегментам);
2 фото (склад Брест + диспетчерская Минск); 1–2 Mermaid (flowchart инцидента + sequence ролей).
Заголовок: «Северная логистика — Q3 2026». Текст на русском, цифры только из Source.
"""

SOURCE_B = """Сервис планирования спринтов «Agile Retro Hub».
Акторы: Product Owner, Scrum Master, Dev Team, Stakeholder, Liber Bot.
Спринты: Planning → Daily → Review → Retro → Backlog Grooming.
Ретро доска: Start / Stop / Continue / Action Items.
Поток бага: Open → Triage → In Progress → Code Review → QA → Done;
ветка Blocked → Unblock → In Progress.
Интеграции: GitHub (PR), Telegram (дайджест), S3 (артефакты PDF).
SLA: Critical ≤4ч, High ≤1д, Medium ≤3д.
Метрики спринта: velocity 34 / 32 / 36 SP; escaped defects 2 / 1 / 0.
"""

INTENT_B = """Режим СХЕМА: только Mermaid, без таблиц KPI и без Chart.js/фото в PDF.
Сделай 2–3 схемы: (1) flowchart жизненного цикла бага с Blocked;
(2) sequence: PO → Scrum Master → Dev → Liber Bot → Stakeholder на Review;
(3 опционально) mindmap или stateDiagram доски Retro.
Короткий stub: заголовок «Agile Retro Hub — процессы» + 1–2 абзаца.
Подписи и числа только из Source.
"""

SOURCE_C = """Кампания запуска Liber Atelier для B2B, сентябрь–октябрь 2026.
Города пилота: Минск, Алматы, Ереван.
Оффер: Source→Intent→PDF/DOCX + Chart.js + фото за один прогон.

Воронка (лиды → SQL → win), шт.:
Минск: 120 → 48 → 11
Алматы: 90 → 31 → 7
Ереван: 70 → 22 → 5

CAC, USD: Минск 180, Алматы 210, Ереван 160.
LTV, USD: Минск 2400, Алматы 1900, Ереван 2100.
Недельные демо (шт.): W36 8, W37 11, W38 14, W39 16, W40 19.
NPS пилотных CSM: 52 (Минск), 47 (Алматы), 55 (Ереван).

Слайдовая история: проблема ручных отчётов → пайплайн Liber → цифры пилота → next steps.
Сцены: офис демо в Минске; команда за большим экраном с отчётом.
Процесс продажи: Lead → Demo → Pilot → Contract → Onboarding.
"""

INTENT_C = """Собери презентацию (не PDF-отчёт) по Source, pack atelier, без выдуманных цифр.
Нужны: KPI-слайды; 1–2 графика; таблица воронки по городам; 1–2 фото;
Takeaways короткие. Заголовок дека: «Liber Atelier — пилот B2B Q4».
"""


def _multipart(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = "----case3matrix7f3a"
    parts: list[bytes] = []
    for k, v in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
                f"{v}\r\n"
            ).encode("utf-8")
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def post_run(fields: dict[str, str]) -> dict:
    body, ctype = _multipart(fields)
    req = urllib.request.Request(
        f"{API}/api/run",
        data=body,
        headers={"Content-Type": ctype},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(path: str, timeout: float = 30) -> dict:
    req = urllib.request.Request(f"{API}{path}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_run(
    run_id: str, *, timeout_s: float = 900, wait_slides: bool = False
) -> dict:
    t0 = time.time()
    last: dict = {}
    while time.time() - t0 < timeout_s:
        try:
            last = get_json(f"/api/runs/{run_id}/status")
        except urllib.error.HTTPError as exc:
            print(f"  status HTTP {exc.code}")
            time.sleep(2)
            continue
        st = str(last.get("status") or "")
        stage = last.get("stage")
        slides = str(last.get("slides_status") or "idle")
        print(f"  [{int(time.time()-t0):4d}s] status={st} stage={stage} slides={slides}")
        if st in {"error", "cancelled"}:
            return last
        if st == "ok":
            if not wait_slides:
                return last
            if slides in {"ok", "error"}:
                return last
            # idle/running/queued — wait for auto-kick + finish
        time.sleep(3)
    raise TimeoutError(f"run {run_id} timed out: {last}")


def out_dir(run_id: str) -> Path:
    return ROOT / "runs" / "out" / run_id


def check_report(run_id: str, status: dict) -> list[str]:
    errs: list[str] = []
    d = out_dir(run_id)
    if status.get("status") != "ok":
        errs.append(f"status={status.get('status')} err={status.get('error')}")
    pdfs = list(d.glob("*.pdf"))
    docxs = list(d.glob("*.docx"))
    figs = list((d / "figures").glob("*.png")) if (d / "figures").is_dir() else []
    if not pdfs:
        errs.append("no PDF")
    if not docxs:
        errs.append("no DOCX")
    if len(figs) < 1:
        errs.append(f"few figures png={len(figs)}")
    dumps = d / "prompts_used"
    work_dumps = ROOT / "runs" / "work" / run_id / "prompts_used"
    if not (dumps / "system.md").is_file() and not (work_dumps / "system.md").is_file():
        errs.append("no prompts_used/system.md (CASE3_DUMP_PROMPTS?)")
    return errs


def check_diagram(run_id: str, status: dict) -> list[str]:
    errs: list[str] = []
    if status.get("status") != "ok":
        errs.append(f"status={status.get('status')} err={status.get('error')}")
    d = out_dir(run_id)
    fj = d / "figures.json"
    if not fj.is_file():
        errs.append("no figures.json")
        return errs
    data = json.loads(fj.read_text(encoding="utf-8"))
    dias = data.get("diagrams") or []
    if len(dias) < 1:
        errs.append(f"diagrams={len(dias)}")
    return errs


def check_presentation(run_id: str, status: dict) -> list[str]:
    errs: list[str] = []
    if status.get("status") != "ok":
        errs.append(f"status={status.get('status')} err={status.get('error')}")
    slides = str(status.get("slides_status") or "")
    if slides != "ok":
        errs.append(
            f"slides_status={slides} slides_error={status.get('slides_error')}"
        )
    d = out_dir(run_id)
    pptx = list(d.glob("*.pptx"))
    if not pptx:
        errs.append("no PPTX")
    deck_pdf = list(d.glob("*deck*.pdf")) + [
        p for p in d.glob("*.pdf") if "deck" in p.name.lower() or "twin" in p.name.lower()
    ]
    if not deck_pdf:
        print("  warn: no deck PDF twin found")
    return errs


def run_case(
    name: str,
    fields: dict[str, str],
    checker,
    *,
    wait_slides: bool = False,
) -> bool:
    print(f"\n=== {name} ===")
    try:
        started = post_run(fields)
    except Exception as exc:
        print(f"FAIL start: {exc}")
        return False
    run_id = started.get("run_id")
    print(f"run_id={run_id}")
    if not run_id:
        print("FAIL no run_id", started)
        return False
    try:
        status = wait_run(run_id, wait_slides=wait_slides)
    except Exception as exc:
        print(f"FAIL wait: {exc}")
        return False
    errs = checker(run_id, status)
    if errs:
        print("FAIL checks:", "; ".join(errs))
        meta = out_dir(run_id) / "meta.json"
        if meta.is_file():
            print("meta:", meta.read_text(encoding="utf-8")[:800])
        return False
    print(f"OK {name} → {run_id}")
    print(
        "artifacts:",
        sorted(p.name for p in out_dir(run_id).iterdir() if p.is_file())[:20],
    )
    return True


def main() -> int:
    health = get_json("/api/health")
    need = ["ok", "docker_ok", "vision_ok", "playwright_ok"]
    bad = [k for k in need if not health.get(k)]
    if bad:
        print("health bad:", bad, health)
        return 2
    print("health OK image=", health.get("image_api_ok"), "soffice=", health.get("soffice_ok"))

    ok = True
    ok &= run_case(
        "A_report",
        {
            "source_text": SOURCE_A,
            "intent": INTENT_A,
            "output_mode": "report",
            "formats": "both",
            "max_charts": "2",
            "max_images": "2",
            "max_diagrams": "2",
            "chart_palette": "atelier",
            "doc_title": "Северная логистика — Q3 2026",
        },
        check_report,
    )
    ok &= run_case(
        "B_diagram",
        {
            "source_text": SOURCE_B,
            "intent": INTENT_B,
            "output_mode": "diagram",
            "formats": "none",
            "max_diagrams": "3",
            "forbid_charts": "true",
            "forbid_images": "true",
            "chart_palette": "atelier",
        },
        check_diagram,
    )
    ok &= run_case(
        "C_presentation",
        {
            "source_text": SOURCE_C,
            "intent": INTENT_C,
            "output_mode": "presentation",
            "formats": "none",
            "max_charts": "2",
            "max_images": "2",
            "max_diagrams": "0",
            "chart_palette": "atelier",
            "deck_pack": "atelier",
            "doc_title": "Liber Atelier — пилот B2B Q4",
        },
        check_presentation,
        wait_slides=True,
    )
    print("\n=== RESULT", "PASS" if ok else "FAIL", "===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
