/** Latest completed bot run in this chat, for the next POST /api/run. */

import { dashboardCardFromSource, type DashboardCard } from "./dashboardCapture";
import type { MediaPreview, RunResult, SourceAttachment } from "./liberTypes";

export type MemoryPreview = {
  id?: string;
  kind?: string;
  url: string;
  caption?: string;
};

export type MemoryAttachment = {
  name?: string;
  title?: string;
  fileName?: string;
  text?: string;
  viewMode?: "text" | "document";
  previewUrl?: string | null;
  originalUrl?: string | null;
  ingestId?: string;
  format?: string;
};

export type MemoryTurn = {
  run_id?: string;
  output_mode?: string;
  chat_prompt?: string;
  chat_summary?: string;
  chat_opening?: string;
  dashboard_source?: string;
  dialogue?: { user?: string; assistant?: string }[];
  photos?: { url: string; name?: string }[];
  attachments?: MemoryAttachment[];
  previews?: MemoryPreview[];
};

export type ThreadLine = {
  id: string;
  role: "user" | "bot";
  text: string;
  lead?: string;
  runId?: string;
  outputMode?: string;
  photos?: { url: string; name?: string }[];
  attachment?: SourceAttachment;
  attachments?: SourceAttachment[];
  previews?: MediaPreview[];
  dashboard?: DashboardCard;
};

function previewIdFromUrl(url: string, idx: number): string {
  const clean = url.split("?")[0] || "";
  const file = clean.split("/").pop() || "";
  const stem = file.replace(/\.[^.]+$/, "").trim();
  return stem || `media_${idx + 1}`;
}

function normalizePreviewKind(rawKind: string | undefined, id: string): string {
  const k = (rawKind || "").trim().toLowerCase();
  if (k) return k;
  if (id.startsWith("dia_")) return "diagram";
  if (id.startsWith("fig_")) return "figure";
  return "chart";
}

export function messagesFromMemory(
  turns: MemoryTurn[],
  id: () => string,
): ThreadLine[] {
  const lines: ThreadLine[] = [];
  for (const turn of turns) {
    const prompt = (turn.chat_prompt || "").trim();
    const photos = (turn.photos || []).filter((photo) => photo.url);
    const attachments: SourceAttachment[] = (turn.attachments || [])
      .map((item): SourceAttachment | null => {
        const text = (item.text || "").trim();
        const name = (item.fileName || item.title || item.name || "Документ").trim();
        if (!text && !item.previewUrl) return null;
        return {
          title: (item.title || name).trim() || name,
          text,
          fileName: (item.fileName || item.name || name).trim() || name,
          viewMode: item.viewMode === "document" ? "document" : "text",
          previewUrl: item.previewUrl ?? null,
          originalUrl: item.originalUrl ?? null,
          ingestId: item.ingestId,
          format: item.format,
        };
      })
      .filter((x): x is SourceAttachment => Boolean(x));
    if (prompt || photos.length || attachments.length) {
      lines.push({
        id: id(),
        role: "user",
        text: prompt || (attachments.length ? "Собрать отчёт" : ""),
        photos: photos.length ? photos : undefined,
        attachment: attachments[0],
        attachments: attachments.length ? attachments : undefined,
      });
    }
    const summary = (turn.chat_summary || "").trim();
    const opening = (turn.chat_opening || "").trim();
    const dashboard = dashboardCardFromSource(turn.dashboard_source || "") || undefined;
    const previews: MediaPreview[] = (turn.previews || [])
      .filter((item) => item && item.url)
      .map((item, idx) => {
        const pid = (item.id || "").trim() || previewIdFromUrl(item.url, idx);
        return {
          id: pid,
          kind: normalizePreviewKind(item.kind, pid),
          url: item.url,
        };
      });
    if (summary || opening || dashboard || previews.length) {
      const lead = opening && opening !== summary ? opening : undefined;
      const runId = (turn.run_id || "").trim() || undefined;
      const outputMode = (turn.output_mode || "").trim() || undefined;
      lines.push({
        id: id(),
        role: "bot",
        text: summary || opening,
        lead,
        runId,
        outputMode,
        previews: previews.length ? previews : undefined,
        dashboard,
      });
    }
    for (const note of turn.dialogue || []) {
      const user = (note.user || "").trim();
      const assistant = (note.assistant || "").trim();
      if (user) lines.push({ id: id(), role: "user", text: user });
      if (assistant) lines.push({ id: id(), role: "bot", text: assistant });
    }
  }
  return lines;
}

