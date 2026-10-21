/** Mary-style empty hero — Liber copy, no mascot, ≤3 prompts. */

import { motion, useReducedMotion } from "framer-motion";
import { IconLiberMark } from "./icons";

const PROMPTS = [
  {
    label: "Отчёт с таблицей и графиками",
    text: "Оформи отчёт по этим данным: структура, таблицы где уместны числа, 1–2 графика.",
  },
  {
    label: "Только текст, без графиков",
    text: "Собери понятный русскоязычный отчёт без графиков и без фото.",
  },
  {
    label: "KPI и сравнение долей",
    text: "Выдели ключевые KPI и покажи доли/сравнение на графиках (donut или bar).",
  },
] as const;

type Props = {
  hasStoredReport: boolean;
  onRestore: () => void;
  onPrompt: (text: string) => void;
};

export function EmptyState({ hasStoredReport, onRestore, onPrompt }: Props) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className="empty empty-hero"
      key="empty"
      initial={reduce ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
    >
      <IconLiberMark size={48} />
      <h2>Я Liber — соберу отчёт из ваших данных</h2>
      <p>
        Вставьте Source или прикрепите .txt / .md. Готовый PDF откроется справа;
        Export — в один клик.
      </p>
      <ul className="empty-prompts">
        {PROMPTS.map((p) => (
          <li key={p.label}>
            <button
              type="button"
              className="empty-prompt"
              onClick={() => onPrompt(p.text)}
            >
              <span>{p.label}</span>
              <span className="empty-prompt-arrow" aria-hidden>
                →
              </span>
            </button>
          </li>
        ))}
      </ul>
      {hasStoredReport && (
        <button type="button" className="empty-restore" onClick={onRestore}>
          Открыть последний отчёт
        </button>
      )}
    </motion.div>
  );
}
