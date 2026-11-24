/** Up to five labeled documents in one chat. */

import type { SourceAttachment, SourceDraft, SourcePart } from "./liberTypes";

export type { SourcePart };

const MAX_DOCS = 5;

function docsTitle(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  const word =
    mod10 === 1 && mod100 !== 11
      ? "документ"
      : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
        ? "документа"
        : "документов";
  return `${n} ${word}`;
}

function docUrls(draft: {
  viewMode?: "text" | "document";
  previewUrl?: string | null;
  originalUrl?: string | null;
  ingestId?: string;
}) {
  const isDoc = draft.viewMode === "document" || Boolean(draft.ingestId);
  const previewUrl = isDoc
    ? draft.previewUrl ||
      (draft.ingestId
        ? `/api/source/files/${encodeURIComponent(draft.ingestId)}/preview`
        : null)
    : draft.previewUrl;
  const originalUrl = isDoc
    ? draft.originalUrl ||
      (draft.ingestId
        ? `/api/source/files/${encodeURIComponent(draft.ingestId)}/original`
        : null)
    : draft.originalUrl;
  return {
    viewMode: (isDoc ? "document" : "text") as "document" | "text",
    previewUrl: previewUrl ?? null,
    originalUrl: originalUrl ?? null,
  };
}

export function mergeSourcePack(
  current: SourceDraft | null,
  next: SourceDraft,
): SourceDraft {
  const existing: SourcePart[] =
    current?.parts?.length
      ? current.parts
      : current?.text
        ? [
            {
              name: current.fileName || current.title || "Документ",
              text: current.text,
              title: current.title,
              ...docUrls(current),
              ingestId: current.ingestId,
              format: current.format,
            },
          ]
        : [];
  const name = (next.fileName || next.title || "Документ").trim() || "Документ";
  const part: SourcePart = {
    name,
    text: next.text,
    title: next.title || name,
    ...docUrls(next),
    ingestId: next.ingestId,
    format: next.format,
  };
  const idx = existing.findIndex((p) => p.name === name);
  let parts = existing.slice();
  if (idx >= 0) parts[idx] = part;
  else if (parts.length < MAX_DOCS) parts.push(part);
  else parts = [...parts.slice(1), part];
  const text = parts
    .map((p) => `===== ${p.name} =====\n${p.text.trim()}`)
    .join("\n\n");
  const title =
    parts.length > 1 ? docsTitle(parts.length) : next.title || name;
  return {
    ...next,
    title,
    text,
    fileName: parts.map((p) => p.name).join(", "),
    parts,
  };
}

export function attachmentsFromDraft(
  draft: SourceDraft | null | undefined,
): SourceAttachment[] {
  if (!draft || !draft.text) return [];
  if (draft.parts?.length) {
    return draft.parts
      .filter((p) => (p.text || "").trim())
      .slice(0, MAX_DOCS)
      .map((p) => {
        const urls = docUrls(p);
        return {
          title: p.title || p.name,
          text: p.text,
          fileName: p.name,
          viewMode: urls.viewMode,
          previewUrl: urls.previewUrl,
          originalUrl: urls.originalUrl,
          ingestId: p.ingestId,
          format: p.format,
        };
      });
  }
  const urls = docUrls(draft);
  return [
    {
      title: draft.title,
      text: draft.text,
      fileName: draft.fileName,
      viewMode: urls.viewMode,
      previewUrl: urls.previewUrl,
      originalUrl: urls.originalUrl,
      ingestId: draft.ingestId,
      format: draft.format,
    },
  ];
}

export function draftFromDocuments(
  docs: { name?: string; text?: string }[] | null | undefined,
): SourceDraft | null {
  const parts: SourcePart[] = (docs || [])
    .map((doc) => ({
      name: (doc.name || "Документ").trim() || "Документ",
      text: (doc.text || "").trim(),
    }))
    .filter((doc) => doc.text)
    .slice(0, MAX_DOCS);
  if (!parts.length) return null;
  const text = parts
    .map((part) => `===== ${part.name} =====\n${part.text}`)
    .join("\n\n");
  const title = parts.length > 1 ? docsTitle(parts.length) : parts[0].name;
  return {
    title,
    text,
    fileName: parts.map((part) => part.name).join(", "),
    parts,
    viewMode: "text",
  };
}
