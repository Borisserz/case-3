/** Adaptive frame-paced text revealer for smooth, flicker-free SSE streaming. */

export type StreamPacerUpdateMeta = {
  draining: boolean;
};

export type StreamPacerOptions = {
  /** Base reading speed in UTF-16 chars/sec (default ~68 for calm editorial feel). */
  baseCps?: number;
  /** Skip animation and reveal immediately (e.g. prefers-reduced-motion). */
  instant?: boolean;
  onUpdate: (visibleText: string, meta?: StreamPacerUpdateMeta) => void;
  now?: () => number;
  scheduleFrame?: (cb: (ts: number) => void) => number;
  cancelFrame?: (id: number) => void;
};

export type StreamPacer = {
  pushTarget: (fullText: string) => void;
  replaceTarget: (fullText: string) => void;
  markDone: (finalText?: string) => Promise<void>;
  flush: () => void;
  stop: () => void;
  getVisible: () => string;
  isDraining: () => boolean;
};

/** Keep every character already on screen.
 * `next` may only drop leading whitespace or add unseen text.
 * A different answer does not replace the stream.
 */
function planReveal(
  shown: string,
  current: string,
  next: string,
): { target: string; floor: number } {
  if (!shown) return { target: next || "", floor: 0 };
  const shownBody = shown.trimStart();
  const nextBody = (next || "").trimStart();
  const continues =
    !!next &&
    (next.startsWith(shown) || (!!shownBody && nextBody.startsWith(shownBody)));
  if (continues) {
    const text = next.startsWith(shown)
      ? next
      : shownBody + nextBody.slice(shownBody.length);
    const floor = next.startsWith(shown) ? shown.length : shownBody.length;
    return { target: text, floor };
  }
  if (current.startsWith(shown)) return { target: current, floor: shown.length };
  return { target: shown, floor: shown.length };
}

function safeSliceEnd(text: string, rawEnd: number): number {
  const clamped = Math.max(0, Math.min(text.length, Math.floor(rawEnd)));
  if (clamped === 0 || clamped === text.length) return clamped;
  const prev = text.charCodeAt(clamped - 1);
  if (prev >= 0xd800 && prev <= 0xdbff) {
    const next = text.charCodeAt(clamped);
    if (next >= 0xdc00 && next <= 0xdfff) {
      return clamped + 1;
    }
    return clamped - 1;
  }
  return clamped;
}

const TABLE_ROW_RE = /^\s*\|.+\|\s*$/;
const TABLE_SEP_RE = /^\s*\|[\s:|-]+\|\s*$/;
const PIPE_START_RE = /^\s*\|/;
const PARTIAL_SEP_RE = /^\s*\|?[\s:|-]*$/;

function isInsideCodeFence(text: string, pos: number): boolean {
  let count = 0;
  let idx = 0;
  while (idx < pos) {
    const hit = text.indexOf("```", idx);
    if (hit < 0 || hit >= pos) break;
    count += 1;
    idx = hit + 3;
  }
  return count % 2 === 1;
}

function lineBounds(
  text: string,
  pos: number,
): { start: number; nl: number; endWithNl: number; line: string } {
  const prevNl = pos > 0 ? text.lastIndexOf("\n", pos - 1) : -1;
  const start = prevNl + 1;
  const nl = text.indexOf("\n", start);
  const endWithNl = nl >= 0 ? nl + 1 : text.length;
  const line = text.slice(start, nl >= 0 ? nl : text.length);
  return { start, nl, endWithNl, line };
}

function hasSeparatorAbove(target: string, lineStart: number): boolean {
  let pos = lineStart;
  while (pos > 0) {
    const nl = pos - 1;
    const prevStart = nl > 0 ? target.lastIndexOf("\n", nl - 1) + 1 : 0;
    const line = target.slice(prevStart, nl);
    if (!PIPE_START_RE.test(line)) return false;
    if (TABLE_SEP_RE.test(line)) return true;
    pos = prevStart;
  }
  return false;
}

/**
 * A markdown table is shown in one shot. While the trailing table is still
 * open (header, separator, or body rows can still grow), hold at its start.
 * When a non-table line follows it — or the stream is finished — snap from
 * the header through the last row together.
 */
