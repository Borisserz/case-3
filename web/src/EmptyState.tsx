/** Liber empty hero — modes live in composer inner bar. */

import { motion, useReducedMotion } from "framer-motion";
import type { LiberWorkMode } from "./domain/liberModes";

type Props = {
  hasStoredReport?: boolean;
  onRestore?: () => void;
  workMode?: LiberWorkMode;
};

export function EmptyState({ workMode = null }: Props) {
  const reduce = useReducedMotion();
  const title =
    workMode === "presentation"
      ? "Какую презентацию соберём?"
      : workMode === "diagram"
        ? "Какую схему нарисовать?"
        : workMode === "report"
          ? "Какой отчёт собрать?"
          : "Чем могу помочь?";
  return (
    <motion.div
      className="empty empty-hero"
      key={`empty-${workMode || "auto"}`}
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <h2>{title}</h2>
    </motion.div>
  );
}
