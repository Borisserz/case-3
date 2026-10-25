/** Collapsible craft checklist — Julius “Running steps” DNA, Liber copy. */

import { useEffect, useState } from "react";
import {
  craftProgress,
  formatMmSs,
  type CraftStepState,
} from "./domain/craftSteps";
import type { ThinkingLine, ThinkingMode } from "./domain/pipelinePhrases";

type Props = {
  lines: ThinkingLine[];
  /** While true — prefer expanded; when false — start collapsed. */
  live?: boolean;
  /** Override live title (e.g. deck build). */
  liveLabel?: string;
  elapsedSec?: number;
  className?: string;
  /** Current pipeline / slides stage for craft checklist. */
  stage?: string | null;
  thinkingMode?: ThinkingMode;
  /** Artifact ready chips (PDF / PNG / PPTX) before run ends. */
  artifactChips?: string[];
  reduceMotion?: boolean | null;
};

function stepWord(n: number): string {
  return n === 1 ? "шаг" : n < 5 ? "шага" : "шагов";
}

export function ThinkingFold({
  lines,
  live = false,
  liveLabel,
  elapsedSec,
  className = "",
  stage,
  thinkingMode = "report",
  artifactChips = [],
  reduceMotion = false,
}: Props) {
  const [open, setOpen] = useState(live);
  const [tick, setTick] = useState(0);

  const craft: CraftStepState[] = craftProgress(stage, thinkingMode, {
    live,
  });
  const activeCraft = craft.find((c) => c.state === "active");
  const useCraft = craft.length > 0 && (live || Boolean(stage));

  useEffect(() => {
    setOpen(live);
  }, [live]);

  useEffect(() => {
    if (live && (lines.length || activeCraft)) setOpen(true);
  }, [live, lines.length, activeCraft?.id]);

  useEffect(() => {
    if (!live) return;
    setTick(0);
    const t = window.setInterval(() => setTick((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [live]);

  if (!lines.length && !useCraft) return null;

  const n = useCraft ? craft.length : lines.length;
  const shownSec = live
    ? tick
    : typeof elapsedSec === "number" && elapsedSec >= 0
      ? elapsedSec
      : undefined;
  const sec =
    typeof shownSec === "number"
      ? live
        ? ` · ${formatMmSs(shownSec)}`
        : ` · ${shownSec} сек`
      : "";
  const title = live
    ? liveLabel || activeCraft?.label || "Выполняется"
    : "Шаги";

  return (
    <div
      className={`thinking-fold${open ? " is-open" : ""}${live ? " is-live" : ""}${
        reduceMotion ? " is-reduced" : ""
      }${className ? ` ${className}` : ""}`}
    >
      <button
        type="button"
        className="thinking-fold-summary"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="thinking-fold-chevron" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="thinking-fold-title">{title}</span>
        <span className="thinking-fold-meta">
          {n} {stepWord(n)}
          {sec}
        </span>
        {live ? (
          <span className="thinking-fold-live" aria-hidden>
            <svg
              className="thinking-fold-live-chevron"
              width="10"
              height="10"
              viewBox="0 0 12 12"
              fill="none"
            >
              <path
                d="M3 4.5 6 7.5 9 4.5"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        ) : null}
      </button>

      {artifactChips.length > 0 ? (
        <div className="thinking-fold-chips" aria-live="polite">
          {artifactChips.map((label) => (
            <span key={label} className="thinking-fold-chip">
              {label}
            </span>
          ))}
        </div>
      ) : null}

      {open ? (
        <ol className="thinking-fold-list">
          {useCraft
            ? craft.map((step) => (
                <li
                  key={step.id}
                  className={`thinking-fold-line is-${step.state}`}
                >
                  <span className="thinking-fold-mark" aria-hidden>
                    {step.state === "active" ? (
                      <span className="thinking-fold-spin" />
                    ) : step.state === "done" ? (
                      <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                        <path
                          d="M2.5 6.2 4.8 8.5 9.5 3.5"
                          stroke="currentColor"
                          strokeWidth="1.6"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    ) : (
                      <span className="thinking-fold-dot" />
                    )}
                  </span>
                  <span className="thinking-fold-text">
                    {step.label}
                    {step.state === "active" && typeof shownSec === "number"
                      ? ` · ${formatMmSs(shownSec)}`
                      : ""}
                  </span>
                </li>
              ))
            : lines.map((line, i) => {
                const isLast = i === lines.length - 1;
                const active = live && isLast;
                return (
                  <li
                    key={line.id}
                    className={`thinking-fold-line${active ? " is-active" : " is-done"}`}
                  >
                    <span className="thinking-fold-mark" aria-hidden>
                      {active ? (
                        <span className="thinking-fold-spin" />
                      ) : (
                        <svg
                          width="11"
                          height="11"
                          viewBox="0 0 12 12"
                          fill="none"
                        >
                          <path
                            d="M2.5 6.2 4.8 8.5 9.5 3.5"
                            stroke="currentColor"
                            strokeWidth="1.6"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </span>
                    <span className="thinking-fold-text">{line.text}</span>
                  </li>
                );
              })}
        </ol>
      ) : null}
    </div>
  );
}
