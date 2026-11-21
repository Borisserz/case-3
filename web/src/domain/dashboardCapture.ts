/** Stimulsoft viewer → one markdown per PNG and per table PDF. */

import { mergeSourcePack } from "./sourcePack";
import type { SourceDraft } from "./liberTypes";

export const CAPTURE_MESSAGE = "liber-dashboard-capture";

const DEFAULT_VIEWER = "http://127.0.0.1:8040/viewer";

export type CaptureFile = {
  name: string;
  ext: "png" | "pdf";
  data_b64: string;
};

export function viewerFrameUrl(raw?: string | null): string {
  const trimmed = (raw || "").trim().replace(/\/+$/, "");
  const base = trimmed || DEFAULT_VIEWER.replace(/\/viewer$/, "");
  if (/\/viewer$/i.test(base)) return base;
  return `${base}/viewer`;
}

export function captureOriginOk(origin: string, viewerUrl: string): boolean {
  try {
    return new URL(viewerUrl).origin === origin;
  } catch {
    return false;
  }
}

export function filesFromCapture(data: unknown): CaptureFile[] {
  if (!data || typeof data !== "object") return [];
  const msg = data as { type?: unknown; files?: unknown };
  if (msg.type !== CAPTURE_MESSAGE || !Array.isArray(msg.files)) return [];
  const out: CaptureFile[] = [];
  for (const item of msg.files) {
    if (!item || typeof item !== "object") continue;
    const row = item as { name?: unknown; ext?: unknown; data_b64?: unknown };
    const ext = row.ext === "png" || row.ext === "pdf" ? row.ext : null;
    const name = typeof row.name === "string" ? row.name.trim() : "";
    const data_b64 = typeof row.data_b64 === "string" ? row.data_b64.trim() : "";
    if (!ext || !name || !data_b64) continue;
    out.push({ name, ext, data_b64 });
  }
  return out;
}

export function markdownDocName(fileName: string): string {
  const base = (fileName || "").trim().split(/[/\\]/).pop() || "dashboard";
  const stem = base.replace(/\.(png|pdf|md)$/i, "") || "dashboard";
  return `${stem}.md`;
}

export function fileFromCapture(file: CaptureFile): File {
  const binary = atob(file.data_b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const type = file.ext === "png" ? "image/png" : "application/pdf";
  return new File([bytes], file.name, { type });
}

export function documentsFromService(
  data: unknown,
): { name: string; markdown: string }[] {
  if (!data || typeof data !== "object") return [];
  const docs = (data as { documents?: unknown }).documents;
  if (!Array.isArray(docs)) return [];
  const out: { name: string; markdown: string }[] = [];
  for (const item of docs) {
    if (!item || typeof item !== "object") continue;
    const row = item as { name?: unknown; markdown?: unknown };
    const name = typeof row.name === "string" ? row.name.trim() : "";
    const markdown = typeof row.markdown === "string" ? row.markdown.trim() : "";
    if (!name || !markdown) continue;
    out.push({ name, markdown });
  }
  return out;
}

export function attachCaptureMarkdowns(
  current: SourceDraft | null,
  docs: { name: string; markdown: string }[],
): SourceDraft | null {
  let next = current;
  for (const doc of docs) {
    const text = (doc.markdown || "").trim();
    if (!text) continue;
    const fileName = markdownDocName(doc.name);
    next = mergeSourcePack(next, {
      title: fileName.replace(/\.md$/i, ""),
      text,
      fileName,
      viewMode: "text",
    });
  }
  return next;
}
