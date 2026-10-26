/** Collapsible craft checklist — Julius “Running steps” DNA, Liber copy. */

import { useEffect, useState } from "react";
import {
  craftProgress,
  effectiveCraftMode,
  formatEtaSuffix,
  formatMmSs,
  type CraftFilmFrame,
  type CraftStepId,
  type CraftStepState,
  type CraftSubstep,
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
  reduceMotion?: boolean | null;
  /** Nested chart/figure beats from SSE step events. */
  craftSubsteps?: CraftSubstep[];
  /** photos → reason when Image API skipped */
  craftSkipped?: Partial<Record<CraftStepId, string>>;
  /** SSE 2B birth film */
  craftFilm?: CraftFilmFrame[];
  onOpenFilm?: (frame: CraftFilmFrame) => void;
  /** Success recap under fold */
  craftRecap?: string | null;
  /** ETA seconds for current stage (server rolling avg). */
  etaSec?: number | null;
  /** Cancel: freeze checklist mid-step */
  craftFrozen?: boolean;
  /** Error recovery line under list */
  errorHint?: string | null;
};

function stepWord(n: number): string {
  return n === 1 ? "шаг" : n < 5 ? "шага" : "шагов";
}

function markFor(
  state: CraftStepState["state"] | CraftSubstep["status"],
  opts?: { animate?: boolean },
) {
  const animate = opts?.animate !== false;
  if (state === "active")
    return animate ? (
      <span className="thinking-fold-spin" />
    ) : (
      <span className="thinking-fold-pause" aria-hidden />
    );
  if (state === "done")
    return (
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
        <path
          d="M2.5 6.2 4.8 8.5 9.5 3.5"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  if (state === "skipped")
    return <span className="thinking-fold-skip-mark">—</span>;
  return <span className="thinking-fold-dot" />;
}

export function ThinkingFold({
  lines,
  live = false,
  liveLabel,
  elapsedSec,
  className = "",
  stage,
  thinkingMode = "report",
  reduceMotion = false,
  craftSubsteps = [],
  craftSkipped,
  craftFilm = [],
  onOpenFilm,
  craftRecap = null,
  etaSec = null,
  craftFrozen = false,
  errorHint = null,
}: Props) {
  const [open, setOpen] = useState(live);
  const [tick, setTick] = useState(0);

  const craftMode = effectiveCraftMode(thinkingMode, stage);
  const craft: CraftStepState[] = craftProgress(stage, craftMode, {
    live: live && !craftFrozen,
    skipped: craftSkipped,
    substeps: craftSubsteps,
    frozen: craftFrozen,
  });
  const activeCraft = craft.find((c) => c.state === "active");
  const useCraft = craft.length > 0 && (live || Boolean(stage) || craftFrozen);
  const activeSub = activeCraft?.substeps?.find((s) => s.status === "active");
  const hasFilm = craftFilm.length > 0;

  useEffect(() => {
    setOpen(live);
  }, [live]);

  useEffect(() => {
    if (live && (lines.length || activeCraft || hasFilm)) setOpen(true);
  }, [live, lines.length, activeCraft?.id, hasFilm]);

  useEffect(() => {
    if (!live) return;
    setTick(0);
    const t = window.setInterval(() => setTick((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [live]);

  if (!lines.length && !useCraft && !errorHint && !hasFilm && !craftRecap)
    return null;

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
  const eta = live && !craftFrozen ? formatEtaSuffix(etaSec) : "";
  const detailBit = activeSub ? ` · ${activeSub.label}` : "";
  const title = craftFrozen
    ? "Остановлено"
    : live
      ? liveLabel ||
        `${activeCraft?.label || "Выполняется"}${detailBit}${eta}`
      : "Шаги";

  return (
    <div
      className={`thinking-fold${open ? " is-open" : ""}${live ? " is-live" : ""}${
        reduceMotion ? " is-reduced" : ""
      }${craftFrozen ? " is-frozen" : ""}${className ? ` ${className}` : ""}`}
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
          {n > 0 ? (
            <>
              {n} {stepWord(n)}
              {sec}
            </>
          ) : (
            sec.replace(/^ · /, "") || null
          )}
        </span>
        {live && !craftFrozen ? (
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

      {hasFilm ? (
        <div className="thinking-fold-film" aria-label="Кадры сборки">
          {craftFilm.map((frame) => (
            <button
              key={frame.id}
              type="button"
              className="thinking-fold-frame"
              title={frame.id}
              onClick={() => onOpenFilm?.(frame)}
            >
              <img
                src={frame.url}
                alt={frame.id}
                loading="lazy"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.visibility =
                    "hidden";
                }}
              />
            </button>
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
                    {markFor(step.state, { animate: !craftFrozen })}
                  </span>
                  <span className="thinking-fold-text">
                    {step.label}
                    {step.state === "skipped" && step.reason
                      ? ` — ${step.reason}`
                      : ""}
                    {step.state === "active" &&
                    !craftFrozen &&
                    typeof shownSec === "number"
                      ? ` · ${formatMmSs(shownSec)}`
                      : ""}
                  </span>
                  {step.substeps && step.substeps.length > 0 ? (
                    <ul className="thinking-fold-sublist">
                      {step.substeps.map((sub) => (
                        <li
                          key={sub.id}
                          className={`thinking-fold-sub is-${sub.status}`}
                        >
                          <span className="thinking-fold-mark" aria-hidden>
                            {markFor(sub.status, { animate: !craftFrozen })}
                          </span>
                          <span className="thinking-fold-text">
                            {sub.label}
                            {sub.status === "skipped" && sub.reason
                              ? ` — ${sub.reason}`
                              : ""}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
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

      {craftRecap ? (
        <p className="thinking-fold-recap" role="status">
          {craftRecap}
        </p>
      ) : null}

      {errorHint ? (
        <p className="thinking-fold-hint" role="status">
          {errorHint}
        </p>
      ) : null}
    </div>
  );
}