const STORED_MODES = new Set(["report", "diagram", "presentation"]);

export function botHistoryResult(
  line: Pick<ThreadLine, "runId" | "outputMode" | "previews">,
  fallbackRunId: string,
): RunResult | undefined {
  if (!line.previews?.length) return undefined;
  const runId = (line.runId || "").trim() || fallbackRunId;
  const chartsCount = line.previews.filter(
    (p) => p.kind === "chart" || p.id.startsWith("cht_"),
  ).length;
  return {
    run_id: runId,
    status: "ok",
    output_mode: line.outputMode || "chat",
    downloads: {},
    previews: line.previews,
    charts_ok: chartsCount,
    figures_ok: 0,
    charts_planned: [],
    figures_planned: [],
    warnings: [],
  };
}

/** A past report, scheme, or deck can be opened even when only the run id was kept. */
export function historyResult(
  line: Pick<ThreadLine, "runId" | "outputMode" | "previews">,
  fallbackRunId: string,
): RunResult | undefined {
  const fromPreviews = botHistoryResult(line, fallbackRunId);
  if (fromPreviews) return fromPreviews;
  const mode = (line.outputMode || "").trim();
  const runId = (line.runId || "").trim();
  if (!runId || !STORED_MODES.has(mode)) return undefined;
  return {
    run_id: runId,
    status: "ok",
    output_mode: mode,
    downloads: {},
    charts_ok: 0,
    figures_ok: 0,
    charts_planned: [],
    figures_planned: [],
    warnings: [],
  };
}

export function storedOpenLabel(mode: string | undefined): string | null {
  if (mode === "report") return "Открыть отчёт";
  if (mode === "diagram") return "Открыть схему";
  if (mode === "presentation") return "Открыть презентацию";
  return null;
}

/** The chat card: a file, a deck, or a scheme. Inline chart PNGs are not a card. */
export function messageHasArtifact(result: RunResult | null | undefined): boolean {
  if (!result) return false;
  return Boolean(
    result.preview?.blocks?.length ||
      result.downloads?.pdf ||
      result.downloads?.docx ||
      result.downloads?.pptx ||
      result.downloads?.deck_pdf ||
      result.diagrams?.length ||
      result.deck?.slides?.length ||
      result.slide_pngs?.length,
  );
}

/** Report, scheme, and deck turns whose files must be loaded again on reopen. */
export function artifactRunIds(lines: ThreadLine[]): string[] {
  const ids: string[] = [];
  for (const line of lines) {
    if (line.role !== "bot") continue;
    const mode = (line.outputMode || "").trim();
    const runId = (line.runId || "").trim();
    if (!runId || !STORED_MODES.has(mode) || ids.includes(runId)) continue;
    ids.push(runId);
  }
  return ids;
}

/**
 * Put the saved file back on the turn that built it.
 * Chart and diagram PNGs on that turn stay attached, and a later chat
 * answer does not inherit the report or the deck.
 */
export function restoredBotResult(
  line: Pick<ThreadLine, "runId" | "outputMode" | "previews">,
  statuses: ReadonlyMap<string, RunResult>,
  fallbackRunId: string,
): RunResult | undefined {
  const runId = (line.runId || "").trim();
  const mode = (line.outputMode || "").trim();
  const loaded = runId ? statuses.get(runId) : undefined;
  if (loaded && STORED_MODES.has(mode)) {
    return {
      ...loaded,
      run_id: loaded.run_id || runId,
      output_mode: loaded.output_mode || mode,
      previews: line.previews?.length ? line.previews : loaded.previews,
    };
  }
  return historyResult(line, fallbackRunId);
}

export function priorRunIdFromMessages(
  msgs: Array<{
    role: string;
    result?: { run_id?: string; chain_head?: string; isolated?: boolean } | null;
  }>,
): string | null {
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const msg = msgs[i];
    if (msg.role !== "bot" || msg.result?.isolated) continue;
    const head = msg.result?.chain_head?.trim();
    if (head) return head;
    const id = msg.result?.run_id?.trim();
    if (id) return id;
  }
  return null;
}
