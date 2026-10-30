/** Pure Liber run helpers (no React state, no network). */

import {
  pushThinkingLine,
  stageKey as thinkingStageKey,
  stageLabelForMode,
  type ThinkingMode,
} from "./pipelinePhrases";
import { STAGE_LABELS } from "./liberConstants";
import type { BotMsg, RunResult } from "./liberTypes";

export function appendBotThinking(
  msg: BotMsg,
  stage?: string | null,
  detail?: string | null,
  beat = false,
): BotMsg {
  const mode: ThinkingMode = msg.thinkingMode || "report";
  const key = thinkingStageKey(stage, detail, mode);
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
    mode,
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
  if (result?.output_mode === "diagram" || result?.diagrams?.length) {
    const n = result.diagrams?.length || 0;
    return n
      ? `Схема готова (${n}). Откройте карточку ниже, чтобы развернуть.`
      : "Схема не собралась — нажмите «Ещё вариант» в панели или отправьте снова.";
  }
  return "Отчёт готов";
}

/** RU toast when charts/photos soft-failed but run status is ok. */
export function softMediaFailToast(result?: {
  warnings?: string[];
  failed_charts?: string[];
  failed_figures?: string[];
  media_status?: Record<string, unknown>;
}): string | null {
  if (!result) return null;
  const failedC = Array.isArray(result.failed_charts)
    ? result.failed_charts.filter(Boolean)
    : [];
  const failedF = Array.isArray(result.failed_figures)
    ? result.failed_figures.filter(Boolean)
    : [];
  const warns = Array.isArray(result.warnings)
    ? result.warnings.filter((w) => typeof w === "string" && w.trim())
    : [];
  if (!failedC.length && !failedF.length && !warns.length) {
    // Infer from media_status if present
    const media = result.media_status;
    if (media && typeof media === "object") {
      for (const [id, st] of Object.entries(media)) {
        const ok =
          st && typeof st === "object" && "ok" in st
            ? (st as { ok?: boolean }).ok
            : undefined;
        if (ok === false) {
          if (id.startsWith("cht_")) failedC.push(id);
          else failedF.push(id);
        }
      }
    }
  }
  if (!failedC.length && !failedF.length && !warns.length) return null;
  const parts: string[] = [];
  if (failedC.length) parts.push(`график: ${failedC.slice(0, 3).join(", ")}`);
  if (failedF.length) parts.push(`фото: ${failedF.slice(0, 3).join(", ")}`);
  if (!parts.length && warns.length) {
    return `Часть медиа не собралась: ${warns[0]}`;
  }
  return `Часть медиа не собралась (${parts.join("; ")}). PDF может быть без них.`;
}

export function stageLabel(
  stage?: string,
  detail?: string | null,
  mode: ThinkingMode = "report",
): string {
  if (mode !== "report") {
    return stageLabelForMode(stage, detail, mode);
  }
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
  if (result.output_mode === "diagram" || result.diagrams?.length) {
    return `Схема · ${result.run_id}`;
  }
  if (result.output_mode === "presentation") {
    return `Презентация · ${result.run_id}`;
  }
  return `Отчёт · ${result.run_id}`;
}

/** Slides job already accepted (POST 202) — attach SSE/poll, do not POST again. */
export function slidesJobInFlight(status?: string | null): boolean {
  const st = (status || "").toLowerCase();
  return st === "running" || st === "queued" || st === "starting";
}

export function slidesJobTerminal(status?: string | null): boolean {
  const st = (status || "").toLowerCase();
  return st === "ok" || st === "error" || st === "cancelled";
}

/** True when Liber should POST /slides (idle / failed), false when done or in-flight. */
export function slidesJobNeedsKick(result: {
  slides_status?: string | null;
  downloads?: Record<string, string | undefined> | null;
}): boolean {
  if (result.downloads?.pptx) return false;
  const st = (result.slides_status || "idle").toLowerCase();
  if (st === "ok") return false;
  if (slidesJobInFlight(st)) return false;
  return true;
}

/** Provisional chat header while a run is in flight (Julius rename). */
export function provisionalSessionTitle(
  mode: "report" | "diagram" | "presentation" | null | undefined,
): string {
  if (mode === "diagram") return "Новая схема";
  if (mode === "presentation") return "Новая презентация";
  return "Новый отчёт";
}

/** Pipeline error that Liber can offer «Продолжить» for. */
export class RunFailedError extends Error {
  readonly canResume: boolean;
  readonly runId: string;
  readonly failedStage: string | null;

  constructor(
    message: string,
    opts: { canResume?: boolean; runId: string; failedStage?: string | null },
  ) {
    super(message);
    this.name = "RunFailedError";
    this.canResume = Boolean(opts.canResume);
    this.runId = opts.runId;
    this.failedStage = opts.failedStage ?? null;
  }
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

/** Narrow JSON `downloads` from Record<string, unknown> API bodies. */
export function asDownloads(
  v: unknown,
  fallback: Record<string, string>,
): Record<string, string> {
  if (!v || typeof v !== "object" || Array.isArray(v)) return fallback;
  const out: Record<string, string> = { ...fallback };
  for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
    if (typeof val === "string") out[k] = val;
  }
  return out;
}

export function asString(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
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
  vision_ok?: boolean;
  docker_ok?: boolean;
  playwright_ok?: boolean;
  soffice_ok?: boolean;
  image_api_configured?: boolean;
  kandinsky_configured?: boolean;
  image_api_ok?: boolean;
  image_api_error?: string | null;
} | null): string {
  if (!health) return "проверка…";
  const imageConfigured =
    health.image_api_configured || health.kandinsky_configured;
  let visionBit: string | null = null;
  if (health.vision_ok) visionBit = "Vision ok";
  else if (health.vision_configured) visionBit = "Vision slow";
  let imageBit: string | null = null;
  if (imageConfigured) {
    imageBit = health.image_api_ok ? "Image ok" : "Image down";
  }
  return (
    [
      visionBit,
      health.docker_ok ? "Docker" : null,
      health.playwright_ok ? "Playwright" : null,
      health.soffice_ok ? "LibreOffice" : null,
      imageBit,
    ]
      .filter(Boolean)
      .join(" · ") || "сервисы не готовы"
  );
}

/** Compact chip label for sidebar / composer. */
export function imageChipFromHealth(health: {
  image_api_configured?: boolean;
  kandinsky_configured?: boolean;
  image_api_ok?: boolean;
  image_api_error?: string | null;
} | null): { label: string; ok: boolean; hint: string } {
  if (!health) {
    return { label: "Image · …", ok: false, hint: "проверка Image API…" };
  }
  const configured =
    health.image_api_configured || health.kandinsky_configured;
  if (!configured) {
    return {
      label: "Image · off",
      ok: false,
      hint: "IMAGE_API_BASE_URL пуст — fig_* будут пропущены",
    };
  }
  if (health.image_api_ok) {
    return { label: "Image · ok", ok: true, hint: "Image API отвечает" };
  }
  return {
    label: "Image · down",
    ok: false,
    hint:
      health.image_api_error ||
      "Image API не отвечает — отчёт соберётся, фото могут пропуститься",
  };
}
