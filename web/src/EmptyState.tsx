/** Liber empty hero — modes live under composer. */

import { motion, useReducedMotion } from "framer-motion";
import { IconLiberMark } from "./icons";
import type { LiberWorkMode } from "./liberModes";

type Props = {
  hasStoredReport: boolean;
  onRestore: () => void;
  workMode?: LiberWorkMode;
};

export function EmptyState({
  hasStoredReport,
  onRestore,
  workMode = null,
}: Props) {
  const reduce = useReducedMotion();
  const copy =
    workMode === "presentation"
      ? { title: "Какую презентацию соберём?", body: "" }
      : workMode === "diagram"
        ? { title: "Какую схему нарисовать?", body: "" }
        : workMode === "report"
          ? { title: "Какой отчёт собрать?", body: "" }
          : { title: "Чем займёмся?", body: "" };
  return (
    <motion.div
      className="empty empty-hero"
      key={`empty-${workMode || "auto"}`}
      initial={reduce ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.45, ease: [0.22, 1, 0.36, 1] }}
    >
      <IconLiberMark size={56} />
      <h2>{copy.title}</h2>
      {copy.body ? <p>{copy.body}</p> : null}
      {hasStoredReport && (
        <button type="button" className="empty-restore" onClick={onRestore}>
          Открыть последний отчёт
        </button>
      )}
    </motion.div>
  );
}
