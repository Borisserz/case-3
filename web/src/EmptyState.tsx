/** Liber empty hero — modes live in composer inner bar. */

import { motion, useReducedMotion } from "framer-motion";
import { IconLiberMark } from "./icons";
import { modeNudge, type LiberWorkMode } from "./liberModes";

type Props = {
  hasStoredReport: boolean;
  onRestore: () => void;
  workMode?: LiberWorkMode;
};

function restoreLabel(workMode: LiberWorkMode): string {
  if (workMode === "diagram") return "Открыть последнюю схему";
  if (workMode === "presentation") return "Открыть последнюю презентацию";
  if (workMode === "report") return "Открыть последний отчёт";
  return "Открыть последнюю работу";
}

export function EmptyState({
  hasStoredReport,
  onRestore,
  workMode = null,
}: Props) {
  const reduce = useReducedMotion();
  const title =
    workMode === "presentation"
      ? "Какую презентацию соберём?"
      : workMode === "diagram"
        ? "Какую схему нарисовать?"
        : workMode === "report"
          ? "Какой отчёт собрать?"
          : "Чем могу помочь?";
  const subtitle = modeNudge(workMode);
  return (
    <motion.div
      className="empty empty-hero"
      key={`empty-${workMode || "auto"}`}
      initial={reduce ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.45, ease: [0.22, 1, 0.36, 1] }}
    >
      <IconLiberMark size={36} />
      <h2>{title}</h2>
      <p>{subtitle}</p>
      {hasStoredReport && (
        <button type="button" className="empty-restore" onClick={onRestore}>
          {restoreLabel(workMode)}
        </button>
      )}
    </motion.div>
  );
}
