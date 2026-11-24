/** Adaptive frame-paced text revealer for smooth, flicker-free SSE streaming. */

export type StreamPacerOptions = {
  /** Base reading speed in UTF-16 chars/sec (default ~68 for calm editorial feel). */
  baseCps?: number;
  /** Skip animation and reveal immediately (e.g. prefers-reduced-motion). */
  instant?: boolean;
  onUpdate: (visibleText: string) => void;
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

function commonPrefixLen(a: string, b: string): number {
  const max = Math.min(a.length, b.length);
  let i = 0;
  while (i < max && a.charCodeAt(i) === b.charCodeAt(i)) {
    i += 1;
  }
  return i;
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
  let done = false;
  let stopped = false;
  let rafId: number | null = null;
  let lastTs: number | null = null;
  const waiters: Array<() => void> = [];

  const resolveWaiters = () => {
    while (waiters.length > 0) {
      const resolve = waiters.shift();
      resolve?.();
    }
  };

  const emitIfChanged = (next: string) => {
    if (next === lastEmit) return;
    lastEmit = next;
    opts.onUpdate(next);
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

    const cps = done
      ? backlog > 300
        ? Math.min(1200, Math.max(baseCps * 1.6, backlog))
        : Math.max(baseCps * 1.5, backlog * 2.2)
      : baseCps + Math.min(260, backlog * 0.4);

    floatRevealed = Math.min(target.length, floatRevealed + (cps * dtMs) / 1000);
    const end = safeSliceEnd(target, floatRevealed);
    if (end > floatRevealed) {
      floatRevealed = end;
    }
    emitIfChanged(target.slice(0, end));

    if (end < target.length) {
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

  return {
    pushTarget(fullText: string) {
      if (stopped) return;
      target = fullText || "";
      if (instant) {
        floatRevealed = target.length;
        emitIfChanged(target);
        return;
      }
      if (floatRevealed > target.length) {
        floatRevealed = safeSliceEnd(target, target.length);
        emitIfChanged(target.slice(0, floatRevealed));
      }
      ensureRunning();
    },

    replaceTarget(fullText: string) {
      if (stopped) return;
      const next = fullText || "";
      const visible = target.slice(0, safeSliceEnd(target, floatRevealed));
      const keep = commonPrefixLen(visible, next);
      target = next;
      if (instant) {
        floatRevealed = target.length;
        emitIfChanged(target);
        return;
      }
      floatRevealed = Math.min(floatRevealed, keep);
      const end = safeSliceEnd(target, floatRevealed);
      emitIfChanged(target.slice(0, end));
      ensureRunning();
    },

    markDone(finalText?: string) {
      if (stopped) return Promise.resolve();
      if (typeof finalText === "string") {
        const next = finalText;
        if (next && next !== target) {
          const visible = target.slice(0, safeSliceEnd(target, floatRevealed));
          const keep = commonPrefixLen(visible, next);
          target = next;
          floatRevealed = Math.min(floatRevealed, keep);
        }
      }
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
