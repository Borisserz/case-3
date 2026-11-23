/** Latest completed bot run in this chat, for the next POST /api/run. */

import { dashboardCardFromSource, type DashboardCard } from "./dashboardCapture";

export type MemoryTurn = {
  run_id?: string;
  chat_prompt?: string;
  chat_summary?: string;
  chat_opening?: string;
  dashboard_source?: string;
  dialogue?: { user?: string; assistant?: string }[];
  photos?: { url: string; name?: string }[];
};

export type ThreadLine = {
  id: string;
  role: "user" | "bot";
  text: string;
  lead?: string;
  photos?: { url: string; name?: string }[];
  dashboard?: DashboardCard;
};

export function messagesFromMemory(
  turns: MemoryTurn[],
  id: () => string,
): ThreadLine[] {
  const lines: ThreadLine[] = [];
  for (const turn of turns) {
    const prompt = (turn.chat_prompt || "").trim();
    const photos = (turn.photos || []).filter((photo) => photo.url);
    if (prompt || photos.length) {
      lines.push({
        id: id(),
        role: "user",
        text: prompt,
        photos: photos.length ? photos : undefined,
      });
    }
    const summary = (turn.chat_summary || "").trim();
    const opening = (turn.chat_opening || "").trim();
    const dashboard = dashboardCardFromSource(turn.dashboard_source || "") || undefined;
    if (summary || opening || dashboard) {
      const lead = opening && opening !== summary ? opening : undefined;
      lines.push({
        id: id(),
        role: "bot",
        text: summary || opening,
        lead,
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
