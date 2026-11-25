/** Which rail a chat edit should reopen. */

import { attachSlidesPayload } from "./attachSlidesPayload";
import type { Msg, RunResult } from "./liberTypes";
import { slidesJobInFlight } from "./runHelpers";
import type { ArtifactTab } from "../ArtifactRail";

export function offersNewChat(op: string): boolean {
  return op === "full";
}

const TEXT_ONLY_REVISE = new Set([
  "rewrite",
  "rewrite_all",
  "retitle",
  "rename_heading",
  "replace_cell",
  "replace_item",
  "add_item",
  "delete_section",
  "delete_chart",
  "delete_paragraph",
  "add_paragraph",
  "add_section",
  "caption",
  "delete_item",
  "add_row",
  "delete_row",
  "undo",
  "redo",
]);

/** A wording edit keeps the PDF and diagram on the first message. */
export function reviseChatStaysText(op: string): boolean {
  return TEXT_ONLY_REVISE.has(op.trim());
}

export function reviseSurface(
  op: string,
  titleOn = "",
): "deck" | "report" | null {
  if (
    op === "recolor_deck" ||
    op === "delete_slide" ||
    op === "reorder_slide" ||
    op === "add_slide" ||
    op === "slide_text" ||
    op === "slide_bullets" ||
    op === "restyle_structure"
  ) {
    return "deck";
  }
  if (op === "retitle" && titleOn === "deck") return "deck";
  if (
    op === "rewrite" ||
    op === "recolor_charts" ||
    op === "retype_charts" ||
    op === "retype_chart" ||
    op === "restyle_chart" ||
    op === "undo" ||
    op === "redo" ||
    op === "retitle" ||
    op === "rename_heading" ||
    op === "replace_cell" ||
    op === "replace_item" ||
    op === "add_item" ||
    op === "refine_diagram" ||
    op === "delete_section" ||
    op === "delete_chart" ||
    op === "delete_paragraph" ||
    op === "rewrite_all" ||
    op === "add_paragraph" ||
    op === "add_section" ||
    op === "caption" ||
    op === "delete_item" ||
    op === "add_row" ||
    op === "delete_row"
  ) {
    return "report";
  }
  return null;
}

export type RefreshStep = {
  surface: "deck" | "report";
  artifactRunId: string;
  op?: string;
};

export function refreshSteps(data: {
  op?: string;
  surface?: string;
  artifact_run_id?: string;
  surfaces?: Array<{ surface?: string; artifact_run_id?: string; op?: string }>;
}): RefreshStep[] {
  const listed = Array.isArray(data.surfaces) ? data.surfaces : [];
  const steps: RefreshStep[] = [];
  for (const item of listed) {
    const surface =
      item?.surface === "deck" || item?.surface === "report" ? item.surface : null;
    if (!surface) continue;
    const step: RefreshStep = {
      surface,
      artifactRunId: (item.artifact_run_id || "").trim(),
    };
    if (item.op === "refine_diagram") step.op = "refine_diagram";
    steps.push(step);
  }
  if (steps.length) return steps;
  if (data.surface === "chat") return [];
  const single =
    data.surface === "deck" || data.surface === "report"
      ? data.surface
      : reviseSurface(data.op || "");
  if (!single) return [];
  const step: RefreshStep = {
    surface: single,
    artifactRunId: (data.artifact_run_id || "").trim(),
  };
  if (data.op === "refine_diagram") step.op = "refine_diagram";
  return [step];
}

export function revisedRailPlan(
  head: string,
  artifact: string,
  surface: "deck" | "report",
  op = "",
): { fetchId: string; chainHead: string; tab: "presentation" | "preview" | "diagram" } {
  const chainHead = head.trim();
  const file = artifact.trim() || chainHead;
  return {
    fetchId: file,
    chainHead,
    tab:
      surface === "deck"
        ? "presentation"
        : op === "refine_diagram"
          ? "diagram"
          : "preview",
  };
}

export function historyRailRun(
  head: {
    run_id?: string;
    preview?: { blocks?: unknown[] } | null;
    deck?: { slides?: unknown[] } | null;
    downloads?: { pdf?: string; pptx?: string; deck_pdf?: string } | null;
    slide_pngs?: string[] | null;
  } | null,
  artifactId: string,
): string {
  const artifact = artifactId.trim();
  const headId = head?.run_id?.trim() || "";
  if (!artifact) return headId;
  const hasFile = Boolean(
    head?.preview?.blocks?.length ||
      head?.deck?.slides?.length ||
      head?.downloads?.pdf ||
      head?.downloads?.pptx ||
      head?.downloads?.deck_pdf ||
      head?.slide_pngs?.length,
  );
  if (hasFile && headId) return headId;
  return artifact;
}

export function chatToReopen(
  items: { runId: string }[],
  openId: string,
  messagesOpen: boolean,
): string {
  if (messagesOpen) return "";
  const id = openId.trim();
  if (!id) return "";
  return items.some((item) => item.runId === id) ? id : "";
}