function scanMarkdownTable(
  target: string,
  tableStart: number,
  done: boolean,
): { action: "hold" | "snap" | "skip"; end: number } {
  const header = lineBounds(target, tableStart);
  if (header.nl < 0) {
    if (!done) return { action: "hold", end: tableStart };
    if (!TABLE_ROW_RE.test(header.line)) return { action: "skip", end: tableStart };
    return { action: "snap", end: target.length };
  }
  if (!TABLE_ROW_RE.test(header.line)) return { action: "skip", end: tableStart };

  const fromBody = hasSeparatorAbove(target, tableStart);
  let pos: number;
  if (!fromBody) {
    if (header.endWithNl >= target.length) {
      return done
        ? { action: "skip", end: tableStart }
        : { action: "hold", end: tableStart };
    }
    const sep = lineBounds(target, header.endWithNl);
    if (sep.nl < 0) {
      if (!done) {
        const pending =
          sep.line.length === 0 ||
          PARTIAL_SEP_RE.test(sep.line) ||
          PIPE_START_RE.test(sep.line);
        return pending
          ? { action: "hold", end: tableStart }
          : { action: "skip", end: tableStart };
      }
      if (!TABLE_SEP_RE.test(sep.line)) return { action: "skip", end: tableStart };
      return { action: "snap", end: target.length };
    }
    if (!TABLE_SEP_RE.test(sep.line)) return { action: "skip", end: tableStart };
    pos = sep.endWithNl;
  } else {
    pos = tableStart;
  }

  while (pos < target.length) {
    const row = lineBounds(target, pos);
    if (row.nl < 0) {
      if (TABLE_ROW_RE.test(row.line)) {
        return done
          ? { action: "snap", end: target.length }
          : { action: "hold", end: tableStart };
      }
      if (PIPE_START_RE.test(row.line)) {
        return done
          ? { action: "snap", end: pos }
          : { action: "hold", end: tableStart };
      }
      return { action: "snap", end: pos };
    }
    if (TABLE_ROW_RE.test(row.line)) {
      pos = row.endWithNl;
      continue;
    }
    return { action: "snap", end: pos };
  }

  return done
    ? { action: "snap", end: target.length }
    : { action: "hold", end: tableStart };
}

function stepTableBoundary(
  target: string,
  currentEnd: number,
  candidateEnd: number,
  done: boolean,
): { end: number; tableAction: "none" | "hold" | "snap" } {
  if (candidateEnd <= currentEnd) {
    return { end: candidateEnd, tableAction: "none" };
  }
  const curLine = lineBounds(target, currentEnd);
  let pipeStart = -1;
  if (PIPE_START_RE.test(curLine.line) && !isInsideCodeFence(target, curLine.start)) {
    pipeStart = curLine.start;
  } else {
    let scan = curLine.nl;
    while (scan >= 0 && scan + 1 < candidateEnd) {
      const nextLine = lineBounds(target, scan + 1);
      if (PIPE_START_RE.test(nextLine.line) && !isInsideCodeFence(target, nextLine.start)) {
        pipeStart = nextLine.start;
        break;
      }
      scan = nextLine.nl;
    }
  }
  if (pipeStart < 0) {
    return { end: candidateEnd, tableAction: "none" };
  }
  if (pipeStart > currentEnd) {
    return { end: pipeStart, tableAction: "none" };
  }

  const table = scanMarkdownTable(target, pipeStart, done);
  if (table.action === "hold") {
    return { end: currentEnd, tableAction: "hold" };
  }
  if (table.action === "snap") {
    const end = Math.max(currentEnd, table.end);
    if (end > currentEnd) return { end, tableAction: "snap" };
    return { end: candidateEnd, tableAction: "none" };
  }

  const line = lineBounds(target, pipeStart);
  const lineEnd = line.nl < 0 ? target.length : line.endWithNl;
  return { end: Math.min(candidateEnd, lineEnd), tableAction: "none" };
}

