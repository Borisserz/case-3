/** Helpers for full-screen Markdown document preview modal + original download. */

import { isDashboardSource } from "./dashboardCapture";
import type { SourceAttachment, SourceDraft } from "./liberTypes";
import { attachmentsFromDraft } from "./sourcePack";

export type OriginalDownloadTarget =
  | { kind: "url"; href: string; fileName: string }
  | { kind: "blob"; text: string; fileName: string };

export function docsForSourceModal(
  source: SourceDraft | SourceAttachment,
): SourceAttachment[] {
  if ("parts" in source && source.parts?.length) {
    return attachmentsFromDraft(source);
  }
  const originalUrl =
    source.originalUrl ||
    (source.ingestId
      ? `/api/source/files/${encodeURIComponent(source.ingestId)}/original`
      : null);
  return [
    {
      title: source.title,
      text: source.text,
      fileName: source.fileName,
      viewMode: source.viewMode,
      previewUrl: source.previewUrl,
      originalUrl,
      ingestId: source.ingestId,
      format: source.format,
    },
  ];
}

function safeDownloadName(raw: string | undefined, fallbackExt = ".md"): string {
  const base = (raw || "document").trim() || "document";
  if (/\.[a-z0-9]{1,8}$/i.test(base)) return base;
  return `${base}${fallbackExt}`;
}

export function resolveOriginalDownload(
  doc: Pick<SourceAttachment, "title" | "fileName" | "text" | "originalUrl" | "ingestId">,
): OriginalDownloadTarget {
  const href =
    (doc.originalUrl || "").trim() ||
    (doc.ingestId
      ? `/api/source/files/${encodeURIComponent(doc.ingestId)}/original`
      : "");
  const name = (doc.fileName || doc.title || "document").trim() || "document";
  if (href) {
    return { kind: "url", href, fileName: name };
  }
  return {
    kind: "blob",
    text: doc.text || "",
    fileName: safeDownloadName(name, ".md"),
  };
}

const OFFICE_EXT = new Set(["pdf", "docx", "doc", "rtf"]);

function officeExt(doc: Pick<SourceAttachment, "format" | "fileName" | "title">): string {
  const raw = (doc.format || "").trim().toLowerCase();
  if (raw) return raw;
  for (const name of [doc.fileName, doc.title]) {
    const match = (name || "").match(/\.([a-z0-9]{1,8})$/i);
    if (match) return match[1].toLowerCase();
  }
  return "";
}

/** PDF/DOCX/DOC/RTF. The rail shows a card; the markdown opens in the modal. */
export function sourceOpensAsCard(
  doc: Pick<SourceAttachment, "viewMode" | "ingestId" | "format" | "fileName" | "title" | "text">,
): boolean {
  if (isDashboardSource(doc.text || "")) return false;
  if (doc.viewMode === "document" || Boolean(doc.ingestId)) return true;
  return OFFICE_EXT.has(officeExt(doc));
}

export function sourceDocBadge(
  doc: Pick<SourceAttachment, "format" | "fileName" | "title">,
): string {
  const ext = officeExt(doc);
  return ext ? ext.toUpperCase() : "DOC";
}

/** Right rail shows the extracted markdown. The original PDF stays a download. */
export function sourceRailView(
  text: string | null | undefined,
  asDocument: boolean,
): "text" | "document" {
  if ((text || "").trim()) return "text";
  return asDocument ? "document" : "text";
}

export function sourceModalEyebrow(
  doc: Pick<SourceAttachment, "title" | "fileName" | "format">,
): string {
  const rawFmt = (doc.format || "").trim().toLowerCase();
  const extMatch = (doc.fileName || doc.title || "").match(/\.([a-z0-9]{1,8})$/i);
  const ext = rawFmt || (extMatch ? extMatch[1].toLowerCase() : "");
  if (ext === "md" || ext === "markdown") return "MD · предпросмотр";
  if (ext) return `${ext.toUpperCase()} · предпросмотр MD`;
  return "Документ · предпросмотр MD";
}
