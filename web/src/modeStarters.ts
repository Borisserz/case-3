/** Quiet empty-home starters under the sheet composer (report / diagram). */

import type { LiberWorkMode } from "./liberModes";

export type ModeStarter = {
  id: string;
  title: string;
  /** Short human line on the card. */
  blurb: string;
  /** Fills the composer on pick. */
  prompt: string;
};

export const REPORT_STARTERS: ModeStarter[] = [
  {
    id: "kpi-quarter",
    title: "Квартальный KPI",
    blurb: "Таблица KPI и один спокойный график по Source.",
    prompt:
      "Собери отчёт по Source: таблица KPI за квартал, один line-график, спокойная палитра atelier, без выдуманных цифр.",
  },
  {
    id: "budget-mix",
    title: "Бюджет и доли",
    blurb: "Доли бюджета и краткие выводы только из цифр Source.",
    prompt:
      "Отчёт по распределению бюджета из Source: краткие выводы и pie/doughnut только по числам Source.",
  },
  {
    id: "exec-brief",
    title: "Краткий бриф",
    blurb: "3–5 выводов и одна таблица — без воды.",
    prompt:
      "Короткий executive-отчёт: 3–5 выводов и одна таблица из Source, без воды.",
  },
  {
    id: "compare-periods",
    title: "Сравнение периодов",
    blurb: "Дельты между периодами и один сравнительный график.",
    prompt:
      "Сравни периоды из Source: таблица дельт и один bar/line-график, только факты Source.",
  },
];

export const DIAGRAM_STARTERS: ModeStarter[] = [
  {
    id: "process-flow",
    title: "Процесс",
    blurb: "Этапы слева направо — только Mermaid-схема.",
    prompt:
      "Нарисуй схему процесса из описания: этапы слева направо, без PDF — только Mermaid.",
  },
  {
    id: "system-arch",
    title: "Архитектура",
    blurb: "Клиент → API → данные с короткими подписями.",
    prompt:
      "Схема компонентов системы: клиент → API → данные. Только Mermaid, подписи короткие.",
  },
  {
    id: "decision-tree",
    title: "Решение",
    blurb: "Условия и ветки из текста, без лишних шагов.",
    prompt:
      "Схема принятия решения (flowchart): условия и ветки из текста, без выдуманных шагов.",
  },
  {
    id: "swimlane",
    title: "Роли и шаги",
    blurb: "Кто что делает — схема по ролям из описания.",
    prompt:
      "Схема с ролями (кто что делает) по Source или краткому описанию — только Mermaid.",
  },
];

export function startersForMode(mode: LiberWorkMode): ModeStarter[] {
  if (mode === "report") return REPORT_STARTERS;
  if (mode === "diagram") return DIAGRAM_STARTERS;
  return [];
}
