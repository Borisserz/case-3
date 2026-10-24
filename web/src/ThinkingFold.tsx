/** Collapsible step timeline — Julius “Running steps” DNA, Liber copy. */

import { useEffect, useState } from "react";
import type { ThinkingLine } from "./pipelinePhrases";

type Props = {
  lines: ThinkingLine[];
  /** While true — prefer expanded; when false — start collapsed. */
  live?: boolean;
  /** Override live title (e.g. deck build). */
  liveLabel?: string;
  elapsedSec?: number;
  className?: string;
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
}: Props) {
  const [open, setOpen] = useState(live);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    // Auto-open while live; auto-collapse when answer arrives
    setOpen(live);
  }, [live]);

  // New phrases while live → keep fold open (user may have collapsed mid-run)
  useEffect(() => {
    if (live && lines.length) setOpen(true);
  }, [live, lines.length]);

  useEffect(() => {
    if (!live) return;
    setTick(0);
    const t = window.setInterval(() => setTick((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [live]);

  if (!lines.length) return null;

  const n = lines.length;
  // Live: prefer local 1s tick — parent elapsedSec only updates on stage churn.
  const shownSec = live
    ? tick
    : typeof elapsedSec === "number" && elapsedSec >= 0
      ? elapsedSec
      : undefined;
  const sec =
    typeof shownSec === "number" ? ` · ${shownSec} сек` : "";
  const title = live ? liveLabel || "Выполняется" : "Шаги";

  return (
    <div
      className={`thinking-fold${open ? " is-open" : ""}${live ? " is-live" : ""}${className ? ` ${className}` : ""}`}
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

      {open ? (
        <ol className="thinking-fold-list">
          {lines.map((line, i) => {
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
                    <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
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