type RefreshHosts = {
  setMsgs: (fn: (msgs: Msg[]) => Msg[]) => void;
  rememberRun: (result: RunResult) => void;
  openReportArtifact: (msgId: string, result: RunResult, tab?: ArtifactTab) => void;
};

/** The open report card, so a chat edit repaints it instead of a new bubble. */
export function reportOwnerId(
  msgs: Msg[],
  fetchId: string,
  chainHead: string,
): string {
  const wanted = new Set([fetchId.trim(), chainHead.trim()].filter(Boolean));
  if (!wanted.size) return "";
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const msg = msgs[i];
    if (msg.role !== "bot" || !msg.result?.run_id) continue;
    const rid = msg.result.run_id;
    const chain = (msg.result.chain_head || "").trim();
    if (wanted.has(rid) || (chain && wanted.has(chain))) return msg.id;
  }
  return "";
}

function paintReportResult(prev: RunResult, fresh: RunResult): RunResult {
  return {
    ...prev,
    preview: fresh.preview !== undefined ? fresh.preview : prev.preview,
    downloads: fresh.downloads !== undefined ? fresh.downloads : prev.downloads,
    diagrams: fresh.diagrams !== undefined ? fresh.diagrams : prev.diagrams,
    warnings: fresh.warnings !== undefined ? fresh.warnings : prev.warnings,
    slides_status: fresh.slides_status ?? prev.slides_status,
    slides_stage: fresh.slides_stage ?? prev.slides_stage,
    slides_error: fresh.slides_error ?? prev.slides_error,
    slide_pngs: fresh.slide_pngs !== undefined ? fresh.slide_pngs : prev.slide_pngs,
    deck: fresh.deck !== undefined ? fresh.deck : prev.deck,
    memory_section:
      fresh.memory_section !== undefined ? fresh.memory_section : prev.memory_section,
  };
}

async function readStatus(runId: string): Promise<RunResult | null> {
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/status`);
  if (!res.ok) return null;
  return (await res.json()) as RunResult;
}

export async function refreshRevisedArtifact(
  runId: string,
  surface: "deck" | "report",
  msgId: string,
  hosts: RefreshHosts,
  artifactRunId = "",
  options?: {
    remember?: boolean;
    isolated?: boolean;
    op?: string;
    memorySection?: string;
    quietCards?: boolean;
    readMsgs?: () => Msg[];
  },
): Promise<void> {
  const plan = revisedRailPlan(runId, artifactRunId, surface, options?.op || "");
  let result = await readStatus(plan.fetchId);
  if (!result) return;
  if (surface === "deck") {
    for (let i = 0; i < 20 && slidesJobInFlight(result.slides_status); i += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 700));
      const next = await readStatus(plan.fetchId);
      if (next) result = next;
    }
    try {
      const slides = await fetch(
        `/api/runs/${encodeURIComponent(plan.fetchId)}/slides`,
      );
      if (slides.ok) result = attachSlidesPayload(result, await slides.json());
    } catch {
      /* status is enough to open the rail */
    }
  }
  const emptyReport =
    surface === "report" &&
    !result.preview?.blocks?.length &&
    !result.downloads?.pdf &&
    !result.downloads?.docx;
  if (!options?.isolated && plan.chainHead && plan.chainHead !== result.run_id) {
    result = { ...result, chain_head: plan.chainHead };
  }
  if (options?.isolated) result = { ...result, isolated: true };
  if (typeof options?.memorySection === "string") {
    result = { ...result, memory_section: options.memorySection };
  } else if (options?.op === "undo") {
    result = { ...result, memory_section: "" };
  }
  if (!options?.quietCards) {
    hosts.setMsgs((msgs) =>
      msgs.map((msg) => {
        if (msg.id !== msgId || msg.role !== "bot") return msg;
        return { ...msg, result, pending: false };
      }),
    );
  } else {
    hosts.setMsgs((msgs) =>
      msgs.map((msg) => {
        if (msg.id !== msgId || msg.role !== "bot") return msg;
        return { ...msg, pending: false };
      }),
    );
  }
  if (options?.remember !== false) {
    hosts.rememberRun(
      plan.chainHead && plan.chainHead !== result.run_id
        ? { ...result, run_id: plan.chainHead }
        : result,
    );
  }
  const ownerId = reportOwnerId(
    options?.readMsgs?.() ?? [],
    plan.fetchId,
    plan.chainHead,
  );
  if (ownerId) {
    hosts.setMsgs((msgs) =>
      msgs.map((msg) => {
        if (msg.id !== ownerId || msg.role !== "bot" || !msg.result) return msg;
        return { ...msg, result: paintReportResult(msg.result, result) };
      }),
    );
  }
  if (!emptyReport) hosts.openReportArtifact(ownerId || msgId, result, plan.tab);
}
