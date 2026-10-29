#!/usr/bin/env python3
"""Build 10 curated Liber decks (skip LLM) → PNG + PPTX + deck PDF.

Usage:
  PYTHONPATH=src python3 scripts/archive/run_slides_matrix10.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from case3.slides_export import build_deck_pdf, build_image_pptx  # noqa: E402
from case3.slides_ir import parse_deck_ir  # noqa: E402
from case3.slides_render import render_deck_pngs  # noqa: E402

OUT = ROOT / "runs" / "slides_matrix10"
CHART_SRC = ROOT / "runs" / "mac_live_qa" / "figures" / "cht_01.png"
if not CHART_SRC.is_file():
    CHART_SRC = ROOT / "runs" / "full_structure_demo" / "figures" / "cht_bar.png"
CHART_SRC2 = ROOT / "runs" / "mac_live_qa" / "figures" / "cht_02.png"
if not CHART_SRC2.is_file():
    CHART_SRC2 = ROOT / "runs" / "full_structure_demo" / "figures" / "cht_donut.png"


def _case(
    case_id: str,
    *,
    title: str,
    source: str,
    palette: str,
    slides: list[dict],
) -> dict:
    return {
        "id": case_id,
        "title": title,
        "source": source,
        "palette": palette,
        "slides": slides,
    }


CASES: list[dict] = [
    _case(
        "01_retail_q",
        title="Ритейл Q3",
        palette="atelier",
        source=(
            "Сеть Liber Market. Выручка Q3 4,8 млрд руб. "
            "Доля e-com 27%. NPS 62. Маржа 18,4%. "
            "Топ-регион: Москва 1,1 млрд. Открыто 12 магазинов."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Liber Market · Q3",
                "subtitle": "Выручка, e-com и маржа — факты из отчёта",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Ключевые цифры",
                "kpis": [
                    {"label": "Выручка Q3", "value": "4,8 млрд", "hint": "руб."},
                    {"label": "E-com", "value": "27%", "hint": "доля"},
                    {"label": "NPS", "value": "62"},
                    {"label": "Маржа", "value": "18,4%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "title": "Продажи и регионы",
                "chart_id": "cht_01",
                "caption": "Выручка Q3 4,8 млрд · Москва 1,1 млрд",
            },
            {
                "id": "s04",
                "layout": "bullets",
                "title": "Что сделали",
                "bullets": [
                    "Открыто 12 магазинов",
                    "Доля e-com выросла до 27%",
                    "NPS удерживается на 62",
                ],
            },
            {
                "id": "s05",
                "layout": "closing",
                "title": "Фокус Q4",
                "bullets": ["Усилить e-com", "Маржа не ниже 18,4%"],
            },
        ],
    ),
    _case(
        "02_saas_mrr",
        title="SaaS MRR",
        palette="ocean",
        source=(
            "Продукт Atelier Cloud. MRR 820 тыс. USD. "
            "Net revenue retention 118%. Churn 2,1%. "
            "Клиентов 340. ARPU 2410 USD. Pipeline 1,4 млн."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Atelier Cloud",
                "subtitle": "MRR и удержание — октябрь",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Снимок",
                "kpis": [
                    {"label": "MRR", "value": "820 тыс.", "hint": "USD"},
                    {"label": "NRR", "value": "118%"},
                    {"label": "Churn", "value": "2,1%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_split",
                "title": "Рост базы",
                "chart_id": "cht_01",
                "body": "340 клиентов, ARPU 2410 USD.",
                "bullets": ["Pipeline 1,4 млн", "Churn 2,1% — в норме"],
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Следующий шаг",
                "bullets": ["Закрыть pipeline 1,4 млн", "Удержать NRR 118%"],
            },
        ],
    ),
    _case(
        "03_ops_sla",
        title="Ops SLA",
        palette="mono",
        source=(
            "Платформа Liber Desk. SLA 99,95%. Инцидентов P1: 2. "
            "MTTR 41 мин. Availability 99,97%. Тикетов 1840. "
            "CSAT 4,6 из 5."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Надёжность · Liber Desk",
                "subtitle": "SLA и инциденты за месяц",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Сервис",
                "kpis": [
                    {"label": "Availability", "value": "99,97%"},
                    {"label": "MTTR", "value": "41 мин"},
                    {"label": "P1", "value": "2"},
                    {"label": "CSAT", "value": "4,6"},
                ],
            },
            {
                "id": "s03",
                "layout": "bullets",
                "title": "Контекст",
                "bullets": [
                    "SLA цели 99,95% — выполнено",
                    "Тикетов 1840 за период",
                    "Два P1 закрыты в MTTR 41 мин",
                ],
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Держим планку",
                "bullets": ["Не выше 2 P1", "MTTR ≤ 41 мин"],
            },
        ],
    ),
    _case(
        "04_bank_risk",
        title="Риск-портфель",
        palette="editorial",
        source=(
            "Портфель кредитов. NPL 3,2%. Coverage 98%. "
            "RWA 210 млрд. CET1 14,1%. Провизии 6,4 млрд. "
            "Рост портфеля 7% YoY."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Кредитный риск",
                "subtitle": "NPL, покрытие и капитал",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Метрики",
                "kpis": [
                    {"label": "NPL", "value": "3,2%"},
                    {"label": "Coverage", "value": "98%"},
                    {"label": "CET1", "value": "14,1%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_split",
                "title": "Портфель",
                "chart_id": "cht_02",
                "body": "RWA 210 млрд, провизии 6,4 млрд.",
                "bullets": ["Рост портфеля 7% YoY", "Coverage 98%"],
                "caption": "Источник — внутренняя отчётность",
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Контроль",
                "bullets": ["NPL не выше 3,2%", "CET1 выше 14%"],
            },
        ],
    ),
    _case(
        "05_hr_hire",
        title="Найм",
        palette="sunset",
        source=(
            "Найм Q3. Офферов 86. Acceptance 71%. "
            "Time-to-hire 28 дней. Стоимость найма 410 тыс. руб. "
            "Текучесть 9%. Headcount 612."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Найм · Q3",
                "subtitle": "Воронка и стоимость",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Воронка",
                "kpis": [
                    {"label": "Офферы", "value": "86"},
                    {"label": "Accept", "value": "71%"},
                    {"label": "TTH", "value": "28 дн."},
                ],
            },
            {
                "id": "s03",
                "layout": "bullets",
                "title": "Люди",
                "bullets": [
                    "Headcount 612",
                    "Текучесть 9%",
                    "Стоимость найма 410 тыс. руб.",
                ],
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Цель Q4",
                "bullets": ["TTH ≤ 28 дней", "Accept ≥ 71%"],
            },
        ],
    ),
    _case(
        "06_mkt_cac",
        title="Маркетинг",
        palette="ocean",
        source=(
            "Performance. CAC 3400 руб. LTV 28 тыс. "
            "ROAS 3,6. Бюджет 19 млн. Лидов 5200. "
            "Конверсия 4,2%."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Performance · месяц",
                "subtitle": "CAC, LTV и отдача бюджета",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Эффективность",
                "kpis": [
                    {"label": "CAC", "value": "3400", "hint": "руб."},
                    {"label": "LTV", "value": "28 тыс."},
                    {"label": "ROAS", "value": "3,6"},
                    {"label": "CR", "value": "4,2%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "title": "Лиды и бюджет",
                "chart_id": "cht_01",
                "caption": "Бюджет 19 млн · лидов 5200",
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Держим ROAS",
                "bullets": ["ROAS ≥ 3,6", "CAC около 3400 руб."],
            },
        ],
    ),
    _case(
        "07_factory",
        title="Производство",
        palette="atelier",
        source=(
            "Завод Север. OEE 81%. Брак 1,4%. "
            "Выпуск 92 тыс. ед. Простой 6,2 ч. "
            "Энергия −8% YoY. Смена A: 310 человек."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Завод Север",
                "subtitle": "OEE, брак и выпуск",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Смена",
                "kpis": [
                    {"label": "OEE", "value": "81%"},
                    {"label": "Брак", "value": "1,4%"},
                    {"label": "Выпуск", "value": "92 тыс."},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_split",
                "title": "Потери",
                "chart_id": "cht_02",
                "body": "Простой 6,2 ч. Энергия −8% YoY.",
                "bullets": ["Смена A: 310 человек", "Цель OEE 81%+"],
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "План",
                "bullets": ["Брак ≤ 1,4%", "Сократить простой"],
            },
        ],
    ),
    _case(
        "08_edu_nps",
        title="Образование",
        palette="editorial",
        source=(
            "Онлайн-курс Liber Learn. Завершили 1840. "
            "NPS 71. Completion 64%. Средний балл 4,5. "
            "Выручка 12,6 млн. Возвраты 2,8%."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Liber Learn",
                "subtitle": "Завершения и удовлетворённость",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Курс",
                "kpis": [
                    {"label": "Завершили", "value": "1840"},
                    {"label": "NPS", "value": "71"},
                    {"label": "Completion", "value": "64%"},
                ],
            },
            {
                "id": "s03",
                "layout": "bullets",
                "title": "Деньги и качество",
                "bullets": [
                    "Выручка 12,6 млн",
                    "Средний балл 4,5",
                    "Возвраты 2,8%",
                ],
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Усилить completion",
                "bullets": ["Цель completion > 64%", "NPS не ниже 71"],
            },
        ],
    ),
    _case(
        "09_logistics",
        title="Логистика",
        palette="mono",
        source=(
            "Склад Юг. OTIF 94%. Стоимость доставки 118 руб. "
            "Скорость 1,8 дня. Остаток 42 тыс. SKU. "
            "Повреждения 0,3%. Рейсы 960."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Склад Юг",
                "subtitle": "OTIF и стоимость мили",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "Сервис",
                "kpis": [
                    {"label": "OTIF", "value": "94%"},
                    {"label": "Доставка", "value": "118 руб."},
                    {"label": "Скорость", "value": "1,8 дн."},
                    {"label": "Поврежд.", "value": "0,3%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "title": "Потоки",
                "chart_id": "cht_01",
                "caption": "Рейсы 960 · остаток 42 тыс. SKU",
            },
            {
                "id": "s04",
                "layout": "closing",
                "title": "Держим OTIF",
                "bullets": ["OTIF ≥ 94%", "Повреждения ≤ 0,3%"],
            },
        ],
    ),
    _case(
        "10_board",
        title="Board summary",
        palette="atelier",
        source=(
            "Группа Liber. Выручка 62 млрд. EBITDA 11,4 млрд. "
            "Маржа EBITDA 18%. FCF 7,1 млрд. Net debt / EBITDA 1,2. "
            "Дивиденд 2,4 млрд. Capex 5,0 млрд."
        ),
        slides=[
            {
                "id": "s01",
                "layout": "title",
                "title": "Группа Liber",
                "subtitle": "Совет директоров — краткий срез",
            },
            {
                "id": "s02",
                "layout": "kpi_row",
                "title": "P&L",
                "kpis": [
                    {"label": "Выручка", "value": "62 млрд"},
                    {"label": "EBITDA", "value": "11,4 млрд"},
                    {"label": "Маржа", "value": "18%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_split",
                "title": "Баланс и кэш",
                "chart_id": "cht_02",
                "body": "FCF 7,1 млрд. Net debt / EBITDA 1,2.",
                "bullets": ["Capex 5,0 млрд", "Дивиденд 2,4 млрд"],
            },
            {
                "id": "s04",
                "layout": "bullets",
                "title": "Послание совету",
                "bullets": [
                    "Маржа EBITDA 18% устойчива",
                    "Долг комфортный: 1,2× EBITDA",
                    "FCF покрывает дивиденд 2,4 млрд",
                ],
            },
            {
                "id": "s05",
                "layout": "closing",
                "title": "Решения",
                "bullets": ["Утвердить дивиденд", "Capex 5,0 млрд без роста"],
            },
        ],
    ),
]


def main() -> int:
    # repair run_one if typo slipped — rewrite cleanly inline
    results = []
    OUT.mkdir(parents=True, exist_ok=True)
    for i, case in enumerate(CASES, 1):
        print(f"[{i}/10] {case['id']} …", flush=True)
        cid = case["id"]
        case_dir = OUT / cid
        if case_dir.exists():
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True)
        (case_dir / "source.txt").write_text(case["source"], encoding="utf-8")
        raw = {
            "version": 1,
            "aspect": "16:9",
            "palette": case["palette"],
            "language": "ru",
            "slides": case["slides"],
        }
        deck = parse_deck_ir(raw, source=case["source"])
        (case_dir / "deck.json").write_text(
            json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        chart_map: dict[str, Path] = {}
        figs = case_dir / "figures"
        figs.mkdir()
        if CHART_SRC.is_file():
            p = figs / "cht_01.png"
            shutil.copy2(CHART_SRC, p)
            chart_map["cht_01"] = p
        if CHART_SRC2.is_file():
            p = figs / "cht_02.png"
            shutil.copy2(CHART_SRC2, p)
            chart_map["cht_02"] = p
        pngs = render_deck_pngs(
            deck,
            work_root=case_dir / "work",
            out_dir=case_dir / "slides",
            chart_png_by_id=chart_map,
        )
        pptx = case_dir / f"{cid}.pptx"
        pdf = case_dir / f"{cid}_deck.pdf"
        build_image_pptx(pngs, pptx)
        build_deck_pdf(pngs, pdf)
        row = {
            "id": cid,
            "title": case["title"],
            "slides": len(pngs),
            "pptx": str(pptx.relative_to(ROOT)),
            "pdf": str(pdf.relative_to(ROOT)),
            "palette": case["palette"],
        }
        results.append(row)
        print(f"    ok · {len(pngs)} slides · {pptx.name}", flush=True)

    summary = {"cases": results, "ok": len(results)}
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
