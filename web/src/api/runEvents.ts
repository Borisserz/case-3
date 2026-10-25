/** SSE client for Liber run progress (stages / artifacts / terminal). */

export type RunEventsHandlers = {
  onStage?: (stage: string, detail: string | null, scope: string) => void;
  onArtifact?: (kind: string) => void;
  onTerminal?: (kind: "done" | "error" | "cancelled", error?: string) => void;
  /** SSE failed — caller should fall back to status poll. */
  onFallback?: () => void;
};

/**
 * Open GET /api/runs/{id}/events. Returns closer.
 * Does not stream model thoughts — only craft stages + artifacts.
 *
 * Note: SSE event name `error` collides with EventSource connection errors —
 * we distinguish MessageEvent (server terminal) vs bare Event (transport).
 */
export function openRunEvents(
  runId: string,
  handlers: RunEventsHandlers,
): () => void {
  const es = new EventSource(
    `/api/runs/${encodeURIComponent(runId)}/events`,
  );
  let closed = false;
  let gotEvent = false;
  let fallbackFired = false;
  let finished = false;

  const fireFallback = () => {
    if (fallbackFired || closed || finished) return;
    fallbackFired = true;
    handlers.onFallback?.();
  };

  const finish = (kind: "done" | "error" | "cancelled", err?: string) => {
    if (finished) return;
    finished = true;
    handlers.onTerminal?.(kind, err);
    es.close();
  };

  const onStage = (ev: Event) => {
    gotEvent = true;
    try {
      const data = JSON.parse((ev as MessageEvent).data) as {
        stage?: string;
        detail?: string | null;
        scope?: string;
      };
      handlers.onStage?.(
        data.stage || "queued",
        data.detail ?? null,
        data.scope || "pipeline",
      );
    } catch {
      /* ignore */
    }
  };

  const onArtifact = (ev: Event) => {
    gotEvent = true;
    try {
      const data = JSON.parse((ev as MessageEvent).data) as { kind?: string };
      if (data.kind) handlers.onArtifact?.(data.kind);
    } catch {
      /* ignore */
    }
  };

  const onDone = (ev: Event) => {
    gotEvent = true;
    let err: string | undefined;
    try {
      const data = JSON.parse((ev as MessageEvent).data) as { error?: string };
      err = data.error;
    } catch {
      /* ignore */
    }
    finish("done", err);
  };

  const onCancelled = (ev: Event) => {
    gotEvent = true;
    finish("cancelled");
    void ev;
  };

  const onErrorEv = (ev: Event) => {
    // Server `event: error` is MessageEvent with JSON {status|error}.
    // Bare EventSource transport errors must NOT be treated as run failure.
    if (ev instanceof MessageEvent && typeof ev.data === "string" && ev.data) {
      try {
        const data = JSON.parse(ev.data) as {
          error?: string;
          status?: string;
        };
        if (data.error != null || data.status === "error") {
          gotEvent = true;
          finish("error", data.error);
          return;
        }
      } catch {
        /* not our terminal payload — fall through to transport handling */
      }
    }
    // Transport failure — poll fallback.
    if (!gotEvent) {
      fireFallback();
      es.close();
    } else if (es.readyState === EventSource.CLOSED) {
      fireFallback();
    }
  };

  es.addEventListener("stage", onStage);
  es.addEventListener("step", onStage);
  es.addEventListener("artifact", onArtifact);
  es.addEventListener("done", onDone);
  es.addEventListener("cancelled", onCancelled);
  es.addEventListener("error", onErrorEv);

  return () => {
    closed = true;
    es.removeEventListener("stage", onStage);
    es.removeEventListener("step", onStage);
    es.removeEventListener("artifact", onArtifact);
    es.removeEventListener("done", onDone);
    es.removeEventListener("cancelled", onCancelled);
    es.removeEventListener("error", onErrorEv);
    es.close();
  };
}
