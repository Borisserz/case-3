/** Pure Liber run helpers (no React state). */

import {
  pushThinkingLine,
  stageKey as thinkingStageKey,
} from "./pipelinePhrases";
import { STAGE_LABELS } from "./liberConstants";
import type { BotMsg, RunResult } from "./liberTypes";

export function appendBotThinking(
  msg: BotMsg,
  stage?: string | null,
  detail?: string | null,
  beat = false,
): BotMsg {
  const key = thinkingStageKey(stage, detail);
  const now = Date.now();
  const stageAt =
    msg.thinkingStageKey === key && msg.thinkingStageAt
      ? msg.thinkingStageAt
      : now;
  const dwellSec = (now - stageAt) / 1000;
  const startedAt = msg.thinkingStartedAt || now;
  const thinking = pushThinkingLine(msg.thinking || [], {
    stage,
    detail,
    dwellSec,
    beat,
    seed: startedAt,
  });
  return {
    ...msg,
    thinking,
    thinkingStartedAt: startedAt,
    thinkingStageKey: key,
    thinkingStageAt: stageAt,
  };
}

export function reportReadyText(result?: RunResult, streamed?: string): string {
  const fromResult = (result?.chat_summary || "").trim();
  if (fromResult) return fromResult;
  const fromStream = (streamed || "").trim();
  if (fromStream) return fromStream;
  return "Отчёт готов";
}

/** Open SSE summary stream; returns closer. */
export function openSummaryStream(
  runId: string,
  onDelta: (full: string) => void,
  onDone: (full: string, status: string) => void,
): () => void {
  const es = new EventSource(
    `/api/runs/${encodeURIComponent(runId)}/summary/stream`,
  );
  let acc = "";
  const onDeltaEv = (ev: Event) => {
    try {
      const data = JSON.parse((ev as MessageEvent).data) as { text?: string };
      acc += data.text || "";
      onDelta(acc);
    } catch {
      /* ignore */
    }
  };
  const onDoneEv = (ev: Event) => {
    try {
      const data = JSON.parse((ev as MessageEvent).data) as {
        text?: string;
        status?: string;
      };
      const final = (data.text || acc || "").trim();
      onDone(final, data.status || "ok");
    } catch {
      onDone(acc, "ok");
    }
    es.close();
  };
  es.addEventListener("delta", onDeltaEv);
  es.addEventListener("done", onDoneEv);
  es.onerror = () => {
    es.close();
  };
  return () => {
    es.removeEventListener("delta", onDeltaEv);
    es.removeEventListener("done", onDoneEv);
    es.close();
  };
}

export function stageLabel(stage?: string, detail?: string | null): string {
  if (detail && stage === "charts") return `Рисую ${detail}…`;
  if (stage && STAGE_LABELS[stage]) return STAGE_LABELS[stage];
  return "Генерирую документ…";
}

export function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function readTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () =>
      reject(reader.error ?? new Error("Не удалось прочитать файл"));
    reader.readAsText(file);
  });
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function reportThumb(result: RunResult): string | null {
  const blocks = result.preview?.blocks;
  if (blocks) {
    for (const b of blocks) {
      if (b.type === "figure" && b.url) return b.url;
    }
  }
  return result.previews?.[0]?.url ?? null;
}

export function reportTitle(result: RunResult): string {
  const t = result.preview?.title?.trim();
  if (t) return t;
  return `Отчёт · ${result.run_id}`;
}

/** C8: human status error with failed charts + TeX log tail. */
export function formatRunStatusError(
  body: Record<string, unknown>,
  runId: string,
): string {
  const failedC = Array.isArray(body.failed_charts)
    ? body.failed_charts.filter(Boolean)
    : [];
  const failedF = Array.isArray(body.failed_figures)
    ? body.failed_figures.filter(Boolean)
    : [];
  const logTail =
    typeof body.latex_log_tail === "string" ? body.latex_log_tail.trim() : "";
  const logHint = logTail
    ? logTail
        .split("\n")
        .filter((ln: string) => ln.trim())
        .slice(-6)
        .join(" | ")
    : "";
  return [
    (body.error as string) || (body.message as string),
    failedC.length ? `график ${failedC.join(", ")}` : null,
    failedF.length ? `фото ${failedF.join(", ")}` : null,
    logHint ? `TeX: ${logHint}` : null,
    runId ? `run ${runId}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** FastAPI error body → message string (sync /api/run failures). */
export function formatApiDetailError(
  data: Record<string, unknown>,
  statusText: string,
): string {
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { message?: string; run_id?: string; hint?: string };
    return [d.message, d.run_id ? `run ${d.run_id}` : null, d.hint]
      .filter(Boolean)
      .join(" · ");
  }
  if (Array.isArray(detail)) {
    return detail
      .map((d: { msg?: string }) => d.msg || JSON.stringify(d))
      .join("; ");
  }
  return (data.error as string) || statusText;
}

export function paradeHintFromHealth(health: {
  vision_configured?: boolean;
  docker_ok?: boolean;
  playwright_ok?: boolean;
  image_api_configured?: boolean;
  kandinsky_configured?: boolean;
} | null): string {
  if (!health) return "проверка…";
  return (
    [
      health.vision_configured ? "Vision" : null,
      health.docker_ok ? "Docker" : null,
      health.playwright_ok ? "Playwright" : null,
      health.image_api_configured || health.kandinsky_configured
        ? "Image API"
        : null,
    ]
      .filter(Boolean)
      .join(" · ") || "сервисы не готовы"
  );
}
