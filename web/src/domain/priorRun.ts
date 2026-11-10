/** Latest completed bot run in this chat, for the next POST /api/run. */

export function priorRunIdFromMessages(
  msgs: Array<{ role: string; result?: { run_id?: string } | null }>,
): string | null {
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const msg = msgs[i];
    if (msg.role !== "bot") continue;
    const id = msg.result?.run_id?.trim();
    if (id) return id;
  }
  return null;
}
