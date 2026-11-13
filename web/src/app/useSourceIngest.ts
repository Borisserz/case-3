/** Paste-long-text + file/photo ingest + drop for Liber composer. */

import {
  useCallback,
  useRef,
  type Dispatch,
  type DragEvent,
  type SetStateAction,
} from "react";
import type { ActiveArtifact } from "../ArtifactRail";
import { LONG_TEXT_CHARS } from "../domain/liberConstants";
import type { SourceDraft } from "../domain/liberTypes";
import { readTextFile } from "../domain/runHelpers";
import {
  ingestOfficeSource,
  isOfficeSourceFile,
} from "../domain/sourceOfficeIngest";

type Deps = {
  setFile: Dispatch<SetStateAction<File | null>>;
  setSourceDraft: Dispatch<SetStateAction<SourceDraft | null>>;
  setPlaqueDismissed: Dispatch<SetStateAction<boolean>>;
  setDeckApplyHint: Dispatch<SetStateAction<string | null>>;
  setActiveArtifact: Dispatch<SetStateAction<ActiveArtifact | null>>;
  setAttachPhotos: Dispatch<SetStateAction<File[]>>;
  setForbidImages: Dispatch<SetStateAction<boolean>>;
  setMaxImages: Dispatch<SetStateAction<number>>;
  setDrag: Dispatch<SetStateAction<boolean>>;
  showToast: (message: string, ms?: number) => void;
};

function artifactFromDraft(draft: SourceDraft): ActiveArtifact {
  return {
    kind: "source",
    tab: "source",
    title: draft.title,
    text: draft.text,
    fileName: draft.fileName,
    viewMode: draft.viewMode || "text",
    previewUrl: draft.previewUrl,
    originalUrl: draft.originalUrl,
    format: draft.format,
  };
}

export function useSourceIngest({
  setFile,
  setSourceDraft,
  setPlaqueDismissed,
  setDeckApplyHint,
  setActiveArtifact,
  setAttachPhotos,
  setForbidImages,
  setMaxImages,
  setDrag,
  showToast,
}: Deps) {
  const blobUrlRef = useRef<string | null>(null);

  const revokeBlob = useCallback(() => {
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
  }, []);

  const applySourceDraft = useCallback(
    (draft: SourceDraft) => {
      setFile(null);
      setSourceDraft(draft);
      setPlaqueDismissed(false);
      setDeckApplyHint(null);
      setActiveArtifact(artifactFromDraft(draft));
    },
    [
      setFile,
      setSourceDraft,
      setPlaqueDismissed,
      setDeckApplyHint,
      setActiveArtifact,
    ],
  );

  const capturePastedSource = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (trimmed.length <= LONG_TEXT_CHARS) return false;
      revokeBlob();
      applySourceDraft({
        title: "Текст",
        text: trimmed,
        viewMode: "text",
      });
      return true;
    },
    [applySourceDraft, revokeBlob],
  );

  const ingestFiles = useCallback(
    (list: FileList | File[]) => {
      const arr = Array.from(list);
      for (const f of arr) {
        if (
          /\.(txt|md)$/i.test(f.name) ||
          f.type === "text/plain" ||
          f.type === "text/markdown"
        ) {
          revokeBlob();
          setPlaqueDismissed(false);
          setDeckApplyHint(null);
          void (async () => {
            try {
              const text = await readTextFile(f);
              applySourceDraft({
                title: f.name,
                text,
                fileName: f.name,
                viewMode: "text",
              });
            } catch (err) {
              showToast(
                err instanceof Error
                  ? err.message
                  : "Не удалось прочитать файл",
              );
            }
          })();
          continue;
        }
        if (isOfficeSourceFile(f)) {
          showToast(`Читаю ${f.name}…`, 8000);
          const localPreview =
            /\.pdf$/i.test(f.name) || f.type === "application/pdf"
              ? URL.createObjectURL(f)
              : null;
          if (localPreview) {
            revokeBlob();
            blobUrlRef.current = localPreview;
          }
          void (async () => {
            try {
              const out = await ingestOfficeSource(f);
              const serverPreview = out.preview_url || null;
              // Prefer local PDF blob for instant viewer; DOCX uses server PDF.
              const previewUrl =
                localPreview || serverPreview || null;
              if (serverPreview && localPreview) {
                // keep local blob — already shown; server extract is enough
              }
              applySourceDraft({
                title: out.filename,
                text: out.markdown,
                fileName: out.filename,
                viewMode: "document",
                previewUrl,
                originalUrl: out.original_url || null,
                ingestId: out.ingest_id,
                format: out.format,
              });
              if (out.warnings?.length) {
                showToast(out.warnings[0], 5000);
              } else {
                showToast(
                  previewUrl
                    ? `Документ: ${out.filename}`
                    : `Документ: ${out.filename} (без PDF-превью)`,
                  2800,
                );
              }
            } catch (err) {
              if (localPreview) revokeBlob();
              showToast(
                err instanceof Error
                  ? err.message
                  : "Не удалось разобрать документ",
                6000,
              );
            }
          })();
          continue;
        }
        if (/^image\//.test(f.type) || /\.(png|jpe?g)$/i.test(f.name)) {
          setAttachPhotos((prev) => [...prev, f].slice(0, 5));
          setForbidImages(false);
          setMaxImages((n) => Math.max(n, 5));
        }
      }
    },
    [
      applySourceDraft,
      revokeBlob,
      setPlaqueDismissed,
      setDeckApplyHint,
      setAttachPhotos,
      setForbidImages,
      setMaxImages,
      showToast,
    ],
  );

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDrag(false);
      if (e.dataTransfer.files?.length) ingestFiles(e.dataTransfer.files);
    },
    [ingestFiles, setDrag],
  );

  return { capturePastedSource, ingestFiles, onDrop };
}
