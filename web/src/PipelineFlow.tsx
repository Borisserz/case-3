/** Liber atelier — soft pipeline nodes while the agent runs. */

import { motion, useReducedMotion } from "framer-motion";

export type FlowStage =
  | "queued"
  | "llm"
  | "images"
  | "charts"
  | "inject"
  | "latex"
  | "docx"
  | "ok"
  | "error"
  | string;

type NodeDef = {
  id: string;
  label: string;
  /** Pipeline stages that light this node. */
  stages: string[];
};

const REPORT_NODES: NodeDef[] = [
  { id: "desk", label: "Стол", stages: ["queued"] },
  { id: "think", label: "Текст", stages: ["llm"] },
  { id: "viz", label: "Фигуры", stages: ["images", "charts"] },
  { id: "bind", label: "Вёрстка", stages: ["inject"] },
  { id: "print", label: "Печать", stages: ["latex", "docx", "summary"] },
];

/** No Печать — diagram finishes on Схема (Mermaid only). */
const DIAGRAM_NODES: NodeDef[] = [
  { id: "desk", label: "Стол", stages: ["queued"] },
  { id: "think", label: "Текст", stages: ["llm"] },
  {
    id: "schema",
    label: "Схема",
    stages: ["inject", "images", "charts", "summary", "latex", "docx"],
  },
];

function activeIndex(nodes: NodeDef[], stage?: string | null): number {
  if (!stage || stage === "queued") return 0;
  if (stage === "ok") return nodes.length; // all complete
  if (stage === "error") return -1;
  const i = nodes.findIndex((n) => n.stages.includes(stage));
  return i >= 0 ? i : 0;
}

type Props = {
  stage?: string | null;
  label?: string;
  detail?: string | null;
  /** Liber mode — diagram uses a short track without Печать. */
  mode?: "report" | "diagram" | "presentation" | string | null;
};

export function PipelineFlow({
  stage = "queued",
  label,
  detail,
  mode = "report",
}: Props) {
  const reduce = useReducedMotion();
  const nodes = mode === "diagram" ? DIAGRAM_NODES : REPORT_NODES;
  const idx = activeIndex(nodes, stage);
  const failed = stage === "error";
  const done = stage === "ok";

  return (
    <div
      className={`pipeline-flow${failed ? " is-error" : ""}${done ? " is-done" : ""}`}
      role="status"
      aria-live="polite"
      aria-label={
        label || (mode === "diagram" ? "Сборка схемы" : "Сборка отчёта")
      }
    >
      <div className="pipeline-flow-track" aria-hidden>
        {nodes.map((node, i) => {
          const complete = done || (idx > i && idx !== -1);
          const active = !done && !failed && idx === i;
          const upcoming = !complete && !active && !failed;

          return (
            <div key={node.id} className="pipeline-flow-unit">
              {i > 0 && (
                <div
                  className={`pipeline-flow-edge${complete ? " is-lit" : ""}${active ? " is-flowing" : ""}`}
                >
                  <span className="pipeline-flow-edge-fill" />
                  {!reduce && active && (
                    <span className="pipeline-flow-sheen" />
                  )}
                </div>
              )}
              <div
                className={`pipeline-flow-node${complete ? " is-complete" : ""}${active ? " is-active" : ""}${upcoming ? " is-upcoming" : ""}${failed && i === Math.max(idx, 0) ? " is-failed" : ""}`}
              >
                <span className="pipeline-flow-ring">
                  {active && !reduce && (
                    <motion.span
                      className="pipeline-flow-pulse"
                      initial={false}
                      animate={{ scale: [1, 1.35], opacity: [0.35, 0] }}
                      transition={{
                        duration: 2.4,
                        ease: [0.33, 0, 0.2, 1],
                        repeat: Infinity,
                        repeatType: "loop",
                      }}
                    />
                  )}
                  <motion.span
                    className="pipeline-flow-dot"
                    layout
                    transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                  >
                    {complete ? (
                      <motion.svg
                        viewBox="0 0 16 16"
                        width="12"
                        height="12"
                        aria-hidden
                        initial={reduce ? false : { opacity: 0, scale: 0.7 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                      >
                        <path
                          d="M3.5 8.2 L6.5 11.2 L12.5 4.8"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </motion.svg>
                    ) : (
                      <span className="pipeline-flow-core" />
                    )}
                  </motion.span>
                </span>
                <span className="pipeline-flow-caption">{node.label}</span>
              </div>
            </div>
          );
        })}
      </div>

      <p className="pipeline-flow-label">
        {failed ? "Сбой на столе" : label || "Набираю отчёт…"}
        {detail && !failed ? (
          <span className="pipeline-flow-detail"> · {detail}</span>
        ) : null}
      </p>
    </div>
  );
}
