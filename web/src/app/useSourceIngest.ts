/** Paste-long-text + file/photo ingest + drop for Liber composer. */

import {
  useCallback,
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
  const capturePastedSource = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (trimmed.length <= LONG_TEXT_CHARS) return false;
      const draft = {
        title: "Текст",
        text: trimmed,
      };
      setFile(null);
      setSourceDraft(draft);
      setPlaqueDismissed(false);
      setDeckApplyHint(null);
      setActiveArtifact({
        kind: "source",
        tab: "source",
        title: draft.title,
        text: draft.text,
      });
      return true;
    },
    [
      setFile,
      setSourceDraft,
      setPlaqueDismissed,
      setDeckApplyHint,
      setActiveArtifact,
    ],
  );

  const applySourceDraft = useCallback(
    (draft: SourceDraft) => {
      setFile(null);
      setSourceDraft(draft);
      setPlaqueDismissed(false);
      setDeckApplyHint(null);
      setActiveArtifact({
        kind: "source",
        tab: "source",
        title: draft.title,
        text: draft.text,
        fileName: draft.fileName,
      });
    },
    [
      setFile,
      setSourceDraft,
      setPlaqueDismissed,
      setDeckApplyHint,
      setActiveArtifact,
    ],
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
          setPlaqueDismissed(false);
          setDeckApplyHint(null);
          void (async () => {
            try {
              const text = await readTextFile(f);
              applySourceDraft({
                title: f.name,
                text,
                fileName: f.name,
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
          showToast(`Читаю ${f.name}…`, 6000);
          void (async () => {
            try {
              const out = await ingestOfficeSource(f);
              applySourceDraft({
                title: out.filename,
                text: out.markdown,
                fileName: out.filename,
              });
              if (out.warnings?.length) {
                showToast(out.warnings[0], 5000);
              } else {
                showToast(`Source: ${out.filename}`, 2800);
              }
            } catch (err) {
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