export function createStreamPacer(opts: StreamPacerOptions): StreamPacer {
  const baseCps = Math.max(20, opts.baseCps ?? 68);
  const instant = Boolean(opts.instant);
  const now = opts.now ?? (() => (typeof performance !== "undefined" ? performance.now() : Date.now()));
  const scheduleFrame =
    opts.scheduleFrame ??
    ((cb: (ts: number) => void) => window.requestAnimationFrame(cb));
  const cancelFrame =
    opts.cancelFrame ?? ((id: number) => window.cancelAnimationFrame(id));

  let target = "";
  let floatRevealed = 0;
  let lastEmit = "";
  let lastDraining: boolean | null = null;
  let done = false;
  let stopped = false;
  let rafId: number | null = null;
  let lastTs: number | null = null;
  let rowHoldUntilTs = 0;
  const waiters: Array<() => void> = [];

  const resolveWaiters = () => {
    while (waiters.length > 0) {
      const resolve = waiters.shift();
      resolve?.();
    }
  };

  const emitIfChanged = (next: string, draining = floatRevealed < target.length) => {
    if (next === lastEmit && draining === lastDraining) return;
    lastEmit = next;
    lastDraining = draining;
    opts.onUpdate(next, { draining });
  };

  const cancelScheduled = () => {
    if (rafId !== null) {
      cancelFrame(rafId);
      rafId = null;
    }
    lastTs = null;
  };

  const tick = (ts: number) => {
    rafId = null;
    if (stopped) return;

    const prevTs = lastTs ?? ts - 16;
    lastTs = ts;
    const dtMs = Math.min(50, Math.max(8, ts - prevTs));
    const backlog = Math.max(0, target.length - floatRevealed);

    if (backlog <= 0) {
      floatRevealed = target.length;
      emitIfChanged(target);
      if (done) resolveWaiters();
      return;
    }

    const prevEnd = safeSliceEnd(target, floatRevealed);
    if (ts < rowHoldUntilTs && prevEnd < target.length) {
      const peek = stepTableBoundary(target, prevEnd, Math.min(target.length, prevEnd + 1), done);
      if (peek.tableAction === "snap") {
        rafId = scheduleFrame(tick);
        return;
      }
      if (peek.tableAction === "hold") {
        lastTs = null;
        return;
      }
      rowHoldUntilTs = 0;
    }

    const cps = done
      ? backlog > 300
        ? Math.min(1200, Math.max(baseCps * 1.6, backlog))
        : Math.max(baseCps * 1.5, backlog * 2.2)
      : baseCps + Math.min(260, backlog * 0.4);

    const nextFloat = Math.min(target.length, floatRevealed + (cps * dtMs) / 1000);
    const candidateEnd = safeSliceEnd(target, nextFloat);
    const step = stepTableBoundary(target, prevEnd, candidateEnd, done);
    const end = step.end;

    if (step.tableAction === "snap") {
      floatRevealed = end;
      const rowDelayMs = done ? (backlog > 300 ? 55 : 85) : 115;
      rowHoldUntilTs = ts + rowDelayMs;
    } else if (step.tableAction === "hold") {
      floatRevealed = end;
      emitIfChanged(target.slice(0, end), false);
      lastTs = null;
      return;
    } else {
      floatRevealed = end === candidateEnd ? Math.max(nextFloat, end) : end;
      rowHoldUntilTs = 0;
    }
    const stillDraining = end < target.length;
    if (!stillDraining) {
      floatRevealed = target.length;
    }
    emitIfChanged(target.slice(0, end), stillDraining);

    if (stillDraining) {
      rafId = scheduleFrame(tick);
    } else {
      floatRevealed = target.length;
      lastTs = null;
      if (done) resolveWaiters();
    }
  };

  const ensureRunning = () => {
    if (stopped || rafId !== null) return;
    if (floatRevealed >= target.length) {
      if (done) resolveWaiters();
      return;
    }
    lastTs = now();
    rafId = scheduleFrame(tick);
  };

  const adopt = (next: string) => {
    const shown = lastEmit;
    const plan = planReveal(shown, target, next || "");
    const droppingLead =
      shown.trimStart().length < shown.length &&
      plan.floor === shown.trimStart().length &&
      plan.target.startsWith(shown.trimStart());
    target = plan.target;
    if (droppingLead) floatRevealed = plan.floor;
    else if (floatRevealed < plan.floor) floatRevealed = plan.floor;
    if (floatRevealed > target.length) floatRevealed = target.length;
  };

  const showNow = () => {
    const end = safeSliceEnd(target, floatRevealed);
    floatRevealed = end;
    emitIfChanged(target.slice(0, end));
  };

  return {
    pushTarget(fullText: string) {
      if (stopped) return;
      adopt(fullText || "");
      if (instant) {
        floatRevealed = target.length;
        emitIfChanged(target);
        return;
      }
      ensureRunning();
    },

    replaceTarget(fullText: string) {
      if (stopped) return;
      rowHoldUntilTs = 0;
      adopt(fullText || "");
      if (instant) {
        floatRevealed = target.length;
        emitIfChanged(target);
        return;
      }
      showNow();
      ensureRunning();
    },

    markDone(finalText?: string) {
      if (stopped) return Promise.resolve();
      if (typeof finalText === "string" && finalText) adopt(finalText);
      done = true;
      if (instant || floatRevealed >= target.length) {
        cancelScheduled();
        floatRevealed = target.length;
        emitIfChanged(target);
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => {
        waiters.push(resolve);
        ensureRunning();
      });
    },

    flush() {
      cancelScheduled();
      floatRevealed = target.length;
      emitIfChanged(target);
      if (done) resolveWaiters();
    },

    stop() {
      stopped = true;
      cancelScheduled();
      resolveWaiters();
    },

    getVisible() {
      return target.slice(0, safeSliceEnd(target, floatRevealed));
    },

    isDraining() {
      return floatRevealed < target.length;
    },
  };
}
