/** Which rail a chat edit should reopen. */

import { attachSlidesPayload } from "./attachSlidesPayload";
import type { Msg, RunResult } from "./liberTypes";
import { slidesJobInFlight } from "./runHelpers";
import type { ArtifactTab } from "../ArtifactRail";

export function reviseSurface(
  op: string,
  titleOn = "",
): "deck" | "report" | null {
  if (op === "recolor_deck" || op === "delete_slide" || op === "reorder_slide") {
    return "deck";
  }
  if (op === "retitle" && titleOn === "deck") return "deck";
  if (
    op === "rewrite" ||
    op === "recolor_charts" ||
    op === "retype_charts" ||
    op === "undo" ||
    op === "redo" ||
    op === "retitle"
  ) {
    return "report";
  }
  return null;
}

export function revisedRailPlan(
  head: string,
  artifact: string,
  surface: "deck" | "report",
): { fetchId: string; chainHead: string; tab: "presentation" | "preview" } {
  const chainHead = head.trim();
  const file = artifact.trim() || chainHead;
  return {
    fetchId: file,
    chainHead,
    tab: surface === "deck" ? "presentation" : "preview",
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
): Promise<void> {
  const plan = revisedRailPlan(runId, artifactRunId, surface);
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
  if (plan.chainHead && plan.chainHead !== result.run_id) {
    result = { ...result, chain_head: plan.chainHead };
  }
  hosts.setMsgs((msgs) =>
    msgs.map((msg) => {
      if (msg.id !== msgId || msg.role !== "bot") return msg;
      return { ...msg, result, pending: false };
    }),
  );
  hosts.rememberRun(
    plan.chainHead && plan.chainHead !== result.run_id
      ? { ...result, run_id: plan.chainHead }
      : result,
  );
  hosts.openReportArtifact(msgId, result, plan.tab);
}
